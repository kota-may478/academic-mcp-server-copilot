"""Step 3 completion statistics written to _step3_stats.json."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from academic_mcp_server.survey.master_list import master_list_path, resolve_python_mirror_dir


def write_step3_stats(mirror_dir: Path | str) -> dict:
    mirror = Path(mirror_dir).expanduser().resolve()
    pydir = resolve_python_mirror_dir(mirror)
    path = master_list_path(pydir)
    with open(path, encoding="utf-8") as f:
        ml: list[dict] = json.load(f)

    content_basis = Counter(str(e.get("content_basis") or "—") for e in ml)
    kw_counts = Counter()
    missing_keywords = 0
    per_axis: dict[str, Counter] = {ax: Counter() for ax in "PAOM"}
    min_kw = 999999
    max_kw = 0

    for e in ml:
        kws = e.get("keywords") or {}
        total = sum(len(kws.get(ax) or []) for ax in "PAOM")
        if total == 0:
            missing_keywords += 1
        else:
            min_kw = min(min_kw, total)
            max_kw = max(max_kw, total)
            kw_counts[total] += 1
        for ax in "PAOM":
            per_axis[ax][len(kws.get(ax) or [])] += 1

    stats = {
        "entries": len(ml),
        "content_basis": dict(content_basis),
        "missing_keywords": missing_keywords,
        "keyword_total_distribution": {str(k): v for k, v in sorted(kw_counts.items())},
        "keyword_total_min": 0 if missing_keywords == len(ml) else min_kw,
        "keyword_total_max": max_kw,
        "per_axis_count_histogram": {ax: dict(sorted(c.items())) for ax, c in per_axis.items()},
        "keywords_source_step": dict(Counter(str(e.get("keywords_source_step") or "unset") for e in ml)),
    }

    out_path = pydir / "_step3_stats.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    return {"path": str(out_path), **stats}
