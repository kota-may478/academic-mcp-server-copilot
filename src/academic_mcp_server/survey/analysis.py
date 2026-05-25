from __future__ import annotations

import importlib
import json
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

from academic_mcp_server.survey.master_list import load_survey_config, master_list_path
# Default import for backwards compatibility
from academic_mcp_server.survey.topics_ipt import TOPICS as _DEFAULT_TOPICS, assign_subtopics as _DEFAULT_ASSIGN


def _load_topics_for_dir(mirror: Path):
    """Load TOPICS and assign_subtopics from survey_config topics_module if set."""
    cfg = load_survey_config(mirror)
    mod_name = cfg.get("topics_module", "academic_mcp_server.survey.topics_ipt")
    mod = importlib.import_module(mod_name)
    return getattr(mod, "TOPICS", _DEFAULT_TOPICS), getattr(mod, "assign_subtopics", _DEFAULT_ASSIGN)


TOPICS = _DEFAULT_TOPICS
assign_subtopics = _DEFAULT_ASSIGN


def _strong_corpus(ml: list[dict]) -> list[dict]:
    return [e for e in ml if e.get("relevance") == "kept" and e.get("relation_strength") == "strong"]


def _year_histogram_by_discovered_in(entries: list[dict]) -> dict[str, dict[str, int]]:
    out: dict[str, Counter[int]] = defaultdict(Counter)
    for e in entries:
        year = e.get("year")
        if not year:
            continue
        for step in e.get("discovered_in") or []:
            out[str(step)][int(year)] += 1
    return {k: dict(sorted(v.items())) for k, v in sorted(out.items())}


def _content_basis_breakdown(entries: list[dict]) -> dict[str, int]:
    c: Counter[str] = Counter()
    for e in entries:
        c[str(e.get("content_basis") or "—")] += 1
    return dict(c.most_common())


def _keyword_cooccurrence(entries: list[dict], top_n: int = 15) -> dict[str, list[tuple[str, str, int]]]:
    result: dict[str, list[tuple[str, str, int]]] = {}
    for ax in ("P", "A", "O", "M"):
        pair_counts: Counter[tuple[str, str]] = Counter()
        for e in entries:
            kws = sorted({str(k).strip().lower() for k in (e.get("keywords") or {}).get(ax, []) if k})
            for a, b in combinations(kws, 2):
                pair_counts[(a, b)] += 1
        result[ax] = [(a, b, n) for (a, b), n in pair_counts.most_common(top_n)]
    return result


def _build_topic_index(strong: list[dict]) -> tuple[dict[str, list[dict]], dict[tuple[str, str], list[dict]]]:
    topic_papers: dict[str, list[dict]] = defaultdict(list)
    subtopic_papers: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for e in strong:
        for t, st in assign_subtopics(e):
            subtopic_papers[(t, st)].append(e)
            if not any(x.get("candidate_key") == e.get("candidate_key") for x in topic_papers[t]):
                topic_papers[t].append(e)
    return dict(topic_papers), dict(subtopic_papers)


def analyze_corpus(mirror_dir: Path | str) -> dict:
    global TOPICS, assign_subtopics
    mirror = Path(mirror_dir).expanduser().resolve()
    TOPICS, assign_subtopics = _load_topics_for_dir(mirror)
    with open(master_list_path(mirror), encoding="utf-8") as f:
        ml: list[dict] = json.load(f)
    kept = [e for e in ml if e.get("relevance") == "kept"]
    strong = _strong_corpus(ml)
    topic_papers, subtopic_papers = _build_topic_index(strong)
    assigned = {e.get("candidate_key") for papers in topic_papers.values() for e in papers}
    unassigned = [e for e in strong if e.get("candidate_key") not in assigned]
    return {
        "counts": {
            "master_total": len(ml),
            "kept": len(kept),
            "strong": len(strong),
            "weak_kept": len([e for e in kept if e.get("relation_strength") == "weak"]),
            "removed": len([e for e in ml if str(e.get("relevance", "")).startswith("removed")]),
            "unassigned_strong": len(unassigned),
        },
        "year_histogram_by_discovered_in": _year_histogram_by_discovered_in(kept),
        "content_basis_breakdown": _content_basis_breakdown(strong),
        "keyword_cooccurrence_top_pairs": _keyword_cooccurrence(strong),
        "topics": TOPICS,
        "topic_papers_keys": {tid: [e.get("candidate_key") for e in papers] for tid, papers in topic_papers.items()},
        "subtopic_papers_keys": {f"{t}:{st}": [e.get("candidate_key") for e in papers] for (t, st), papers in subtopic_papers.items()},
        "topic_paper_counts": {tid: len(papers) for tid, papers in topic_papers.items()},
        "unassigned_candidate_keys": [e.get("candidate_key") for e in unassigned],
    }
