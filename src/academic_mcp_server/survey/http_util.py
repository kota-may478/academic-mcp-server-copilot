"""Backward-compatible re-exports; use api_gateway for new code."""
from __future__ import annotations

from academic_mcp_server.survey.api_gateway import (
    CR_API_BASE,
    OA_API_BASE,
    SS_GRAPH,
    append_openalex_auth,
    fetch_openalex_abstract,
    fetch_ss_abstract,
    http_get_json,
    oa_get_path,
    openalex_query_suffix,
    polite_sleep,
    ss_get_path,
    survey_api_lock,
)

# Legacy name used by enrich.py
openalex_mailto_param = openalex_query_suffix

__all__ = [
    "CR_API_BASE",
    "OA_API_BASE",
    "SS_GRAPH",
    "append_openalex_auth",
    "fetch_openalex_abstract",
    "fetch_ss_abstract",
    "http_get_json",
    "oa_get_path",
    "openalex_mailto_param",
    "openalex_query_suffix",
    "polite_sleep",
    "ss_get_path",
    "survey_api_lock",
]
