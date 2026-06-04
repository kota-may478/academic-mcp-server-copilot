"""Structured survey ledger Markdown generation."""
from __future__ import annotations

from datetime import date

from academic_mcp_server.survey.master_list import is_kept_entry


def _fmt_keywords(kws: dict) -> str:
    parts = []
    for ax in ("P", "A", "O", "M"):
        vals = kws.get(ax, [])
        if vals:
            parts.append(f"[{ax}] " + ", ".join(str(v) for v in vals))
    return "; ".join(parts) if parts else "—"


def _entry_md(e: dict) -> str:
    lines = []
    title = e.get("title", "(no title)")
    ck = e.get("candidate_key", "")
    doi = ck[4:] if ck.startswith("DOI:") else None
    arxiv = ck[6:] if ck.startswith("arXiv:") else None
    url = f"https://doi.org/{doi}" if doi else (f"https://arxiv.org/abs/{arxiv}" if arxiv else "")
    title_link = f"[{title}]({url})" if url else title
    lines.append(f"**{title_link}**")

    authors = e.get("authors", [])
    if len(authors) >= 5:
        auth_str = ", ".join(str(a) for a in authors[:4]) + " et al."
    elif authors:
        auth_str = "; ".join(str(a) for a in authors)
    else:
        auth_str = "—"
    lines.append(f"- Authors: {auth_str}")
    lines.append(f"- Year: {e.get('year', '—')}")
    lines.append(f"- Venue: {e.get('venue') or '—'}")
    lines.append(f"- candidate_key: `{ck}`")
    lines.append(f"- discovered_in: {', '.join(e.get('discovered_in', []))}")
    lines.append(f"- seed_or_query: {', '.join(str(s) for s in e.get('seed_or_query', []))}")
    lines.append(f"- content_basis: {e.get('content_basis') or '—'}")
    lines.append(f"- keywords_source_step: {e.get('keywords_source_step') or '—'}")
    lines.append(f"- keywords_stale: {e.get('keywords_stale', False)}")
    lines.append(f"- keywords: {_fmt_keywords(e.get('keywords') or {})}")
    lines.append(f"- relevance: {e.get('relevance') or '—'}")
    lines.append(f"- relation_strength: {e.get('relation_strength') or '—'}")
    lines.append(f"- screened_at_step: {e.get('screened_at_step') or '—'}")
    lines.append(f"- crossref_metadata: {e.get('crossref_metadata') or '—'}")
    return "\n".join(lines)


def _in_step(e: dict, step: str) -> bool:
    return step in (e.get("discovered_in") or [])


def _not_in_steps(e: dict, steps: list[str]) -> bool:
    return not any(s in (e.get("discovered_in") or []) for s in steps)


def _categorize_kept(ml: list[dict]) -> dict[str, list[dict]]:
    kept = [e for e in ml if is_kept_entry(e)]
    return {
        "step1": [e for e in kept if _in_step(e, "step1_seed")],
        "step2": [
            e for e in kept
            if _in_step(e, "step2_snowball") and _not_in_steps(e, ["step1_seed"])
        ],
        "step4": [
            e for e in kept
            if _in_step(e, "step4_keyword")
            and _not_in_steps(e, ["step1_seed", "step2_snowball"])
        ],
        "step6": [
            e for e in kept
            if _in_step(e, "step6_snowball")
            and _not_in_steps(e, ["step1_seed", "step2_snowball", "step4_keyword"])
        ],
    }


def render_structured_ledger(ml: list[dict], cfg: dict) -> str:
    name = cfg.get("survey_name", "survey")
    tags = cfg.get("ledger_tags", cfg.get("tags", []))
    tag_lines = "\n".join("  - " + t for t in tags)
    today = date.today().isoformat()
    cats = _categorize_kept(ml)
    all_kept = cats["step1"] + cats["step2"] + cats["step4"] + cats["step6"]
    strong_n = sum(1 for e in all_kept if e.get("relation_strength") == "strong")
    weak_n = sum(1 for e in all_kept if e.get("relation_strength") == "weak")

    lines = [
        "---",
        f"number: {cfg.get('ledger_number', 0)}",
        f"title: {name}_Ledger",
        "tags:",
        tag_lines,
        f"created: {today}",
        "status: WIP",
        "---",
        "",
        f"# {name} — Survey Ledger",
        "",
        f"Total entries in master list: **{len(ml)}** | Kept: **{len(all_kept)}** "
        f"(strong **{strong_n}**, weak **{weak_n}**)",
        "",
        f"- Seeds (Step 1): {len(cats['step1'])}",
        f"- Step 2 snowball (unique): {len(cats['step2'])}",
        f"- Step 4 keyword search (unique): {len(cats['step4'])}",
        f"- Step 6 second snowball (unique): {len(cats['step6'])}",
        "",
        "> Weak papers are listed here for traceability but are excluded from the article "
        "(Section 3, Sections 4–8, References).",
        "",
        "---",
        "",
        "## 1. Final Corpus — Seeds (Step 1)",
        "",
    ]
    for e in cats["step1"]:
        lines.append(_entry_md(e))
        lines.append("")

    lines += ["---", "", "## 2. Final Corpus — Step 2 Snowball (unique)", ""]
    for e in cats["step2"]:
        lines.append(_entry_md(e))
        lines.append("")

    lines += ["---", "", "## 3. Final Corpus — Step 4 Keyword Search (unique)", ""]
    for e in cats["step4"]:
        lines.append(_entry_md(e))
        lines.append("")

    lines += ["---", "", "## 4. Final Corpus — Step 6 Second Snowball (unique)", ""]
    for e in cats["step6"]:
        lines.append(_entry_md(e))
        lines.append("")

    return "\n".join(lines)
