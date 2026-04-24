from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

PaperSource = Literal["semantic_scholar", "arxiv", "crossref"]
SUPPORTED_SOURCES: tuple[PaperSource, ...] = (
    "semantic_scholar",
    "arxiv",
    "crossref",
)


class Paper(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: PaperSource
    source_id: str = Field(description="Identifier in the upstream source.")
    title: str
    abstract: str | None = None
    authors: list[str] = Field(default_factory=list)
    author_details: list["Author"] = Field(default_factory=list)
    published: str | None = None
    updated: str | None = None
    doi: str | None = None
    venue: str | None = None
    publisher: str | None = None
    url: str | None = None
    pdf_url: str | None = None
    citation_count: int | None = None
    reference_count: int | None = None
    influential_citation_count: int | None = None
    is_open_access: bool | None = None
    license: str | None = None
    primary_subject: str | None = None
    publication_types: list[str] = Field(default_factory=list)
    journal_reference: str | None = None
    funders: list[str] = Field(default_factory=list)
    subjects: list[str] = Field(default_factory=list)
    external_ids: dict[str, Any] = Field(default_factory=dict)
    source_metadata: dict[str, Any] = Field(default_factory=dict)


class Author(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    author_id: str | None = None
    affiliations: list[str] = Field(default_factory=list)
    orcid: str | None = None
    url: str | None = None
    homepage: str | None = None
    paper_count: int | None = None
    citation_count: int | None = None
    h_index: int | None = None
    external_ids: dict[str, Any] = Field(default_factory=dict)


class PaperSearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: PaperSource
    query: str
    limit: int
    total: int | None = None
    items: list[Paper] = Field(default_factory=list)


class PaperCollectionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: PaperSource
    kind: str
    query: str | None = None
    identifier: str | None = None
    limit: int | None = None
    offset: int | None = None
    next_offset: int | None = None
    total: int | None = None
    items: list[Paper] = Field(default_factory=list)


class AuthorCollectionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: Literal["semantic_scholar"]
    kind: str
    query: str | None = None
    identifier: str | None = None
    limit: int | None = None
    offset: int | None = None
    next_offset: int | None = None
    total: int | None = None
    items: list[Author] = Field(default_factory=list)


class SourceError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: PaperSource
    message: str


class UnifiedSearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    sources: list[PaperSource]
    limit_per_source: int
    items: list[Paper] = Field(default_factory=list)
    errors: list[SourceError] = Field(default_factory=list)


Paper.model_rebuild()