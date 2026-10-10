"""Unit tests for Feature 2: Multi-Agent LLM Stakeholder Debate."""

import pytest
from bioradar.ai.debate import run_debate, AGENT_PERSONAS


def test_agent_personas():
    """Verifies that all 4 required stakeholder personas are defined."""
    assert len(AGENT_PERSONAS) == 4
    assert "forest_officer" in AGENT_PERSONAS
    assert "local_fisherman" in AGENT_PERSONAS
    assert "conservation_ngo" in AGENT_PERSONAS
    assert "government_regulator" in AGENT_PERSONAS


def test_run_debate():
    """Tests execution of 6-round multi-agent debate and consensus synthesis."""
    res = run_debate("BR-GOA-001", topic="Mandovi Estuary Conservation Strategy", rounds=6)
    assert res["status"] == "COMPLETED"
    assert "debate_id" in res
    assert res["sample_id"] == "BR-GOA-001"
    assert len(res["messages"]) == 6
    assert "consensus" in res
    assert "consensus_recommendation" in res["consensus"]
    assert len(res["consensus"]["dissenting_opinions"]) >= 1
