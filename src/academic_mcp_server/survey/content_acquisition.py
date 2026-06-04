"""Abstract / content acquisition for survey mirrors (Step 4.5 pre-screening, Step 5.5 strong)."""
from __future__ import annotations

import json
from pathlib import Path

from academic_mcp_server.survey.api_gateway import (
    fetch_openalex_abstract,
    fetch_ss_abstract,
    polite_sleep,
)
from academic_mcp_server.survey.master_list import (
    is_strong_corpus_entry,
    master_list_path,
    resolve_python_mirror_dir,
    save_master_list,
)

CONTENT_CHECKPOINT = 25


def _ss_identifier_from_entry(entry: dict) -> str | None:
    for key in ("ss_paper_id", "source_id", "paper_id", "semantic_scholar_id"):
        val = str(entry.get(key) or "").strip()
        if val:
            return val
    ck = str(entry.get("candidate_key") or "").strip()
    if ck.startswith("SS:"):
        return ck[3:]
    if ck.startswith("DOI:"):
        return "DOI:" + ck[4:]
    if ck.startswith("arXiv:"):
        return "arXiv:" + ck[6:]
    return None


def _is_strong_kept(entry: dict) -> bool:
    return is_strong_corpus_entry(entry)


def _normalize_existing_abstract(entry: dict) -> bool:
    abstract = (entry.get("abstract") or "").strip()
    if not abstract:
        return False
    cb = (entry.get("content_basis") or "").strip()
    if cb in ("abstract", "arxiv_fulltext"):
        return False
    entry["content_basis"] = "abstract"
    entry.setdefault("abstract_source", "pre_existing")
    return True


def _has_upgraded_content(entry: dict) -> bool:
    cb = (entry.get("content_basis") or "").strip()
    if cb == "arxiv_fulltext":
        return True
    if cb == "abstract" and (entry.get("abstract") or "").strip():
        return True
    return bool((entry.get("abstract") or "").strip())


def _needs_abstract_fetch(entry: dict) -> bool:
    if entry.get("abstract_attempted"):
        return False
    if _has_upgraded_content(entry):
        return False
    cb = (entry.get("content_basis") or "").strip()
    if cb in ("abstract", "arxiv_fulltext"):
        return False
    return True


def _needs_strong_content_upgrade(entry: dict) -> bool:
    if not _is_strong_kept(entry):
        return False
    return _needs_abstract_fetch(entry)


def _apply_abstract(entry: dict, abstract: str, source: str) -> None:
    entry["abstract"] = abstract
    entry["abstract_source"] = source
    entry["content_basis"] = "abstract"
    entry["keywords_stale"] = True


def _enrich_abstracts_for_entries(
    ml: list[dict],
    candidates: list[dict],
    path: Path,
) -> dict[str, int]:
    filled_ss = filled_oa = skipped = normalized = 0
    for i, entry in enumerate(candidates, 1):
        if _normalize_existing_abstract(entry):
            normalized += 1
            polite_sleep()
            if i % CONTENT_CHECKPOINT == 0:
                save_master_list(path, ml)
            continue
        ident = _ss_identifier_from_entry(entry)
        abstract = None
        source = ""
        if ident:
            abstract = fetch_ss_abstract(ident)
            if abstract:
                source = "semantic_scholar"
        if not abstract:
            abstract = fetch_openalex_abstract(entry)
            if abstract:
                source = "openalex"
        if abstract:
            _apply_abstract(entry, abstract, source)
            entry["abstract_attempted"] = True
            if source == "semantic_scholar":
                filled_ss += 1
            else:
                filled_oa += 1
        else:
            entry["content_basis"] = entry.get("content_basis") or "title_only"
            entry["abstract_attempted"] = True
            skipped += 1
        polite_sleep()
        if i % CONTENT_CHECKPOINT == 0:
            save_master_list(path, ml)

    save_master_list(path, ml)
    return {
        "candidates": len(candidates),
        "abstracts_filled_ss": filled_ss,
        "abstracts_filled_openalex": filled_oa,
        "abstracts_filled": filled_ss + filled_oa,
        "unchanged_or_missing_id": skipped,
        "keywords_stale_set": filled_ss + filled_oa,
        "normalized_pre_existing_abstract": normalized,
    }


def enrich_pre_screening_content(mirror_dir: Path | str) -> dict[str, int]:
    """Step 4.5: attempt abstract fetch for every master-list entry before Step 5 screening."""
    mirror = Path(mirror_dir).expanduser().resolve()
    pydir = resolve_python_mirror_dir(mirror)
    path = master_list_path(pydir)
    with open(path, encoding="utf-8") as f:
        ml: list[dict] = json.load(f)

    candidates = [e for e in ml if _needs_abstract_fetch(e)]
    stats = _enrich_abstracts_for_entries(ml, candidates, path)
    out = {**stats, "scope": "pre_screening_all", "entries_total": len(ml)}
    stats_path = pydir / "_step4_5_stats.json"
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    return out


def enrich_strong_content(mirror_dir: Path | str, *, upgrade_title_only: bool = True) -> dict[str, int]:
    """Step 5.5 / 8: fetch abstracts for kept+strong entries still missing abstract."""
    mirror = Path(mirror_dir).expanduser().resolve()
    pydir = resolve_python_mirror_dir(mirror)
    path = master_list_path(pydir)
    with open(path, encoding="utf-8") as f:
        ml: list[dict] = json.load(f)

    if upgrade_title_only:
        candidates = [e for e in ml if _needs_strong_content_upgrade(e)]
    else:
        candidates = [
            e for e in ml
            if _is_strong_kept(e) and not (e.get("abstract") or "").strip()
        ]
    stats = _enrich_abstracts_for_entries(ml, candidates, path)
    return {
        **stats,
        "strong_candidates": stats["candidates"],
        "scope": "strong_kept_only",
    }


def enrich_content(mirror_dir: Path | str, *, scope: str = "pre_screening") -> dict[str, int]:
    """Dispatch abstract enrichment by scope: pre_screening (all) or strong (kept+strong)."""
    if scope in ("pre_screening", "all", "collection"):
        return enrich_pre_screening_content(mirror_dir)
    if scope == "strong":
        return enrich_strong_content(mirror_dir)
    raise ValueError(f"unknown enrich-content scope: {scope}")
