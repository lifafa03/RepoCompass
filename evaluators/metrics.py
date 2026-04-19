"""Evaluation metrics for RepoCompass.

Provides:
- API extraction precision/recall/F1
- Groundedness scoring (citation coverage, unsupported claim rate)
- Runtime/resource tracking
"""
import time
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

from app.schemas import (
    ArchitectureExplainer, APIMap, CallFlowSummary, RiskNotes,
    APIEndpoint, EvidenceRef, Component, SystemObservation,
)


@dataclass
class APIMapMetrics:
    """Evaluation metrics for API endpoint extraction."""
    precision: float
    recall: float
    f1: float
    true_positives: int
    false_positives: int
    false_negatives: int
    details: list[dict] = field(default_factory=list)


def _endpoint_key(ep: APIEndpoint) -> str:
    """Normalize an endpoint to a (method, route) key for matching."""
    return f"{ep.method} {ep.route}"


def evaluate_api_map(predicted: APIMap, ground_truth: APIMap) -> APIMapMetrics:
    """Compare predicted API map against ground truth."""
    pred_keys = {_endpoint_key(ep) for ep in predicted.endpoints}
    gt_keys = {_endpoint_key(ep) for ep in ground_truth.endpoints}
    tp = len(pred_keys & gt_keys)
    fp = len(pred_keys - gt_keys)
    fn = len(gt_keys - pred_keys)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    details = []
    for ep in predicted.endpoints:
        key = _endpoint_key(ep)
        details.append({"endpoint": key, "match": key in gt_keys, "confidence": ep.confidence, "has_evidence": len(ep.evidence) > 0})
    return APIMapMetrics(precision=round(precision, 4), recall=round(recall, 4), f1=round(f1, 4), true_positives=tp, false_positives=fp, false_negatives=fn, details=details)


@dataclass
class GroundednessReport:
    total_claims: int
    claims_with_evidence: int
    claims_without_evidence: int
    unsupported_rate: float
    avg_evidence_per_claim: float
    confidence_distribution: dict[str, int] = field(default_factory=dict)
    details: list[dict] = field(default_factory=list)


def _count_evidenced(items: list, get_evidence, get_confidence, get_name) -> list[dict]:
    details = []
    for item in items:
        evidence = get_evidence(item)
        details.append({"name": get_name(item), "has_evidence": len(evidence) > 0, "evidence_count": len(evidence), "confidence": get_confidence(item)})
    return details


def evaluate_groundedness(architecture: ArchitectureExplainer, api_map: APIMap, callflow: CallFlowSummary, risk_notes: RiskNotes) -> GroundednessReport:
    all_details = []
    conf_dist = {"high": 0, "medium": 0, "low": 0}
    all_details.extend(_count_evidenced(architecture.components, lambda c: c.evidence, lambda c: c.confidence, lambda c: c.name))
    all_details.extend(_count_evidenced(architecture.system_observations, lambda o: o.evidence, lambda o: o.confidence, lambda o: o.claim[:60]))
    all_details.extend(_count_evidenced(api_map.endpoints, lambda e: e.evidence, lambda e: e.confidence, lambda e: f"{e.method} {e.route}"))
    for flow in callflow.flows:
        all_details.extend(_count_evidenced(flow.steps, lambda s: s.evidence, lambda s: s.confidence, lambda s: f"Step {s.step_number}"))
    all_details.extend(_count_evidenced(risk_notes.risk_notes, lambda n: n.evidence, lambda n: n.confidence, lambda n: n.title))
    total = len(all_details)
    with_evidence = sum(1 for d in all_details if d["has_evidence"])
    without_evidence = total - with_evidence
    total_evidence_items = sum(d["evidence_count"] for d in all_details)
    for d in all_details:
        conf = d["confidence"]
        conf_dist[conf] = conf_dist.get(conf, 0) + 1
    return GroundednessReport(
        total_claims=total, claims_with_evidence=with_evidence, claims_without_evidence=without_evidence,
        unsupported_rate=round(without_evidence / total, 4) if total > 0 else 0.0,
        avg_evidence_per_claim=round(total_evidence_items / total, 2) if total > 0 else 0.0,
        confidence_distribution=conf_dist, details=all_details,
    )


@dataclass
class ResourceReport:
    total_seconds: float
    phase_timings: dict[str, float] = field(default_factory=dict)
    chunks_indexed: int = 0
    endpoints_extracted: int = 0
    risk_notes_count: int = 0
    memory_peak_mb: Optional[float] = None


def measure_pipeline_stats(pipeline_stats: dict, chunks_count: int = 0, api_endpoints: int = 0, risk_notes: int = 0) -> ResourceReport:
    total = sum(v for k, v in pipeline_stats.items() if k.endswith("_seconds"))
    return ResourceReport(total_seconds=round(total, 2), phase_timings=pipeline_stats, chunks_indexed=chunks_count, endpoints_extracted=api_endpoints, risk_notes_count=risk_notes)


@dataclass
class FullEvaluation:
    api_metrics: Optional[APIMapMetrics] = None
    groundedness: Optional[GroundednessReport] = None
    resources: Optional[ResourceReport] = None
    def to_dict(self) -> dict:
        import dataclasses
        return dataclasses.asdict(self)
    def save(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)
    @classmethod
    def load(cls, path: Path) -> "FullEvaluation":
        with open(path) as f:
            data = json.load(f)
        return cls(
            api_metrics=APIMapMetrics(**data["api_metrics"]) if data.get("api_metrics") else None,
            groundedness=GroundednessReport(**data["groundedness"]) if data.get("groundedness") else None,
            resources=ResourceReport(**data["resources"]) if data.get("resources") else None,
        )


def run_full_evaluation(architecture, api_map, callflow, risk_notes, pipeline_stats, ground_truth_api=None, chunks_count=0) -> FullEvaluation:
    api_metrics = evaluate_api_map(api_map, ground_truth_api) if ground_truth_api is not None else None
    groundedness = evaluate_groundedness(architecture, api_map, callflow, risk_notes)
    resources = measure_pipeline_stats(pipeline_stats, chunks_count, len(api_map.endpoints), len(risk_notes.risk_notes))
    return FullEvaluation(api_metrics=api_metrics, groundedness=groundedness, resources=resources)
