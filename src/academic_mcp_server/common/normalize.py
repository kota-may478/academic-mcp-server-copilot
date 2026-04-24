from __future__ import annotations

import re
from html import unescape
from typing import Any

from academic_mcp_server.common.models import Author, Paper

_TAG_PATTERN = re.compile(r"<[^>]+>")
_ARXIV_VERSION_PATTERN = re.compile(r"v(\d+)$", re.IGNORECASE)


def normalize_limit(limit: int | None, *, default: int, maximum: int = 25) -> int:
    if limit is None:
        return default

    if limit < 1 or limit > maximum:
        raise ValueError(f"limit must be between 1 and {maximum}.")

    return limit


def normalize_offset(offset: int | None) -> int:
    if offset is None:
        return 0

    if offset < 0:
        raise ValueError("offset must be greater than or equal to 0.")

    return offset


def normalize_text(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    without_tags = _TAG_PATTERN.sub(" ", text)
    collapsed = " ".join(unescape(without_tags).split())
    return collapsed or None


def normalize_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value

    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    return None


def coerce_int(value: Any) -> int | None:
    if value is None:
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize_text_list(values: Any) -> list[str]:
    if values is None:
        return []
    if not isinstance(values, list):
        values = [values]

    normalized_values: list[str] = []
    for value in values:
        normalized_value = normalize_text(value)
        if normalized_value:
            normalized_values.append(normalized_value)
    return normalized_values


def normalize_identifier_map(values: dict[str, Any] | None) -> dict[str, Any]:
    if not values:
        return {}

    normalized_values: dict[str, Any] = {}
    for key, value in values.items():
        if value is None:
            continue
        if isinstance(value, list):
            normalized_list = normalize_text_list(value)
            if normalized_list:
                normalized_values[key] = normalized_list
            continue

        normalized_value = normalize_text(value)
        if normalized_value:
            normalized_values[key] = normalized_value

    return normalized_values


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


def parse_orcid(value: Any) -> str | None:
    normalized_value = normalize_text(value)
    if not normalized_value:
        return None

    if normalized_value.lower().startswith("http") and "/" in normalized_value:
        return normalized_value.rsplit("/", 1)[-1]

    return normalized_value


def extract_arxiv_version(source_id: str | None) -> str | None:
    if not source_id:
        return None

    match = _ARXIV_VERSION_PATTERN.search(source_id)
    if not match:
        return None

    return match.group(1)


def sort_papers_for_display(papers: list[Paper]) -> list[Paper]:
    return sorted(
        papers,
        key=lambda paper: (paper.published or "", paper.title.casefold()),
        reverse=True,
    )


def normalize_semantic_scholar_author(raw_author: dict[str, Any]) -> Author:
    external_ids = normalize_identifier_map(raw_author.get("externalIds") or {})
    raw_orcid = external_ids.get("ORCID")
    orcid = first_text(raw_orcid) if isinstance(raw_orcid, list) else parse_orcid(raw_orcid)

    return Author(
        name=normalize_text(raw_author.get("name")) or "Unknown author",
        author_id=normalize_text(raw_author.get("authorId")),
        affiliations=normalize_text_list(raw_author.get("affiliations")),
        orcid=orcid,
        url=normalize_text(raw_author.get("url")),
        homepage=normalize_text(raw_author.get("homepage")),
        paper_count=coerce_int(raw_author.get("paperCount")),
        citation_count=coerce_int(raw_author.get("citationCount")),
        h_index=coerce_int(raw_author.get("hIndex")),
        external_ids=external_ids,
    )


def normalize_semantic_scholar_paper(
    raw_paper: dict[str, Any],
    *,
    extra_metadata: dict[str, Any] | None = None,
) -> Paper:
    external_ids = normalize_identifier_map(raw_paper.get("externalIds") or {})
    raw_doi = external_ids.get("DOI")
    doi = first_text(raw_doi) if isinstance(raw_doi, list) else normalize_text(raw_doi)
    source_id = (
        normalize_text(raw_paper.get("paperId"))
        or normalize_text(raw_paper.get("corpusId"))
        or doi
        or first_text(raw_paper.get("title"))
        or "unknown"
    )

    author_details = [
        normalize_semantic_scholar_author(author)
        for author in (raw_paper.get("authors") or [])
        if normalize_text(author.get("name"))
    ]

    source_metadata: dict[str, Any] = {}
    tldr = normalize_text((raw_paper.get("tldr") or {}).get("text"))
    if tldr:
        source_metadata["tldr"] = tldr

    publication_venue = raw_paper.get("publicationVenue") or {}
    publication_venue_name = normalize_text(publication_venue.get("name"))
    if publication_venue_name:
        source_metadata["publication_venue"] = publication_venue_name

    journal = raw_paper.get("journal") or {}
    journal_metadata = {
        key: value
        for key, value in {
            "name": normalize_text(journal.get("name")),
            "volume": normalize_text(journal.get("volume")),
            "pages": normalize_text(journal.get("pages")),
        }.items()
        if value
    }
    if journal_metadata:
        source_metadata["journal"] = journal_metadata

    text_availability = normalize_text(raw_paper.get("textAvailability"))
    if text_availability:
        source_metadata["text_availability"] = text_availability

    if extra_metadata:
        for key, value in extra_metadata.items():
            if value not in (None, [], {}, ""):
                source_metadata[key] = value

    primary_subject = first_text(
        [item.get("category") for item in (raw_paper.get("s2FieldsOfStudy") or [])]
    ) or first_text(raw_paper.get("fieldsOfStudy"))

    return Paper(
        source="semantic_scholar",
        source_id=source_id,
        title=first_text(raw_paper.get("title")) or "Untitled",
        abstract=normalize_text(raw_paper.get("abstract")),
        authors=[author.name for author in author_details],
        author_details=author_details,
        published=normalize_text(raw_paper.get("publicationDate"))
        or year_to_iso(raw_paper.get("year")),
        updated=normalize_text(raw_paper.get("updated")),
        doi=doi,
        venue=normalize_text(raw_paper.get("venue")),
        publisher=publication_venue_name or normalize_text(journal.get("name")),
        url=normalize_text(raw_paper.get("url")),
        pdf_url=normalize_text((raw_paper.get("openAccessPdf") or {}).get("url")),
        citation_count=coerce_int(raw_paper.get("citationCount")),
        reference_count=coerce_int(raw_paper.get("referenceCount")),
        influential_citation_count=coerce_int(raw_paper.get("influentialCitationCount")),
        is_open_access=normalize_bool(raw_paper.get("isOpenAccess")),
        license=normalize_text((raw_paper.get("openAccessPdf") or {}).get("license")),
        primary_subject=primary_subject,
        publication_types=normalize_text_list(raw_paper.get("publicationTypes")),
        subjects=[
            subject
            for subject in (
                normalize_text(value) for value in (raw_paper.get("fieldsOfStudy") or [])
            )
            if subject
        ],
        external_ids=external_ids,
        source_metadata=source_metadata,
    )


def normalize_arxiv_author(raw_author: dict[str, Any]) -> Author:
    return Author(
        name=normalize_text(raw_author.get("name")) or "Unknown author",
        affiliations=normalize_text_list(
            raw_author.get("arxiv_affiliation") or raw_author.get("affiliation")
        ),
    )


def normalize_arxiv_entry(
    entry: Any,
    *,
    extra_metadata: dict[str, Any] | None = None,
) -> Paper:
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

    author_details = [
        normalize_arxiv_author(author)
        for author in (entry.get("authors") or [])
        if normalize_text(author.get("name"))
    ]

    source_metadata: dict[str, Any] = {}
    comment = normalize_text(entry.get("arxiv_comment"))
    if comment:
        source_metadata["comment"] = comment

    version = extract_arxiv_version(source_id)
    if version:
        source_metadata["version"] = version

    if extra_metadata:
        for key, value in extra_metadata.items():
            if value not in (None, [], {}, ""):
                source_metadata[key] = value

    primary_subject = normalize_text((entry.get("arxiv_primary_category") or {}).get("term"))

    return Paper(
        source="arxiv",
        source_id=source_id,
        title=normalize_text(entry.get("title")) or "Untitled",
        abstract=normalize_text(entry.get("summary")),
        authors=[author.name for author in author_details],
        author_details=author_details,
        published=normalize_text(entry.get("published")) or normalize_text(entry.get("updated")),
        updated=normalize_text(entry.get("updated")),
        doi=doi,
        venue="arXiv",
        url=normalize_text(entry.get("id")),
        pdf_url=pdf_url,
        is_open_access=True,
        primary_subject=primary_subject,
        publication_types=["Preprint"],
        journal_reference=normalize_text(entry.get("arxiv_journal_ref")),
        subjects=[
            subject
            for subject in (
                normalize_text(tag.get("term")) for tag in (entry.get("tags") or [])
            )
            if subject
        ],
        external_ids=external_ids,
        source_metadata=source_metadata,
    )


def normalize_crossref_author(raw_author: dict[str, Any]) -> Author:
    direct_name = normalize_text(raw_author.get("name"))
    if direct_name:
        name = direct_name
    else:
        given = normalize_text(raw_author.get("given"))
        family = normalize_text(raw_author.get("family"))
        name = " ".join(part for part in (given, family) if part) or "Unknown author"

    affiliations: list[str] = []
    for affiliation in raw_author.get("affiliation") or []:
        if isinstance(affiliation, dict):
            normalized_affiliation = normalize_text(affiliation.get("name"))
        else:
            normalized_affiliation = normalize_text(affiliation)
        if normalized_affiliation:
            affiliations.append(normalized_affiliation)

    orcid = parse_orcid(raw_author.get("ORCID"))
    external_ids: dict[str, Any] = {}
    if orcid:
        external_ids["ORCID"] = orcid

    return Author(
        name=name,
        affiliations=affiliations,
        orcid=orcid,
        external_ids=external_ids,
    )


def normalize_crossref_work(
    raw_work: dict[str, Any],
    *,
    extra_metadata: dict[str, Any] | None = None,
) -> Paper:
    doi = normalize_text(raw_work.get("DOI"))
    source_id = doi or normalize_text(raw_work.get("URL")) or "unknown"

    author_details = [
        normalize_crossref_author(author)
        for author in (raw_work.get("author") or [])
    ]

    published = (
        date_parts_to_iso(raw_work.get("published-print"))
        or date_parts_to_iso(raw_work.get("published-online"))
        or date_parts_to_iso(raw_work.get("issued"))
        or date_parts_to_iso(raw_work.get("created"))
    )

    updated = date_parts_to_iso(raw_work.get("indexed")) or date_parts_to_iso(raw_work.get("deposited"))

    license_urls = [
        license_url
        for license_url in (
            normalize_text(item.get("URL")) for item in (raw_work.get("license") or [])
        )
        if license_url
    ]
    link_urls = [
        link_url
        for link_url in (
            normalize_text(item.get("URL")) for item in (raw_work.get("link") or [])
        )
        if link_url
    ]
    pdf_url = next(
        (
            normalize_text(item.get("URL"))
            for item in (raw_work.get("link") or [])
            if normalize_text(item.get("content-type")) == "application/pdf"
        ),
        None,
    )

    funders = [
        funder_name
        for funder_name in (
            normalize_text(funder.get("name")) for funder in (raw_work.get("funder") or [])
        )
        if funder_name
    ]

    external_ids: dict[str, str] = {}
    if doi:
        external_ids["DOI"] = doi

    source_metadata: dict[str, Any] = {}
    relation = raw_work.get("relation") or {}
    if relation:
        source_metadata["relation"] = relation
    if license_urls:
        source_metadata["license_urls"] = license_urls
    if link_urls:
        source_metadata["link_urls"] = link_urls
    issn = normalize_text_list(raw_work.get("ISSN"))
    if issn:
        source_metadata["issn"] = issn
    if extra_metadata:
        for key, value in extra_metadata.items():
            if value not in (None, [], {}, ""):
                source_metadata[key] = value

    return Paper(
        source="crossref",
        source_id=source_id,
        title=first_text(raw_work.get("title")) or "Untitled",
        abstract=normalize_text(raw_work.get("abstract")),
        authors=[author.name for author in author_details],
        author_details=author_details,
        published=published,
        updated=updated,
        doi=doi,
        venue=first_text(raw_work.get("container-title")),
        publisher=normalize_text(raw_work.get("publisher")),
        url=normalize_text(raw_work.get("URL")),
        pdf_url=pdf_url,
        citation_count=coerce_int(raw_work.get("is-referenced-by-count")),
        license=license_urls[0] if license_urls else None,
        primary_subject=first_text(raw_work.get("subject")),
        publication_types=normalize_text_list(raw_work.get("type")),
        funders=funders,
        subjects=[
            subject
            for subject in (
                normalize_text(value) for value in (raw_work.get("subject") or [])
            )
            if subject
        ],
        external_ids=external_ids,
        source_metadata=source_metadata,
    )