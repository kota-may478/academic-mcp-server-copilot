from __future__ import annotations

import json
import urllib.parse
from pathlib import Path

from academic_mcp_server.survey.api_gateway import cr_get_path, oa_get_path, polite_sleep
from academic_mcp_server.survey.master_list import (
    ARXIV_DOI_PREFIX,
    is_kept_entry,
    is_strong_corpus_entry,
    master_list_path,
    resolve_python_mirror_dir,
    save_master_list,
)

ENRICH_CHECKPOINT = 500


def cr_fetch_work(doi: str) -> dict | None:
    enc = urllib.parse.quote(doi, safe="/")
    data = cr_get_path(f"/works/{enc}")
    return (data or {}).get("message")


def oa_fetch_work_id(doi: str) -> str:
    enc = urllib.parse.quote(doi, safe="/")
    data = oa_get_path(f"/works/doi:{enc}?select=id")
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


def enrich_crossref(mirror_dir: Path | str, scope: str = "strong") -> dict[str, int]:
    mirror = Path(mirror_dir).expanduser().resolve()
    pydir = resolve_python_mirror_dir(mirror)
    path = master_list_path(pydir)
    with open(path, encoding="utf-8") as f:
        ml: list[dict] = json.load(f)
    enriched = 0
    processed = 0
    for entry in ml:
        if scope != "collection":
            if scope == "strong" and not is_strong_corpus_entry(entry):
                continue
            if scope == "all" and not is_kept_entry(entry):
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
            polite_sleep()
        if need_oa:
            oa_id = oa_fetch_work_id(doi)
            if oa_id:
                entry["openalex_id"] = oa_id
            polite_sleep()
        processed += 1
        if processed % ENRICH_CHECKPOINT == 0:
            save_master_list(path, ml)
            print(f"  enrich checkpoint [{processed}]: crossref_enriched={enriched}", flush=True)
    save_master_list(path, ml)
    return {"enriched_crossref": enriched, "entries": len(ml)}
