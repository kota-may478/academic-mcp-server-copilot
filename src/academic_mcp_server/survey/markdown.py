from __future__ import annotations

import re

OLD_LINK_RE = re.compile(r"\[(R\d{3})\]\(#(?:\^ref)?r?\1\)", re.IGNORECASE)


def ref_link(rid: str) -> str:
    rid = rid.strip()
    if not rid.startswith("R"):
        rid = f"R{rid}"
    return f"[{rid}](#^ref{rid})"


def esc_table_cell(text: object) -> str:
    if text is None:
        return ""
    s = str(text)
    s = s.replace("|", "\|")
    s = s.replace(chr(10), " ").replace(chr(13), " ")
    return s


def fix_internal_ref_links(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        return ref_link(match.group(1).upper())

    return OLD_LINK_RE.sub(repl, text)
