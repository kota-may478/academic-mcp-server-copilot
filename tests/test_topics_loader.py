"""Regression tests for survey topics_module loading and taxonomy alignment."""
from __future__ import annotations

import pytest

from academic_mcp_server.survey.topics_loader import (
    TopicsConfigError,
    load_topics_symbols,
    topics_module_from_cfg,
    validate_topic_taxonomy_alignment,
)


def test_topics_module_required():
    with pytest.raises(TopicsConfigError):
        topics_module_from_cfg({})


def test_load_oma_topics():
    cfg = {"topics_module": "academic_mcp_server.survey.topics_operational_modal_uav"}
    _, _, topics, _, assign = load_topics_symbols(cfg)
    assert "T1" in topics
    assert callable(assign)


def test_validate_detects_ipt_headings_with_oma_module():
    cfg = {"topics_module": "academic_mcp_server.survey.topics_operational_modal_uav"}
    article = "\n".join(
        [
            "## Section 4 Topic taxonomy",
            "### 飛行中・ホバリングIPT",
            "body",
            "## Section 5",
        ]
    )
    errs = validate_topic_taxonomy_alignment(cfg, article)
    assert errs
    assert "IPT" in errs[0]


def test_validate_ok_for_oma_headings():
    cfg = {"topics_module": "academic_mcp_server.survey.topics_operational_modal_uav"}
    article = "\n".join(
        [
            "## Section 4 Topic taxonomy",
            "### OMA理論・識別アルゴリズム",
            "body",
            "## Section 5",
        ]
    )
    assert validate_topic_taxonomy_alignment(cfg, article) == []


if __name__ == "__main__":
    test_topics_module_required()
    test_load_oma_topics()
    test_validate_detects_ipt_headings_with_oma_module()
    test_validate_ok_for_oma_headings()
    print("topics_loader tests: ok")
