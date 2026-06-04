"""Survey corpus validation (strong-only References invariant, metadata completeness)."""
from __future__ import annotations

import json
import re
from pathlib import Path

from academic_mcp_server.survey.generate import _ordered_strong
from academic_mcp_server.survey.topics_loader import (
    TopicsConfigError,
    topics_module_from_cfg,
    validate_topic_taxonomy_alignment,
)
from academic_mcp_server.survey.master_list import (
    is_kept_entry,
    is_seed_entry,
    is_strong_corpus_entry,
    load_survey_config,
    master_list_path,
    resolve_python_mirror_dir,
)

_REF_LINE = re.compile(r"^\[(R\d+)\]")
_REF_LINK = re.compile(r"\[(R\d+)\]\(#\^refR\d+\)")


def _strong_corpus(ml: list[dict]) -> list[dict]:
    return [e for e in ml if is_strong_corpus_entry(e)]


def parse_reference_ids(article_text: str) -> set[str]:
    """Reference IDs from ## References lines like [R001]."""
    return _parse_reference_ids(article_text)


def parse_cited_ids(article_text: str) -> set[str]:
    """Rxxx IDs cited as [Rxxx](#^refRxxx) anywhere in the article."""
    return _parse_cited_ids(article_text)


def _parse_reference_ids(article_text: str) -> set[str]:
    ids: set[str] = set()
    in_refs = False
    for line in article_text.splitlines():
        if line.strip().startswith("## References"):
            in_refs = True
            continue
        if in_refs and line.startswith("## "):
            break
        if in_refs:
            m = _REF_LINE.match(line.strip())
            if m:
                ids.add(m.group(1))
    return ids


def _parse_cited_ids(article_text: str) -> set[str]:
    return set(_REF_LINK.findall(article_text))


def validate_survey(mirror_dir: Path | str, *, article_path: Path | str | None = None) -> dict:
    mirror = Path(mirror_dir).expanduser().resolve()
    pydir = resolve_python_mirror_dir(mirror)
    cfg = load_survey_config(pydir)
    path = master_list_path(pydir)
    with open(path, encoding="utf-8") as f:
        ml: list[dict] = json.load(f)

    errors: list[str] = []
    warnings: list[str] = []

    try:
        topics_module_from_cfg(cfg)
    except TopicsConfigError as exc:
        errors.append(str(exc))

    ordered, rids, kept = _ordered_strong(ml)
    strong = _strong_corpus(ml)
    weak_kept = [e for e in ml if is_kept_entry(e) and e.get("relation_strength") == "weak"]
    expected_rids = set(rids.values())

    if len(ordered) != len(strong):
        errors.append(f"ordered_strong count ({len(ordered)}) != strong corpus ({len(strong)})")

    if len(ml) > 0 and len(strong) == 0:
        warnings.append("strong corpus is empty — Step 5 screening may be incomplete")
    elif len(strong) > 0 and len(strong) < 3 and any(is_seed_entry(e) for e in ml):
        warnings.append(f"strong corpus has only {len(strong)} entries; verify Step 5 kept seeds")

    stale_kw = [e for e in strong if e.get("keywords_stale")]
    if stale_kw:
        warnings.append(f"{len(stale_kw)} strong entries have keywords_stale=true (re-extract pending)")

    unscreened = [
        e for e in ml
        if not (e.get("relevance") or "").startswith("removed")
        and "step1_seed" not in (e.get("discovered_in") or [])
        and not e.get("relation_strength")
    ]
    if unscreened:
        warnings.append(f"{len(unscreened)} entries lack relation_strength (screening incomplete?)")

    missing_kw = [
        e for e in ml
        if is_kept_entry(e)
        and not any((e.get("keywords") or {}).get(ax) for ax in "PAOM")
    ]
    if missing_kw:
        warnings.append(f"{len(missing_kw)} kept entries have empty keywords")

    art_path = Path(article_path).expanduser().resolve() if article_path else None
    if not art_path:
        name = cfg.get("survey_name", "survey")
        vault = Path(cfg.get("vault_survey_dir", mirror))
        candidate = vault / f"{name}.md"
        if candidate.is_file():
            art_path = candidate

    article_checks: dict = {}
    if art_path and art_path.is_file():
        text = art_path.read_text(encoding="utf-8")
        ref_ids = _parse_reference_ids(text)
        cite_ids = _parse_cited_ids(text)

        article_checks = {
            "article_path": str(art_path),
            "reference_ids": sorted(ref_ids),
            "cited_ids_count": len(cite_ids),
        }

        if ref_ids != expected_rids:
            extra = ref_ids - expected_rids
            missing = expected_rids - ref_ids
            if extra:
                errors.append(f"References contain non-strong or unexpected IDs: {sorted(extra)}")
            if missing:
                errors.append(f"References missing strong corpus IDs: {sorted(missing)}")

        orphan_cites = cite_ids - ref_ids
        if orphan_cites:
            errors.append(f"In-text citations without References entry: {sorted(orphan_cites)}")

        errors.extend(validate_topic_taxonomy_alignment(cfg, text))

    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "counts": {
            "master_total": len(ml),
            "kept": len(kept),
            "strong": len(strong),
            "weak_kept": len(weak_kept),
            "expected_references": len(expected_rids),
        },
        "article": article_checks,
        "mirror_dir": str(mirror),
    }
