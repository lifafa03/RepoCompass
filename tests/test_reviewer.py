"""Tests for the reviewer agent."""
from app.schemas import (
    ArchitectureExplainer, Component, SystemObservation,
    APIMap, APIEndpoint, CallFlowSummary, CallFlow, EvidenceRef,
)
from agents.reviewer import review_architecture, review_api_map, generate_risk_notes


class TestReviewArchitecture:
    def test_downgrades_no_evidence(self):
        arch = ArchitectureExplainer(summary="test", components=[Component(name="X", role="Y", evidence=[], confidence="high")])
        result = review_architecture(arch)
        assert result.components[0].confidence == "low"
    def test_keeps_evidence_backed(self):
        arch = ArchitectureExplainer(summary="test", components=[Component(name="X", role="Y", evidence=[EvidenceRef(file_path="a.py", line_start=1, line_end=5, snippet_id="s1")], confidence="high")])
        result = review_architecture(arch)
        assert result.components[0].confidence == "high"


class TestReviewApiMap:
    def test_flags_no_evidence(self):
        api_map = APIMap(framework="fastapi", endpoints=[APIEndpoint(method="GET", route="/test", evidence=[])])
        result = review_api_map(api_map)
        assert result.endpoints[0].confidence == "low"
    def test_flags_no_handler(self):
        api_map = APIMap(framework="fastapi", endpoints=[APIEndpoint(method="GET", route="/test", handler_name=None, evidence=[EvidenceRef(file_path="a.py", line_start=1, line_end=5, snippet_id="s1")])])
        result = review_api_map(api_map)
        assert "resolved" in (result.endpoints[0].uncertainty_note or "").lower()


class TestRiskNotes:
    def test_generates_notes_for_low_confidence(self):
        arch = ArchitectureExplainer(summary="test", components=[Component(name="X", role="Y", evidence=[], confidence="low")])
        notes = generate_risk_notes(arch, APIMap(framework="fastapi"), CallFlowSummary())
        assert len(notes.risk_notes) >= 1
