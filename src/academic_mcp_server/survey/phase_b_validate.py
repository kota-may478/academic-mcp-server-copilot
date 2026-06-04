"""Phase B post-edit checks: Markdown tables and [Rxxx](#^refRxxx) link integrity."""
from __future__ import annotations

import re
from pathlib import Path

from academic_mcp_server.survey.validate import (
    parse_cited_ids,
    parse_reference_ids,
    validate_survey,
)

_REF_LINK_PAIR = re.compile(r"\[(R\d+)\]\(#\^ref(R\d+)\)")
_ANY_REF_LINK = re.compile(r"\[(R\d+)\]\((#[^)]+)\)")
_BLOCK_ID = re.compile(r"\^ref(R\d+)\b")
_TODO_STUB = re.compile(
    r"TODO\s*\(agent\)|\*\*TODO|Kept=\d+\s+strong=|Rep:\s*\d+",
    re.IGNORECASE,
)
_TABLE_ROW = re.compile(r"^\|.+\|$")
# Block-level elements that may precede a table without a blank line (headings, HR, blockquotes)
_BLOCK_LEVEL = re.compile(r"^\s*(#{1,6}\s|>\s*|---+\s*$|===+\s*$)")


def _split_table_row(line: str) -> list[str]:
    inner = line.strip()
    if not inner.startswith("|"):
        return []
    if inner.endswith("|"):
        inner = inner[1:-1]
    else:
        inner = inner[1:]
    return [c.strip() for c in inner.split("|")]


def _is_separator_row(cells: list[str]) -> bool:
    if not cells:
        return False
    return all(re.fullmatch(r":?-{3,}:?", c.replace(" ", "")) for c in cells if c)


def _iter_pipe_table_blocks(lines: list[str]) -> list[list[tuple[int, str]]]:
    """Group *strictly* consecutive pipe rows.

    A blank line TERMINATES the current table block (CommonMark / Obsidian behaviour).
    Previously this function skipped blank lines, causing split tables to appear valid.
    """
    blocks: list[list[tuple[int, str]]] = []
    i = 0
    n = len(lines)
    while i < n:
        stripped = lines[i].strip()
        if not _TABLE_ROW.match(stripped):
            i += 1
            continue
        # Start collecting a contiguous block – stop at blank line or non-pipe line
        block: list[tuple[int, str]] = []
        while i < n:
            stripped = lines[i].strip()
            if not stripped:
                break  # blank line terminates the table
            if not _TABLE_ROW.match(stripped):
                break
            block.append((i + 1, lines[i]))
            i += 1
        if block:
            blocks.append(block)
    return blocks


def check_markdown_tables(text: str) -> tuple[list[str], list[str]]:
    """Return (errors, warnings) for pipe-table column-count structure."""
    errors: list[str] = []
    warnings: list[str] = []
    for block in _iter_pipe_table_blocks(text.splitlines()):
        start_line = block[0][0]
        header_cells = _split_table_row(block[0][1])
        ncol = len(header_cells)
        if ncol < 2:
            warnings.append(f"Line {start_line}: table row has fewer than 2 columns")
        idx = 1
        if idx < len(block) and _is_separator_row(_split_table_row(block[idx][1])):
            sep_cells = _split_table_row(block[idx][1])
            if len(sep_cells) != ncol:
                errors.append(
                    f"Line {block[idx][0]}: separator column count ({len(sep_cells)}) "
                    f"!= header ({ncol})"
                )
            idx += 1
        body_rows = 0
        while idx < len(block):
            line_no, row = block[idx]
            row_cells = _split_table_row(row)
            if not _is_separator_row(row_cells):
                body_rows += 1
                if len(row_cells) != ncol:
                    errors.append(
                        f"Line {line_no}: table body column count ({len(row_cells)}) "
                        f"!= header ({ncol})"
                    )
            idx += 1
        if body_rows == 0 and ncol > 0:
            warnings.append(f"Line {start_line}: table has header but no body rows")
    return errors, warnings


def check_table_rendering_gaps(text: str) -> tuple[list[str], list[str]]:
    """Detect rendering-breaking table layout issues (Obsidian / CommonMark).

    Two error classes:
    1. **Blank line between table rows** — splits the table; rows after the blank
       render as plain text instead of table cells.
    2. **Table header directly following a plain-text line** (no blank line) —
       Obsidian/CommonMark requires a blank line before a table when it follows
       paragraph text.
    """
    errors: list[str] = []
    lines = text.splitlines()
    n = len(lines)

    for i, raw_line in enumerate(lines):
        stripped = raw_line.strip()
        if not _TABLE_ROW.match(stripped):
            continue
        if i == 0:
            continue  # first line of file – OK

        prev = lines[i - 1].strip()

        # ── Case 1: blank line between pipe rows ───────────────────────────
        if not prev:
            if i >= 2 and _TABLE_ROW.match(lines[i - 2].strip()):
                errors.append(
                    f"Line {i + 1}: blank line splits table rows "
                    f"(pipe row at line {i - 1}, blank at line {i}, "
                    f"pipe row resumes at line {i + 1}) — "
                    f"remove the blank line to keep rows in the same table"
                )
            # else: blank line before the very first pipe row → OK (proper table start)
            continue

        # ── Case 2: consecutive pipe rows → OK ────────────────────────────
        if _TABLE_ROW.match(prev):
            continue

        # ── Case 3: block-level element (heading / HR / blockquote) → OK ──
        if _BLOCK_LEVEL.match(prev):
            continue

        # ── Case 4: plain text immediately before table header ─────────────
        errors.append(
            f"Line {i + 1}: table header not preceded by blank line "
            f"(line {i} is plain text: {prev[:60]!r}) — "
            f"insert a blank line before the table"
        )

    return errors, []


def check_reference_links(text: str) -> tuple[list[str], list[str]]:
    """Validate [Rxxx](#^refRxxx) vs References block IDs."""
    errors: list[str] = []
    warnings: list[str] = []

    ref_ids = parse_reference_ids(text)
    cite_ids = parse_cited_ids(text)
    block_ids = {m.group(1) for m in _BLOCK_ID.finditer(text)}

    for m in _REF_LINK_PAIR.finditer(text):
        label, anchor = m.group(1), m.group(2)
        if label != anchor:
            errors.append(
                f"Link label/anchor mismatch: [{label}](#^ref{anchor}) "
                f"(expected [#^{label}](#^ref{label}))"
            )

    for m in _ANY_REF_LINK.finditer(text):
        rid, target = m.group(1), m.group(2)
        canonical = f"#^ref{rid}"
        if target != canonical:
            errors.append(f"Non-canonical ref link: [{rid}]({target}) (expected [{rid}]({canonical}))")

    orphan_cites = cite_ids - ref_ids
    if orphan_cites:
        errors.append(f"In-text links without References entry: {sorted(orphan_cites)}")

    missing_anchors = ref_ids - block_ids
    if missing_anchors:
        sample = sorted(missing_anchors)[:10]
        extra = f" … +{len(missing_anchors) - 10}" if len(missing_anchors) > 10 else ""
        errors.append(f"References missing ^ref block ID (sample): {sample}{extra}")

    unused_refs = ref_ids - cite_ids
    if len(unused_refs) > 20:
        warnings.append(
            f"{len(unused_refs)} References entries never cited in prose/tables "
            "(may be OK if only listed in Section 3)"
        )

    return errors, warnings


def check_phase_b_stubs(text: str) -> list[str]:
    warnings: list[str] = []
    for i, line in enumerate(text.splitlines(), 1):
        if _TODO_STUB.search(line):
            warnings.append(
                f"Line {i}: possible Phase B stub/TODO remaining: {line.strip()[:80]}"
            )
    return warnings


def validate_phase_b_article(
    article_path: Path | str,
    *,
    mirror_dir: Path | str | None = None,
    check_corpus: bool = True,
) -> dict:
    """
    Phase B completion gate: tables, ref links, optional corpus invariant (validate_survey).
    """
    art_path = Path(article_path).expanduser().resolve()
    if not art_path.is_file():
        return {"ok": False, "errors": [f"Article not found: {art_path}"], "warnings": []}

    text = art_path.read_text(encoding="utf-8")
    errors: list[str] = []
    warnings: list[str] = []

    table_err, table_warn = check_markdown_tables(text)
    errors.extend(table_err)
    warnings.extend(table_warn)

    render_err, _ = check_table_rendering_gaps(text)
    errors.extend(render_err)

    link_err, link_warn = check_reference_links(text)
    errors.extend(link_err)
    warnings.extend(link_warn)

    warnings.extend(check_phase_b_stubs(text))

    corpus_result: dict | None = None
    if check_corpus and mirror_dir is not None:
        corpus_result = validate_survey(mirror_dir, article_path=art_path)
        errors.extend(corpus_result.get("errors") or [])
        warnings.extend(corpus_result.get("warnings") or [])

    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "article_path": str(art_path),
        "corpus_validate": corpus_result,
    }
