from __future__ import annotations

import json
import re
from pathlib import Path

WORKING_MASTER_LIST = "_working_master_list.json"
SURVEY_CONFIG = "survey_config.json"
ARXIV_DOI_PREFIX = "10.48550"


def make_candidate_key(item: dict) -> str:
    ext = item.get("externalIds") or item.get("external_ids") or {}
    doi = ext.get("DOI") or ext.get("doi")
    arxiv = ext.get("ArXiv") or ext.get("arXiv")
    prefix = "10.48550/arXiv."
    if doi and str(doi).startswith(prefix):
        return "arXiv:" + str(doi)[len(prefix):]
    if doi:
        return f"DOI:{doi}"
    if arxiv:
        return f"arXiv:{arxiv}"
    sid = item.get("paperId") or item.get("source_id") or item.get("corpusId")
    if sid:
        return f"SS:{sid}"
    title = item.get("title", "")
    if title:
        norm = re.sub(r"[^a-z0-9 ]", "", title.lower())
        norm = re.sub(r"\s+", "_", norm.strip())[:80]
        return f"title:{norm}"
    return ""


def candidate_key_from_entry(entry: dict) -> str:
    return str(entry.get("candidate_key") or "")


def extract_year(raw: object) -> int | None:
    if not raw:
        return None
    m = re.match(r"(\d{4})", str(raw))
    return int(m.group(1)) if m else None


def fmt_authors(authors: list) -> list[str]:
    result: list[str] = []
    for a in authors or []:
        if isinstance(a, dict):
            a = a.get("name", "")
        a = str(a).strip()
        parts = a.split()
        if len(parts) >= 2:
            last = parts[-1]
            initials = ".".join(p[0].upper() for p in parts[:-1] if p) + "."
            result.append(f"{last}, {initials}")
        elif a:
            result.append(a)
    return result


def load_master_list(path: Path) -> tuple[list[dict], set[str]]:
    with open(path, encoding="utf-8") as f:
        ml: list[dict] = json.load(f)
    seen = {str(e.get("candidate_key")) for e in ml if e.get("candidate_key")}
    return ml, seen


def save_master_list(path: Path, ml: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(ml, f, ensure_ascii=False, indent=2)


def mark_keywords_from_step(entry: dict, step: str) -> None:
    """Record keyword provenance after agent re-extraction in Step 3 / 5.5 / 8."""
    entry["keywords_source_step"] = step
    entry["keywords_stale"] = False


def mark_screened(entry: dict, step: str) -> None:
    entry["screened_at_step"] = step


def is_seed_entry(entry: dict) -> bool:
    return "step1_seed" in (entry.get("discovered_in") or [])


def is_kept_entry(entry: dict) -> bool:
    if entry.get("relevance") == "kept":
        return True
    # Seed immunity: Step 1 seeds are strong corpus members even before Step 5 sets relevance.
    return is_seed_entry(entry) and entry.get("relation_strength") == "strong"


def is_strong_corpus_entry(entry: dict) -> bool:
    return is_kept_entry(entry) and entry.get("relation_strength") == "strong"


def resolve_python_mirror_dir(mirror_dir: Path | str) -> Path:
    mirror = Path(mirror_dir).expanduser().resolve()
    cfg_path = mirror / SURVEY_CONFIG
    if cfg_path.is_file():
        cfg = load_survey_config(mirror)
        return Path(cfg.get("python_survey_dir", mirror)).expanduser().resolve()
    return mirror


def load_survey_config(mirror_dir: Path) -> dict:
    cfg_path = mirror_dir / SURVEY_CONFIG
    with open(cfg_path, encoding="utf-8") as f:
        return json.load(f)


def master_list_path(mirror_dir: Path) -> Path:
    return mirror_dir / WORKING_MASTER_LIST
