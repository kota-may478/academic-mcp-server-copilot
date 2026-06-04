"""Strong-relation minimum criteria for survey Step 5 / 7."""
from __future__ import annotations
from typing import Any

DEFAULT_STRONG_RELATION_CRITERIA: dict[str, Any] = {
    "mode": "default",
    "required_all": [],
    "required_any_groups": [],
    "notes": "",
}


def normalize_criteria(raw: dict[str, Any] | None) -> dict[str, Any]:
    if not raw:
        return dict(DEFAULT_STRONG_RELATION_CRITERIA)
    mode = (raw.get("mode") or "default").strip()
    required_all = [str(x).strip() for x in (raw.get("required_all") or []) if str(x).strip()]
    groups: list[list[str]] = []
    for group in raw.get("required_any_groups") or []:
        if isinstance(group, str):
            terms = [t.strip() for t in group.split(",") if t.strip()]
        else:
            terms = [str(t).strip() for t in group if str(t).strip()]
        if terms:
            groups.append(terms)
    notes = str(raw.get("notes") or "").strip()
    return {
        "mode": mode if mode in ("default", "custom_minimum") else "default",
        "required_all": required_all,
        "required_any_groups": groups,
        "notes": notes,
    }


def format_markdown_block(criteria: dict[str, Any] | None, target_word: str = "") -> str:
    c = normalize_criteria(criteria)
    lines = [
        "Classify strong only when all minimum conditions below are satisfied ",
        "(title, abstract, or P/A/O/M keywords; case-insensitive). Seeds stay strong.",
        "",
    ]
    if c["mode"] == "default" and not c["required_all"] and not c["required_any_groups"]:
        tw = target_word or "(target words)"
        lines.append("- Mode: default")
        lines.append("- Minimum: centrally addresses at least one of: " + tw)
        lines.append("")
    else:
        lines.append("- Mode: " + c["mode"])
        if c["required_all"]:
            lines.append("- Required ALL:")
            for t in c["required_all"]:
                lines.append("  - " + t)
        if c["required_any_groups"]:
            lines.append("- Required ANY groups (each group needs one match):")
            for i, g in enumerate(c["required_any_groups"], 1):
                lines.append("  - Group %d: %s" % (i, " OR ".join(g)))
        lines.append("")
    if c["notes"]:
        lines.append("Notes: " + c["notes"])
        lines.append("")
    return chr(10).join(lines)
