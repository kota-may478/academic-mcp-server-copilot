from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

from academic_mcp_server.survey.enrich import enrich_crossref
from academic_mcp_server.survey.master_list import load_survey_config, master_list_path, save_master_list

STEP2_STATS = "_step2_stats.json"
WORKFLOW_STEP3 = Path.home() / "Obsidian/00_kotaprivate/Tool/prompt/survey_workflow_step3plus.prompt.md"
JSON_FENCE = "```json"
JSON_FENCE_END = "```"

SS_GRAPH = "https://api.semanticscholar.org/graph/v1"
RATE_SLEEP = 0.35
MAX_RETRIES = 5


def _http_get_json(url: str) -> dict | None:
    hdrs = {"User-Agent": "academic-mcp-server/survey-collection/1.0"}
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


def _ss_identifier_from_entry(entry: dict) -> str | None:
    for key in ("ss_paper_id", "source_id", "paper_id", "semantic_scholar_id"):
        val = str(entry.get(key) or "").strip()
        if val:
            if val.startswith(("DOI:", "arXiv:", "CorpusId:", "corpusId:")):
                return val
            return val
    ck = str(entry.get("candidate_key") or "").strip()
    if ck.startswith("SS:"):
        return ck[3:]
    if ck.startswith("DOI:"):
        return "DOI:" + ck[4:]
    if ck.startswith("arXiv:"):
        return "arXiv:" + ck[6:]
    return None


def _fetch_ss_abstract(identifier: str) -> str | None:
    enc = urllib.parse.quote(identifier.strip(), safe="")
    url = f"{SS_GRAPH}/paper/{enc}?fields=abstract"
    data = _http_get_json(url)
    if not data:
        return None
    abstract = (data.get("abstract") or "").strip()
    return abstract or None


def enrich_abstracts_semantic_scholar(ml: list[dict]) -> dict[str, int]:
    filled = 0
    for entry in ml:
        if (entry.get("abstract") or "").strip():
            continue
        ident = _ss_identifier_from_entry(entry)
        if not ident:
            continue
        abstract = _fetch_ss_abstract(ident)
        if abstract:
            entry["abstract"] = abstract
            entry["abstract_source"] = "semantic_scholar"
            filled += 1
        time.sleep(RATE_SLEEP)
    return {"abstracts_filled": filled}


def _in_step(entry: dict, step: str) -> bool:
    return step in (entry.get('discovered_in') or [])


def _not_in_steps(entry: dict, steps: list[str]) -> bool:
    return not any(s in (entry.get('discovered_in') or []) for s in steps)


def _fmt_authors(authors: list, max_n: int = 5) -> str:
    if not authors:
        return '-'
    if len(authors) >= max_n + 1:
        return ", ".join(authors[:max_n]) + " et al."
    return "; ".join(authors)


def _entry_md(entry: dict) -> str:
    lines: list[str] = []
    title = entry.get("title") or "(no title)"
    ck = entry.get("candidate_key") or ""
    doi = ck[4:] if ck.startswith("DOI:") else ""
    arxiv = ck[6:] if ck.startswith("arXiv:") else ""
    url = f"https://doi.org/{doi}" if doi else (f"https://arxiv.org/abs/{arxiv}" if arxiv else "")
    title_link = f"[{title}]({url})" if url else title
    lines.append(f"**{title_link}**")
    lines.append(f"- Authors: {_fmt_authors(entry.get('authors') or [])}")
    lines.append(f"- Year: {entry.get('year') or '-'}")
    lines.append(f"- Venue: {entry.get('venue') or '-'}")
    abstract = (entry.get("abstract") or "").strip()
    if abstract:
        lines.append(f"- Abstract: {abstract}")
    lines.append(f"- candidate_key: {ck!r}")
    oa = (entry.get("openalex_id") or "").strip()
    if oa:
        lines.append(f"- openalex_id: {oa!r}")
    cr = (entry.get("crossref_metadata") or "").strip()
    if cr:
        lines.append(f"- crossref_metadata: {cr}")
    disc = ", ".join(entry.get("discovered_in") or []) or "-"
    lines.append(f"- discovered_in: {disc}")
    sq = entry.get("seed_or_query") or []
    sqs = ", ".join(str(s) for s in sq) or "-"
    lines.append(f"- seed_or_query: {sqs}")
    lines.append(f"- content_basis: {entry.get('content_basis') or '-'}")
    lines.append(f"- relevance: {entry.get('relevance') or '-'}")
    lines.append(f"- relation_strength: {entry.get('relation_strength') or '-'}")
    return "\n".join(lines)


def _load_step2_stats(mirror: Path):
    path = mirror / STEP2_STATS
    if not path.is_file():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def render_ledger_collection(ml: list[dict], cfg: dict, step2_stats, enrich_result: dict) -> str:
    name = cfg.get("survey_name", "survey")
    tags = cfg.get("ledger_tags") or cfg.get("tags") or []
    tag_lines = "\n".join(f"  - {t}" for t in tags)
    today = date.today().isoformat()
    seeds = [e for e in ml if _in_step(e, "step1_seed")]
    step2_only = [e for e in ml if _in_step(e, "step2_snowball") and _not_in_steps(e, ["step1_seed"])]
    lines = [
        "---",
        f"number: {cfg.get('ledger_number', 0)}",
        f"title: {name}_Ledger_Collection",
        "tags:",
        tag_lines,
        f"created: {today}",
        "status: WIP",
        "phase: collection",
        "---",
        "",
        f"# {name} — Collection Ledger (Phase A)",
        "",
        f"Step 9 produces the final {name}_Ledger.md; this file aggregates all papers after Steps 1–2 (pre-screening).",
        "",
        f"- Total entries: **{len(ml)}**",
        f"- Step 1 seeds: **{len(seeds)}**",
        f"- Step 2 snowball (unique): **{len(step2_only)}**",
        f"- enrich (scope=collection): {json.dumps(enrich_result, ensure_ascii=False)}",
        "",
    ]
    if step2_stats is not None:
        lines += ["## Step 2 snowball stats (_step2_stats.json)", "", JSON_FENCE, json.dumps(step2_stats, ensure_ascii=False, indent=2), JSON_FENCE_END, ""]
    lines += ["---", "", "## 1. Seeds (Step 1)", ""]
    for e in seeds:
        lines.append(_entry_md(e))
        lines.append("")
    lines += ["---", "", "## 2. Step 2 snowball (unique)", ""]
    for e in step2_only:
        lines.append(_entry_md(e))
        lines.append("")
    return "\n".join(lines)


def render_handoff(cfg: dict, mirror: Path, vault: Path, ledger_path: Path) -> str:
    name = cfg.get("survey_name", "survey")
    target = cfg.get("target_word", "")
    wf = WORKFLOW_STEP3
    article = vault / f"{name}.md"
    final_ledger = vault / f"{name}_Ledger.md"
    return "\n".join([
        "# Survey handoff — continue from Step 3 (Phase B)",
        "",
        "You are continuing a literature survey after Phase A (Steps 1–2 + collection finalize).",
        "Do not redo Steps 1–2 unless the user explicitly resets the mirror.",
        "",
        "## Paths",
        f"- Mirror directory: {mirror}",
        f"- Master list: {mirror / '_working_master_list.json'}",
        f"- survey_config.json: {mirror / 'survey_config.json'}",
        f"- Collection ledger: {ledger_path}",
        f"- Workflow prompt (Steps 3–9): {wf}",
        f"- Target article (Step 9): {article}",
        f"- Final ledger (Step 9): {final_ledger}",
        "",
        "## Survey parameters",
        f"- survey_name: {name}",
        f"- target_word: {target}",
        f"- article_number: {cfg.get('article_number')}",
        f"- ledger_number: {cfg.get('ledger_number')}",
        "",
        "## Instructions",
        "1. Read the workflow prompt at the path above and execute Steps 3–9.",
        "2. Use _working_master_list.json as the authoritative deduplication source.",
        "3. Phase A artifacts (Ledger_Collection, _step2_stats.json, Crossref/OpenAlex fields) are reference only.",
        "4. Output language: Japanese.",
        "5. Prefer MCP survey tools; fallback survey-cli with PYTHONPATH=academic-mcp-server-copilot/src.",
        "",
    ])


def collection_finalize(mirror_dir: Path) -> dict:
    mirror = mirror_dir.expanduser().resolve()
    cfg = load_survey_config(mirror)
    enrich_result = enrich_crossref(mirror, scope="collection")
    ml_path = master_list_path(mirror)
    with open(ml_path, encoding="utf-8") as f:
        ml: list[dict] = json.load(f)
    abstract_result = enrich_abstracts_semantic_scholar(ml)
    save_master_list(ml_path, ml)
    step2_stats = _load_step2_stats(mirror)
    phase_a_meta = {**enrich_result, **abstract_result}
    name = cfg.get("survey_name", "survey")
    vault = Path(cfg.get("vault_survey_dir", mirror))
    ledger_path = vault / f"{name}_Ledger_Collection.md"
    handoff_path = vault / "handoff_step3.prompt.md"
    vault.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(render_ledger_collection(ml, cfg, step2_stats, phase_a_meta), encoding="utf-8")
    handoff_path.write_text(render_handoff(cfg, mirror, vault, ledger_path), encoding="utf-8")
    return {
        "mirror_dir": str(mirror),
        "ledger_collection_path": str(ledger_path),
        "handoff_path": str(handoff_path),
        "entries": len(ml),
        "enrich": phase_a_meta,
        "step2_stats_present": step2_stats is not None,
    }
