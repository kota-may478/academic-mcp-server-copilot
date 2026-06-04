from __future__ import annotations

import os
from dataclasses import dataclass
from email.utils import parseaddr

from academic_mcp_server import __version__


def _clean_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None

    cleaned = value.strip()
    return cleaned or None


def _parse_positive_number(name: str, default: float) -> float:
    raw_value = _clean_env(name)
    if raw_value is None:
        return default

    try:
        parsed_value = float(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a valid number.") from exc

    if parsed_value <= 0:
        raise RuntimeError(f"{name} must be greater than zero.")

    return parsed_value


def _parse_email(name: str) -> str:
    raw_value = _clean_env(name)
    if raw_value is None:
        raise RuntimeError(
            f"{name} is required. Configure it through VS Code MCP inputs or environment variables."
        )

    _, parsed_email = parseaddr(raw_value)
    if "@" not in parsed_email:
        raise RuntimeError(f"{name} must be a valid email address.")

    return parsed_email


def _parse_optional_email(name: str) -> str | None:
    raw_value = _clean_env(name)
    if raw_value is None:
        return None

    _, parsed_email = parseaddr(raw_value)
    if "@" not in parsed_email:
        raise RuntimeError(f"{name} must be a valid email address.")

    return parsed_email


def _parse_required_token(name: str) -> str:
    raw_value = _clean_env(name)
    if raw_value is None:
        raise RuntimeError(
            f"{name} is required. Configure it through VS Code MCP inputs or environment variables."
        )
    return raw_value


@dataclass(frozen=True, slots=True)
class AppConfig:
    semantic_scholar_api_key: str
    contact_email: str
    openalex_contact_email: str
    openalex_api_key: str | None
    request_timeout_seconds: float
    arxiv_export_query_timeout_seconds: float
    cache_ttl_seconds: int
    default_limit: int

    @classmethod
    def from_env(cls) -> "AppConfig":
        request_timeout_seconds = _parse_positive_number(
            "ACADEMIC_MCP_REQUEST_TIMEOUT_SECONDS",
            20.0,
        )
        return cls(
            semantic_scholar_api_key=_parse_required_token(
                "ACADEMIC_MCP_SEMANTIC_SCHOLAR_API_KEY"
            ),
            contact_email=_parse_email("ACADEMIC_MCP_CONTACT_EMAIL"),
            openalex_contact_email=(
                _parse_optional_email("ACADEMIC_MCP_OPENALEX_CONTACT_EMAIL")
                or _parse_email("ACADEMIC_MCP_CONTACT_EMAIL")
            ),
            openalex_api_key=_clean_env("OPENALEX_API_KEY")
            or _clean_env("ACADEMIC_MCP_OPENALEX_API_KEY"),
            request_timeout_seconds=request_timeout_seconds,
            arxiv_export_query_timeout_seconds=max(
                request_timeout_seconds,
                _parse_positive_number(
                    "ACADEMIC_MCP_ARXIV_EXPORT_QUERY_TIMEOUT_SECONDS",
                    60.0,
                ),
            ),
            cache_ttl_seconds=int(
                _parse_positive_number("ACADEMIC_MCP_CACHE_TTL_SECONDS", 300.0)
            ),
            default_limit=int(
                _parse_positive_number("ACADEMIC_MCP_DEFAULT_LIMIT", 10.0)
            ),
        )

    @property
    def semantic_scholar_headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "x-api-key": self.semantic_scholar_api_key,
        }

    @property
    def crossref_headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "User-Agent": f"academic-mcp-server/{__version__} (mailto:{self.contact_email})",
        }

    @property
    def openalex_headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "User-Agent": (
                f"academic-mcp-server/{__version__} "
                f"(mailto:{self.openalex_contact_email})"
            ),
        }