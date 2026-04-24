from __future__ import annotations

import re
from html import unescape
from typing import Any

from academic_mcp_server.common.models import Paper

_TAG_PATTERN = re.compile(r"<[^>]+>")


def normalize_limit(limit: int | None, *, default: int, maximum: int = 25) -> int:
    if limit is None:
        return default

    if limit < 1 or limit > maximum:
        raise ValueError(f"limit must be between 1 and {maximum}.")

    return limit


def normalize_text(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    without_tags = _TAG_PATTERN.sub(" ", text)
    collapsed = " ".join(unescape(without_tags).split())
    return collapsed or None


def coerce_int(value: Any) -> int | None:
    if value is None:
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def first_text(values: Any) -> str | None:
    if isinstance(values, list):
        for value in values:
            text = normalize_text(value)
            if text:
                return text
        return None

    return normalize_text(values)


def date_parts_to_iso(value: dict[str, Any] | None) -> str | None:
    if not value:
        return None

    date_parts = value.get("date-parts") or []
    if not date_parts:
        return None

    parts = [str(part) for part in date_parts[0] if part is not None]
    if not parts:
        return None

    if len(parts) == 1:
        return f"{parts[0]}-01-01"
    if len(parts) == 2:
        return f"{parts[0]}-{parts[1].zfill(2)}-01"
    return f"{parts[0]}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"


def year_to_iso(year: Any) -> str | None:
    normalized_year = coerce_int(year)
    if normalized_year is None:
        return None
    return f"{normalized_year:04d}-01-01"


def sort_papers_for_display(papers: list[Paper]) -> list[Paper]:
    return sorted(
        papers,
        key=lambda paper: (paper.published or "", paper.title.casefold()),
        reverse=True,
    )


def normalize_semantic_scholar_paper(raw_paper: dict[str, Any]) -> Paper:
    external_ids = {
        key: str(value)
        for key, value in (raw_paper.get("externalIds") or {}).items()
        if value is not None
    }
    doi = normalize_text(external_ids.get("DOI"))
    source_id = (
        normalize_text(raw_paper.get("paperId"))
        or normalize_text(raw_paper.get("corpusId"))
        or doi
        or first_text(raw_paper.get("title"))
        or "unknown"
    )

    return Paper(
        source="semantic_scholar",
        source_id=source_id,
        title=first_text(raw_paper.get("title")) or "Untitled",
        abstract=normalize_text(raw_paper.get("abstract")),
        authors=[
            author_name
            for author_name in (
                normalize_text(author.get("name"))
                for author in (raw_paper.get("authors") or [])
            )
            if author_name
        ],
        published=normalize_text(raw_paper.get("publicationDate"))
        or year_to_iso(raw_paper.get("year")),
        doi=doi,
        venue=normalize_text(raw_paper.get("venue")),
        url=normalize_text(raw_paper.get("url")),
        pdf_url=normalize_text((raw_paper.get("openAccessPdf") or {}).get("url")),
        citation_count=coerce_int(raw_paper.get("citationCount")),
        subjects=[
            subject
            for subject in (
                normalize_text(value) for value in (raw_paper.get("fieldsOfStudy") or [])
            )
            if subject
        ],
        external_ids=external_ids,
    )


def normalize_arxiv_entry(entry: Any) -> Paper:
    links = entry.get("links") or []
    pdf_url = next(
        (
            normalize_text(link.get("href"))
            for link in links
            if link.get("title") == "pdf" or link.get("type") == "application/pdf"
        ),
        None,
    )
    source_id = normalize_text(entry.get("id"))
    if source_id and "/" in source_id:
        source_id = source_id.rsplit("/", 1)[-1]
    source_id = source_id or "unknown"

    external_ids = {"ArXiv": source_id}
    doi = normalize_text(entry.get("arxiv_doi"))
    if doi:
        external_ids["DOI"] = doi

    return Paper(
        source="arxiv",
        source_id=source_id,
        title=normalize_text(entry.get("title")) or "Untitled",
        abstract=normalize_text(entry.get("summary")),
        authors=[
            author_name
            for author_name in (
                normalize_text(author.get("name"))
                for author in (entry.get("authors") or [])
            )
            if author_name
        ],
        published=normalize_text(entry.get("published"))
        or normalize_text(entry.get("updated")),
        doi=doi,
        venue="arXiv",
        url=normalize_text(entry.get("id")),
        pdf_url=pdf_url,
        subjects=[
            subject
            for subject in (
                normalize_text(tag.get("term")) for tag in (entry.get("tags") or [])
            )
            if subject
        ],
        external_ids=external_ids,
    )


def normalize_crossref_work(raw_work: dict[str, Any]) -> Paper:
    doi = normalize_text(raw_work.get("DOI"))
    source_id = doi or normalize_text(raw_work.get("URL")) or "unknown"

    authors: list[str] = []
    for author in raw_work.get("author") or []:
        direct_name = normalize_text(author.get("name"))
        if direct_name:
            authors.append(direct_name)
            continue

        given = normalize_text(author.get("given"))
        family = normalize_text(author.get("family"))
        combined = " ".join(part for part in (given, family) if part)
        if combined:
            authors.append(combined)

    published = (
        date_parts_to_iso(raw_work.get("published-print"))
        or date_parts_to_iso(raw_work.get("published-online"))
        or date_parts_to_iso(raw_work.get("issued"))
        or date_parts_to_iso(raw_work.get("created"))
    )

    external_ids: dict[str, str] = {}
    if doi:
        external_ids["DOI"] = doi

    return Paper(
        source="crossref",
        source_id=source_id,
        title=first_text(raw_work.get("title")) or "Untitled",
        abstract=normalize_text(raw_work.get("abstract")),
        authors=authors,
        published=published,
        doi=doi,
        venue=first_text(raw_work.get("container-title")),
        url=normalize_text(raw_work.get("URL")),
        citation_count=coerce_int(raw_work.get("is-referenced-by-count")),
        subjects=[
            subject
            for subject in (
                normalize_text(value) for value in (raw_work.get("subject") or [])
            )
            if subject
        ],
        external_ids=external_ids,
    )