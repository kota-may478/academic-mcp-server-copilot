from __future__ import annotations
import importlib
import json
from collections import defaultdict
from datetime import date
from pathlib import Path
from academic_mcp_server.survey.analysis import analyze_corpus
from academic_mcp_server.survey.markdown import esc_table_cell, fix_internal_ref_links, ref_link
from academic_mcp_server.survey.master_list import load_survey_config, master_list_path
# Default import for backwards compatibility
from academic_mcp_server.survey.topics_ipt import RESEARCH_GAPS, SEED_SUMMARIES, TOPICS, TOPIC_SUMMARIES, assign_subtopics


def _load_topics_symbols(cfg: dict):
    """Load topics module symbols from cfg['topics_module'], falling back to topics_ipt."""
    mod_name = cfg.get("topics_module", "academic_mcp_server.survey.topics_ipt")
    mod = importlib.import_module(mod_name)
    return (
        getattr(mod, "RESEARCH_GAPS", []),
        getattr(mod, "SEED_SUMMARIES", {}),
        getattr(mod, "TOPICS", {}),
        getattr(mod, "TOPIC_SUMMARIES", {}),
        getattr(mod, "assign_subtopics"),
    )

def _ordered_strong(ml):
    kept = [e for e in ml if e.get("relevance") == "kept"]
    seeds = [e for e in kept if "step1_seed" in (e.get("discovered_in") or [])]

    def by_year(ps):
        return sorted(ps, key=lambda e: e.get("year") or 0, reverse=True)

    def only(step, exclude):
        return [
            e
            for e in kept
            if step in (e.get("discovered_in") or [])
            and not any(x in (e.get("discovered_in") or []) for x in exclude)
        ]

    s2 = only("step2_snowball", ["step1_seed"])
    s4 = only("step4_keyword", ["step1_seed", "step2_snowball"])
    s6 = only("step6_snowball", ["step1_seed", "step2_snowball", "step4_keyword"])
    ordered = [e for e in seeds + by_year(s2) + by_year(s4) + by_year(s6) if e.get("relation_strength") == "strong"]
    rids = {e["candidate_key"]: f"R{i:03d}" for i, e in enumerate(ordered, 1)}
    return ordered, rids, kept

def get_url(entry):
    ck = entry.get("candidate_key", "")
    if ck.startswith("DOI:"):
        return "https://doi.org/" + ck[4:]
    if ck.startswith("arXiv:"):
        return "https://arxiv.org/abs/" + ck[6:]
    return ""

def _topic_index(strong):
    tp = defaultdict(list)
    sp = defaultdict(list)
    for e in strong:
        for t, st in assign_subtopics(e):
            sp[(t, st)].append(e)
            if not any(x.get("candidate_key") == e.get("candidate_key") for x in tp[t]):
                tp[t].append(e)
    return dict(tp), dict(sp)

def fmt_authors(authors, max_n=4):
    if not authors: return "-"
    if len(authors) >= 5: return ", ".join(authors[:4]) + " et al."
    return "; ".join(authors)

def fmt_keywords_short(kws):
    parts = []
    for ax in ("P", "A", "O", "M"):
        vs = kws.get(ax, [])
        if vs: parts.append("[" + ax + "] " + ", ".join(vs))
    return "; ".join(parts) if parts else "-"

def gen_ja_summary(entry):
    ck = entry.get("candidate_key", "")
    if ck in SEED_SUMMARIES: return SEED_SUMMARIES[ck]
    cb = entry.get("content_basis", "title_only")
    s = "Survey corpus entry."
    if cb == "title_only": s += " (title only)"
    return s

def _sections_4_8(strong, rids, analysis, weak):
    tp, sp = _topic_index(strong)
    out = ["## Section 4 - Topic Classification", "> strong=%d weak=%d" % (len(strong), len(weak))]
    for tid, tinfo in TOPICS.items():
        out.append("### " + tinfo["name"])
        out.append("| subtopic | papers | count |\n|---|---|---|")
        for stid, stname in tinfo["subtopics"].items():
            papers = sp.get((tid, stid), [])
            cites = ", ".join(ref_link(rids[e["candidate_key"]]) for e in papers) if papers else "-"
            out.append("| %s | %s | %d |" % (esc_table_cell(stname), cites, len(papers)))
    out.append("## Section 5 - Quant tables")
    cb = analysis.get("content_basis_breakdown") or {}
    out.append("| content_basis | count |\n|---|---|")
    for k, v in cb.items(): out.append("| %s | %d |" % (esc_table_cell(k), v))
    co = analysis.get("keyword_cooccurrence_top_pairs") or {}
    for ax in ("P", "A", "O", "M"):
        out.append("### co-occurrence " + ax)
        out.append("| kw1 | kw2 | n |\n|---|---|---|")
        for a, b, n in (co.get(ax) or [])[:10]: out.append("| %s | %s | %d |" % (esc_table_cell(a), esc_table_cell(b), n))
    hist = analysis.get("year_histogram_by_discovered_in") or {}
    out.append("### year histogram")
    for step, years in hist.items():
        out.append("#### " + step)
        out.append("| year | count |\n|---|---|")
        for y, c in years.items(): out.append("| %s | %d |" % (y, c))
    out.append("## Section 6 - Topic summaries")
    ranked = sorted(TOPICS.items(), key=lambda kv: len(tp.get(kv[0], [])), reverse=True)[:5]
    for tid, tinfo in ranked:
        papers = tp.get(tid, [])
        if not papers: continue
        rep = ", ".join(ref_link(rids[e["candidate_key"]]) for e in sorted(papers, key=lambda e: -(e.get("year") or 0))[:8])
        out.append("### " + tinfo["name"] + "\n" + TOPIC_SUMMARIES.get(tid, "") + "\nRep: " + rep)
    out.append("## Section 7 - Gaps")
    for i, (t, b, _) in enumerate(RESEARCH_GAPS, 1): out.append("%d. **%s** %s" % (i, t, b))
    counts = analysis.get("counts", {})
    out.append("## Section 8 - Conclusion\nKept=%d strong=%d" % (counts.get("kept", 0), len(strong)))
    return "\n\n".join(out)

def _section3(ordered, rids, kept, weak):
    lines = ["## Section 3 - Master Paper List", "", "Corpus kept=%d strong=%d weak=%d" % (len(kept), len(ordered), len(weak)), "| ID | Title | Authors | Year | CB | RS | Keywords |", "|---|---|---|---|---|---|---|"]
    for e in ordered:
        r = rids[e["candidate_key"]]
        url = get_url(e)
        title = e.get("title", "-")
        tc = "[%s](%s)" % (esc_table_cell(title), url) if url else "\"%s\"" % esc_table_cell(title)
        row = [ref_link(r), tc, esc_table_cell(fmt_authors(e.get("authors", []), 3)), esc_table_cell(str(e.get("year") or "-")), esc_table_cell(e.get("content_basis", "-")), esc_table_cell(e.get("relation_strength", "-")), esc_table_cell(fmt_keywords_short(e.get("keywords", {})))]
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)

def generate_ledger(ml, cfg):
    tags = cfg.get("ledger_tags", cfg.get("tags", []))
    tag_lines = "\n".join("  - " + t for t in tags)
    today = date.today().isoformat()
    name = cfg.get("survey_name", "survey")
    lines = ["---", "number: %s" % cfg.get("ledger_number", 0), "title: %s_Ledger" % name, "tags:", tag_lines, "created: " + today, "status: WIP", "---", "", "# %s Ledger" % name, ""]
    for e in ml:
        lines.append("- **%s** ck=%s rel=%s rs=%s" % (e.get("title", "(no title)"), e.get("candidate_key", ""), e.get("relevance"), e.get("relation_strength")))
    return "\n".join(lines)


def _references(ordered, rids):
    lines = ["## References", ""]
    for e in ordered:
        r = rids[e["candidate_key"]]
        title = e.get("title", "-")
        url = get_url(e)
        title_md = ('"[%s](%s)"' % (title, url)) if url else ('"%s"' % title)
        cr = (e.get("crossref_metadata") or "").strip()
        venue = cr if cr else str(e.get("year") or "-")
        lines.append("[%s] %s. %s. %s. %s ^ref%s" % (r, fmt_authors(e.get("authors", [])), title_md, venue, gen_ja_summary(e), r))
        lines.append("")
    return chr(10).join(lines)

def generate_docs(mirror_dir):
    global RESEARCH_GAPS, SEED_SUMMARIES, TOPICS, TOPIC_SUMMARIES, assign_subtopics
    mirror = Path(mirror_dir).expanduser().resolve()
    cfg = load_survey_config(mirror)
    if cfg.get("topics_module"):
        RESEARCH_GAPS, SEED_SUMMARIES, TOPICS, TOPIC_SUMMARIES, assign_subtopics = _load_topics_symbols(cfg)
    name = cfg.get("survey_name", "survey")
    vault = Path(cfg.get("vault_survey_dir", mirror))
    pydir = Path(cfg.get("python_survey_dir", mirror))
    article_path = vault / (name + ".md")
    ledger_path = vault / (name + "_Ledger.md")
    with open(master_list_path(pydir), encoding="utf-8") as f:
        ml = json.load(f)
    ordered, rids, kept = _ordered_strong(ml)
    weak = [e for e in ml if e.get("relation_strength") == "weak" and e.get("relevance") == "kept"]
    analysis = analyze_corpus(mirror)
    tags = cfg.get("tags", [cfg.get("target_word", "")])
    tag_lines = chr(10).join("  - " + t for t in tags)
    fm = ["---", "number: %s" % cfg.get("article_number", 0), "title: " + name, "tags:", tag_lines, "created: " + date.today().isoformat(), "status: WIP", "---", "", "> Ref links use [Rxxx](#^refRxxx)", ""]
    parts = fm + [_section3(ordered, rids, kept, weak), _sections_4_8(ordered, rids, analysis, weak), _references(ordered, rids)]
    article = fix_internal_ref_links((chr(10)*2).join(parts))
    article_path.parent.mkdir(parents=True, exist_ok=True)
    with open(article_path, "w", encoding="utf-8") as f:
        f.write(article)
    with open(ledger_path, "w", encoding="utf-8") as f:
        f.write(generate_ledger(ml, cfg))
    return {"article_path": str(article_path), "ledger_path": str(ledger_path)}
