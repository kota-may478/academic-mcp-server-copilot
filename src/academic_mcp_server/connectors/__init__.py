"""API connectors for supported paper providers."""

from academic_mcp_server.connectors.arxiv import ArxivConnector
from academic_mcp_server.connectors.crossref import CrossrefConnector
from academic_mcp_server.connectors.semantic_scholar import SemanticScholarConnector

__all__ = [
    "ArxivConnector",
    "CrossrefConnector",
    "SemanticScholarConnector",
]