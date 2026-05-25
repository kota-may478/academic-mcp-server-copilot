from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from academic_mcp_server.survey.master_list import ARXIV_DOI_PREFIX, master_list_path, save_master_list

CR_API_BASE = "https://api.crossref.org"
OA_API_BASE = "https://api.openalex.org"
RATE_SLEEP = 0.35
MAX_RETRIES = 5


def _http_get_json(url: str, headers: dict | None = None) -> dict | None:
    hdrs = {"User-Agent": "academic-mcp-server/survey-enrich/1.0"}
    if headers:
        hdrs.update(headers)
    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(url, headers=hdrs)
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(2 * (attempt + 1))
                continue
            if e.code == 404:
                return None
            time.sleep(2 * (attempt + 1))
        except Exception:
            time.sleep(2 * (attempt + 1))
    return None


def cr_fetch_work(doi: str) -> dict | None:
    enc = urllib.parse.quote(doi, safe="/")
    data = _http_get_json(f"{CR_API_BASE}/works/{enc}")
    return (data or {}).get("message")


def oa_fetch_work_id(doi: str) -> str:
    email = os.environ.get("OPENALEX_EMAIL", "")
    mail = f"mailto={urllib.parse.quote(email)}&" if email else ""
    enc = urllib.parse.quote(doi, safe="/")
    data = _http_get_json(f"{OA_API_BASE}/works/doi:{enc}?{mail}select=id")
    if not data:
        return ""
    wid = data.get("id") or ""
    return wid.split("/")[-1] if wid else ""


def format_crossref_metadata(msg: dict | None, doi: str) -> str:
    if not msg:
        return ""
    container = ""
    for key in ("container-title", "short-container-title"):
        val = msg.get(key)
        if isinstance(val, list) and val:
            container = val[0]
            break
        if isinstance(val, str) and val:
            container = val
            break
    vol = msg.get("volume") or ""
    issue = msg.get("issue") or ""
    pages = msg.get("page") or ""
    if not pages:
        sp = msg.get("page-first") or ""
        ep = msg.get("page-last") or ""
        if sp and ep:
            pages = f"{sp}-{ep}"
        elif sp:
            pages = sp
    year = ""
    parts = (msg.get("issued") or {}).get("date-parts") or [[]]
    if parts and parts[0]:
        year = str(parts[0][0])
    bits: list[str] = []
    if container:
        bits.append(str(container))
    if vol:
        bits.append(f"Vol. {vol}")
    if issue:
        bits.append(f"No. {issue}")
    if pages:
        bits.append(f"pp. {pages}")
    if year:
        bits.append(year)
    line = ", ".join(bits)
    if line:
        line += "."
    return f"{line} DOI: {doi}".strip()


ENRICH_CHECKPOINT = 500


def enrich_crossref(mirror_dir: Path | str, scope: str = "strong") -> dict[str, int]:
    mirror = Path(mirror_dir).expanduser().resolve()
    path = master_list_path(mirror)
    with open(path, encoding="utf-8") as f:
        ml: list[dict] = json.load(f)
    enriched = 0
    processed = 0
    for entry in ml:
        if scope != "collection":
            if entry.get("relevance") != "kept":
                continue
            if scope == "strong" and entry.get("relation_strength") != "strong":
                continue
        ck = entry.get("candidate_key") or ""
        if not ck.startswith("DOI:"):
            continue
        doi = ck[4:]
        if doi.startswith(ARXIV_DOI_PREFIX):
            continue
        need_cr = not (entry.get("crossref_metadata") or "").strip()
        need_oa = not (entry.get("openalex_id") or "").strip()
        if not need_cr and not need_oa:
            continue
        if need_cr:
            meta = format_crossref_metadata(cr_fetch_work(doi), doi)
            if meta:
                entry["crossref_metadata"] = meta
                enriched += 1
            time.sleep(RATE_SLEEP)
        if need_oa:
            oa_id = oa_fetch_work_id(doi)
            if oa_id:
                entry["openalex_id"] = oa_id
            time.sleep(RATE_SLEEP)
        processed += 1
        if processed % ENRICH_CHECKPOINT == 0:
            save_master_list(path, ml)
            print(f"  enrich checkpoint [{processed}]: crossref_enriched={enriched}", flush=True)
    save_master_list(path, ml)
    return {"enriched_crossref": enriched, "entries": len(ml)}
