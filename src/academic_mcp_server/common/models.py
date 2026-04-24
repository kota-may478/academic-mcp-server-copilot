from __future__ import annotations

from typing import Literal

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
    published: str | None = None
    doi: str | None = None
    venue: str | None = None
    url: str | None = None
    pdf_url: str | None = None
    citation_count: int | None = None
    subjects: list[str] = Field(default_factory=list)
    external_ids: dict[str, str] = Field(default_factory=dict)


class PaperSearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: PaperSource
    query: str
    limit: int
    total: int | None = None
    items: list[Paper] = Field(default_factory=list)


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