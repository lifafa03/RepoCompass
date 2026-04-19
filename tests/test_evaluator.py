"""Tests for the evaluation metrics."""
import pytest
from app.schemas import (
    ArchitectureExplainer, Component, SystemObservation,
    APIMap, APIEndpoint, CallFlowSummary, CallFlow, FlowStep,
    RiskNotes, RiskNote, EvidenceRef,
)
from evaluators.metrics import (
    evaluate_api_map, evaluate_groundedness, measure_pipeline_stats,
    run_full_evaluation, FullEvaluation,
)


class TestAPIMapEvaluation:
    def test_perfect_match(self):
        predicted = APIMap(framework="fastapi", endpoints=[
            APIEndpoint(method="GET", route="/users", evidence=[EvidenceRef(file_path="a.py", line_start=1, line_end=5, snippet_id="s1")]),
            APIEndpoint(method="POST", route="/users", evidence=[EvidenceRef(file_path="a.py", line_start=6, line_end=10, snippet_id="s2")]),
        ])
        ground_truth = APIMap(framework="fastapi", endpoints=[
            APIEndpoint(method="GET", route="/users"),
            APIEndpoint(method="POST", route="/users"),
        ])
        result = evaluate_api_map(predicted, ground_truth)
        assert result.precision == 1.0
        assert result.recall == 1.0
        assert result.f1 == 1.0
        assert result.true_positives == 2

    def test_partial_match(self):
        predicted = APIMap(framework="fastapi", endpoints=[
            APIEndpoint(method="GET", route="/users"),
            APIEndpoint(method="DELETE", route="/users"),
        ])
        ground_truth = APIMap(framework="fastapi", endpoints=[
            APIEndpoint(method="GET", route="/users"),
            APIEndpoint(method="POST", route="/users"),
        ])
        result = evaluate_api_map(predicted, ground_truth)
        assert result.true_positives == 1
        assert result.false_positives == 1
        assert result.false_negatives == 1

    def test_empty_predictions(self):
        predicted = APIMap(framework="fastapi")
        ground_truth = APIMap(framework="fastapi", endpoints=[APIEndpoint(method="GET", route="/health")])
        result = evaluate_api_map(predicted, ground_truth)
        assert result.recall == 0.0
        assert result.false_negatives == 1


class TestGroundednessEvaluation:
    def test_all_grounded(self):
        arch = ArchitectureExplainer(summary="test", components=[Component(name="X", role="Y", evidence=[EvidenceRef(file_path="a.py", line_start=1, line_end=5, snippet_id="s1")], confidence="high")])
        result = evaluate_groundedness(arch, APIMap(framework="fastapi"), CallFlowSummary(), RiskNotes())
        assert result.total_claims == 1
        assert result.claims_with_evidence == 1
        assert result.unsupported_rate == 0.0

    def test_no_evidence(self):
        arch = ArchitectureExplainer(summary="test", components=[Component(name="X", role="Y", evidence=[], confidence="low")], system_observations=[SystemObservation(claim="obs", evidence=[], confidence="low")])
        result = evaluate_groundedness(arch, APIMap(framework="fastapi"), CallFlowSummary(), RiskNotes())
        assert result.unsupported_rate == 1.0

    def test_confidence_distribution(self):
        arch = ArchitectureExplainer(summary="test", components=[
            Component(name="A", role="r", evidence=[EvidenceRef(file_path="a", line_start=1, line_end=1, snippet_id="s")], confidence="high"),
            Component(name="B", role="r", evidence=[], confidence="low"),
        ])
        result = evaluate_groundedness(arch, APIMap(framework="fastapi"), CallFlowSummary(), RiskNotes())
        assert result.confidence_distribution["high"] == 1
        assert result.confidence_distribution["low"] == 1


class TestResourceTracking:
    def test_measures_stats(self):
        stats = {"ingest_seconds": 0.5, "embed_seconds": 2.3, "gen_seconds": 5.1}
        report = measure_pipeline_stats(stats, chunks_count=100, api_endpoints=5, risk_notes=3)
        assert report.total_seconds == 7.9
        assert report.chunks_indexed == 100

    def test_empty_stats(self):
        report = measure_pipeline_stats({})
        assert report.total_seconds == 0


class TestFullEvaluation:
    def test_run_without_ground_truth(self):
        arch = ArchitectureExplainer(summary="test")
        result = run_full_evaluation(arch, APIMap(framework="fastapi"), CallFlowSummary(), RiskNotes(), {})
        assert result.api_metrics is None
        assert result.groundedness is not None

    def test_save_and_load(self, tmp_path):
        arch = ArchitectureExplainer(summary="test")
        result = run_full_evaluation(arch, APIMap(framework="fastapi"), CallFlowSummary(), RiskNotes(), {"ingest_seconds": 1.0})
        path = tmp_path / "eval.json"
        result.save(path)
        loaded = FullEvaluation.load(path)
        assert loaded.resources.total_seconds == 1.0
