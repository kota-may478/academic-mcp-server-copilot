"""Unified HTTP access for survey workflows: auth, lock, rate limit, disk cache, 429 retries."""
from __future__ import annotations

import email.utils
import hashlib
import json
import os
import random
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from contextlib import contextmanager
from email.utils import parseaddr
from pathlib import Path
from typing import Any, Iterator, Literal

Provider = Literal["semantic_scholar", "openalex", "crossref", "other"]

SS_GRAPH = "https://api.semanticscholar.org/graph/v1"
SS_API_BASE = SS_GRAPH
OA_API_BASE = "https://api.openalex.org"
CR_API_BASE = "https://api.crossref.org"

USER_AGENT = "academic-mcp-server/survey/2.0"
DEFAULT_CACHE_TTL = 86400.0
DEFAULT_CACHE_DIR = Path.home() / ".cache" / "academic-mcp-survey" / "http"
DEFAULT_LOCK_FILE = Path.home() / ".cache" / "academic-mcp-survey" / "api.lock"

MAX_RETRIES = 8
RATE_SLEEP_DEFAULT = 0.35

_rate_lock = threading.Lock()
_last_request_at: dict[str, float] = {"semantic_scholar": 0.0, "openalex": 0.0, "crossref": 0.0, "other": 0.0}
_lock_depth = 0


def _clean_env(name: str) -> str:
    value = os.environ.get(name)
    if value is None:
        return ""
    return value.strip()


def semantic_scholar_api_key() -> str:
    return _clean_env("ACADEMIC_MCP_SEMANTIC_SCHOLAR_API_KEY") or _clean_env(
        "SEMANTIC_SCHOLAR_API_KEY"
    )


def openalex_email() -> str:
    for name in (
        "OPENALEX_EMAIL",
        "ACADEMIC_MCP_OPENALEX_CONTACT_EMAIL",
        "ACADEMIC_MCP_CONTACT_EMAIL",
    ):
        raw = _clean_env(name)
        if not raw:
            continue
        _, parsed = parseaddr(raw)
        if "@" in parsed:
            return parsed
    return ""


def openalex_api_key() -> str:
    return _clean_env("OPENALEX_API_KEY") or _clean_env("ACADEMIC_MCP_OPENALEX_API_KEY")


def _min_interval(provider: Provider, url: str) -> float:
    if provider == "semantic_scholar":
        return float(os.environ.get("SURVEY_SS_MIN_INTERVAL", "0.34"))
    if provider == "openalex":
        if "/works?" in url or "filter=" in url:
            return float(os.environ.get("SURVEY_OA_LIST_MIN_INTERVAL", "0.55"))
        return float(os.environ.get("SURVEY_OA_MIN_INTERVAL", "0.22"))
    if provider == "crossref":
        return float(os.environ.get("SURVEY_CR_MIN_INTERVAL", "0.35"))
    return float(os.environ.get("SURVEY_HTTP_MIN_INTERVAL", "0.2"))


def _rate_limit_wait(provider: Provider, url: str) -> None:
    interval = _min_interval(provider, url)
    with _rate_lock:
        now = time.monotonic()
        elapsed = now - _last_request_at[provider]
        if elapsed < interval:
            time.sleep(interval - elapsed)
        _last_request_at[provider] = time.monotonic()


def _cache_dir() -> Path:
    raw = _clean_env("SURVEY_API_CACHE_DIR")
    path = Path(raw).expanduser() if raw else DEFAULT_CACHE_DIR
    path.mkdir(parents=True, exist_ok=True)
    return path


def _cache_ttl_seconds() -> float:
    raw = _clean_env("SURVEY_API_CACHE_TTL")
    if not raw:
        return DEFAULT_CACHE_TTL
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_CACHE_TTL
    return max(value, 0.0)


def _cache_enabled() -> bool:
    return _clean_env("SURVEY_API_CACHE_DISABLE") not in ("1", "true", "yes")


def _normalize_cache_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    drop = {"mailto", "api_key"}
    filtered = [(k, v) for k, v in pairs if k not in drop]
    filtered.sort()
    query = urllib.parse.urlencode(filtered)
    return urllib.parse.urlunparse(
        (parsed.scheme, parsed.netloc, parsed.path, parsed.params, query, "")
    )


def _cache_path(url: str) -> Path:
    digest = hashlib.sha256(_normalize_cache_url(url).encode("utf-8")).hexdigest()
    return _cache_dir() / f"{digest}.json"


def _cache_read(url: str) -> dict | None:
    if not _cache_enabled():
        return None
    path = _cache_path(url)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    expires_at = payload.get("expires_at")
    if not isinstance(expires_at, (int, float)) or expires_at <= time.time():
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
        return None
    body = payload.get("body")
    return body if isinstance(body, dict) else None


def _cache_write(url: str, body: dict) -> None:
    if not _cache_enabled():
        return
    path = _cache_path(url)
    payload = {"expires_at": time.time() + _cache_ttl_seconds(), "body": body}
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _lock_path() -> Path:
    raw = _clean_env("SURVEY_API_LOCK_FILE")
    path = Path(raw).expanduser() if raw else DEFAULT_LOCK_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _auto_lock_enabled() -> bool:
    return _clean_env("SURVEY_API_LOCK_DISABLE") not in ("1", "true", "yes")


@contextmanager
def _api_request_lock(*, blocking: bool = True) -> Iterator[None]:
    """Serialize SS/OpenAlex HTTP across processes; re-entrant within one Python process."""
    global _lock_depth
    if not _auto_lock_enabled():
        yield
        return
    if _lock_depth > 0:
        _lock_depth += 1
        try:
            yield
        finally:
            _lock_depth -= 1
        return

    import fcntl

    lock_path = _lock_path()
    handle = open(lock_path, "a+", encoding="utf-8")
    flags = fcntl.LOCK_EX
    if not blocking:
        flags |= fcntl.LOCK_NB
    try:
        fcntl.flock(handle.fileno(), flags)
    except BlockingIOError as exc:
        handle.close()
        raise RuntimeError(
            f"Another survey API job holds {lock_path}. "
            "Wait for it to finish or stop the other process."
        ) from exc
    _lock_depth = 1
    try:
        yield
    finally:
        _lock_depth = 0
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


@contextmanager
def survey_api_lock(*, blocking: bool = True) -> Iterator[None]:
    """Hold exclusive API lock for an entire batch (Step 4, enrich-content, snowball)."""
    with _api_request_lock(blocking=blocking):
        yield


def _detect_provider(url: str) -> Provider:
    if "api.semanticscholar.org" in url:
        return "semantic_scholar"
    if "api.openalex.org" in url:
        return "openalex"
    if "api.crossref.org" in url:
        return "crossref"
    return "other"


def _request_headers(url: str, extra: dict[str, str] | None) -> dict[str, str]:
    provider = _detect_provider(url)
    headers: dict[str, str] = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    email = openalex_email()
    if email:
        headers["User-Agent"] = f"{USER_AGENT} (mailto:{email})"
    if provider == "semantic_scholar":
        key = semantic_scholar_api_key()
        if key:
            headers["x-api-key"] = key
    if extra:
        headers.update(extra)
    return headers


def _retry_after_seconds(error: urllib.error.HTTPError) -> float | None:
    raw = error.headers.get("Retry-After") if error.headers else None
    if not raw:
        return None
    raw = raw.strip()
    if raw.isdigit():
        return float(raw)
    try:
        parsed = email.utils.parsedate_to_datetime(raw)
    except (TypeError, ValueError, OverflowError):
        return None
    if parsed is None:
        return None
    delay = parsed.timestamp() - time.time()
    return max(delay, 0.0)


def http_get_json(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    provider: Provider | None = None,
    use_cache: bool = True,
) -> dict | None:
    """GET JSON with cross-process lock, rate limit, disk cache, and unified 429 backoff."""
    prov = provider or _detect_provider(url)
    if use_cache:
        cached = _cache_read(url)
        if cached is not None:
            return cached
    hdrs = _request_headers(url, headers)
    backoff = 2.0
    with _api_request_lock():
        for attempt in range(MAX_RETRIES):
            _rate_limit_wait(prov, url)
            try:
                req = urllib.request.Request(url, headers=hdrs)
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                if not isinstance(data, dict):
                    return None
                if use_cache:
                    _cache_write(url, data)
                return data
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    return None
                if e.code in (429, 408, 500, 502, 503, 504) and attempt < MAX_RETRIES - 1:
                    retry_after = _retry_after_seconds(e)
                    wait = retry_after if retry_after is not None else min(backoff, 120.0)
                    wait += random.uniform(0.0, 0.5)
                    print(
                        f"    HTTP {e.code} ({url[:70]}…), retry in {wait:.1f}s "
                        f"[{attempt + 1}/{MAX_RETRIES}]",
                        flush=True,
                    )
                    time.sleep(wait)
                    backoff = min(backoff * 2, 120.0)
                    continue
                return None
            except Exception:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(min(backoff, 30.0))
                    backoff = min(backoff * 2, 120.0)
                    continue
                return None
    return None


def openalex_query_suffix() -> str:
    """Query-string prefix for OpenAlex auth (mailto and/or api_key)."""
    parts: list[str] = []
    email = openalex_email()
    if email:
        parts.append(f"mailto={urllib.parse.quote(email)}")
    key = openalex_api_key()
    if key:
        parts.append(f"api_key={urllib.parse.quote(key)}")
    if not parts:
        return ""
    return "&".join(parts) + "&"


def append_openalex_auth(url: str) -> str:
    suffix = openalex_query_suffix()
    if not suffix:
        return url
    if "?" in url:
        return f"{url}&{suffix.rstrip('&')}"
    return f"{url}?{suffix.rstrip('&')}"


def oa_get_path(path: str) -> dict | None:
    """GET OpenAlex path (e.g. '/works/W123') with mailto/api_key."""
    if not path.startswith("/"):
        path = "/" + path
    url = append_openalex_auth(f"{OA_API_BASE}{path}")
    return http_get_json(url, provider="openalex")


def ss_get_path(path: str) -> dict | None:
    """GET Semantic Scholar Graph API path with x-api-key when configured."""
    if not path.startswith("/"):
        path = "/" + path
    url = f"{SS_GRAPH}{path}"
    return http_get_json(url, provider="semantic_scholar")


def cr_get_path(path: str) -> dict | None:
    if not path.startswith("/"):
        path = "/" + path
    url = f"{CR_API_BASE}{path}"
    return http_get_json(url, provider="crossref")


def polite_sleep() -> None:
    time.sleep(float(os.environ.get("SURVEY_CONTENT_SLEEP", RATE_SLEEP_DEFAULT)))


def fetch_ss_abstract(identifier: str) -> str | None:
    enc = urllib.parse.quote(identifier.strip(), safe="")
    data = ss_get_path(f"/paper/{enc}?fields=abstract")
    if not data:
        return None
    abstract = (data.get("abstract") or "").strip()
    return abstract or None


def _openalex_work_url(entry: dict) -> str | None:
    oa_id = str(entry.get("openalex_id") or "").strip()
    if oa_id:
        wid = oa_id if oa_id.startswith("W") else oa_id.split("/")[-1]
        return f"{OA_API_BASE}/works/{wid}"
    ck = str(entry.get("candidate_key") or "").strip()
    if ck.startswith("DOI:"):
        doi = ck[4:]
        enc = urllib.parse.quote(doi, safe="/")
        return f"{OA_API_BASE}/works/doi:{enc}"
    return None


def _reconstruct_openalex_abstract(abstract_inverted_index: object) -> str | None:
    if not isinstance(abstract_inverted_index, dict):
        return None
    indexed: list[tuple[int, str]] = []
    for token, positions in abstract_inverted_index.items():
        if not token or not isinstance(positions, list):
            continue
        for position in positions:
            if isinstance(position, int):
                indexed.append((position, str(token)))
    if not indexed:
        return None
    indexed.sort(key=lambda item: item[0])
    return " ".join(token for _, token in indexed)


def fetch_openalex_abstract(entry: dict) -> str | None:
    base = _openalex_work_url(entry)
    if not base:
        return None
    url = append_openalex_auth(f"{base}?select=abstract_inverted_index")
    data = http_get_json(url, provider="openalex")
    if not data:
        return None
    return _reconstruct_openalex_abstract(data.get("abstract_inverted_index"))


def assert_exclusive_survey_api_jobs(job_label: str = "survey API batch") -> None:
    """Fail fast when another survey-cli enrich / enrich-content process is already running."""
    import re
    import subprocess

    pattern = "academic_mcp_server.survey.cli enrich"
    try:
        out = subprocess.check_output(
            ["pgrep", "-af", pattern],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        return

    me = os.getpid()
    py_cli = re.compile(
        r"^(?:\S*/)?python3?\s+-m\s+academic_mcp_server\.survey\.cli\s+enrich",
    )
    others: list[str] = []
    for line in out.strip().splitlines():
        if not line.strip():
            continue
        parts = line.split(None, 1)
        if len(parts) < 2:
            continue
        try:
            pid = int(parts[0])
        except ValueError:
            continue
        if pid == me:
            continue
        cmd = parts[1]
        if not py_cli.match(cmd):
            continue
        others.append(line.strip())

    if others:
        sample = "\n  ".join(others[:5])
        raise RuntimeError(
            f"Another {job_label} is already running ({len(others)} python process(es)). "
            "Stop duplicates first: pgrep -af 'survey.cli enrich'\n  "
            + sample
        )


def survey_auth_status() -> dict[str, Any]:
    """Diagnostics for configured survey API credentials (no secrets)."""
    ss_key = semantic_scholar_api_key()
    oa_mail = openalex_email()
    oa_key = openalex_api_key()
    return {
        "semantic_scholar_api_key": "present" if ss_key else "absent",
        "openalex_email": "present" if oa_mail else "absent",
        "openalex_api_key": "present" if oa_key else "absent",
        "cache_dir": str(_cache_dir()),
        "lock_file": str(_lock_path()),
        "cache_enabled": _cache_enabled(),
        "lock_enabled": _auto_lock_enabled(),
    }
