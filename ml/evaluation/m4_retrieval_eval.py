"""Generate synthetic-only M4 judged-set and duplicate diagnostics."""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/core/src"))

from pulse109.retrieval.models import AppealDocument, RetrievalQuery  # noqa: E402
from pulse109.retrieval.service import HybridRetriever  # noqa: E402


def _percentile95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, max(0, math.ceil(len(ordered) * 0.95) - 1))]


def _ndcg_at_10(results: list[tuple[str, int]]) -> float:
    ranked = results[:10]
    dcg = sum(relevance / math.log2(rank + 2) for rank, (_, relevance) in enumerate(ranked))
    ideal = sorted((relevance for _, relevance in results), reverse=True)[:10]
    idcg = sum(relevance / math.log2(rank + 2) for rank, relevance in enumerate(ideal))
    return dcg / idcg if idcg else 0.0


def _pair_metrics(
    predicted: set[tuple[str, str]], expected: set[tuple[str, str]]
) -> dict[str, float]:
    true_positive = len(predicted & expected)
    precision = true_positive / len(predicted) if predicted else 0.0
    recall = true_positive / len(expected) if expected else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "precision": round(precision, 8),
        "recall": round(recall, 8),
        "f1": round(f1, 8),
    }


def _canonical_pair(left: str, right: str) -> tuple[str, str]:
    return (left, right) if left <= right else (right, left)


def _bcubed_f1(
    item_ids: set[str], true_pairs: set[tuple[str, str]], predicted_pairs: set[tuple[str, str]]
) -> dict[str, float]:
    def clusters(pairs: set[tuple[str, str]]) -> dict[str, set[str]]:
        groups: list[set[str]] = []
        for left, right in pairs:
            group = next((item for item in groups if left in item or right in item), None)
            if group is None:
                groups.append({left, right})
            else:
                group.update((left, right))
        result: dict[str, set[str]] = {item: {item} for item in item_ids}
        for group in groups:
            for item in group:
                result[item] = group
        return result

    true_clusters = clusters(true_pairs)
    predicted_clusters = clusters(predicted_pairs)
    precisions: list[float] = []
    recalls: list[float] = []
    for item in sorted(item_ids):
        overlap = len(true_clusters[item] & predicted_clusters[item])
        precisions.append(overlap / len(predicted_clusters[item]))
        recalls.append(overlap / len(true_clusters[item]))
    precision = sum(precisions) / len(precisions)
    recall = sum(recalls) / len(recalls)
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "precision": round(precision, 8),
        "recall": round(recall, 8),
        "f1": round(f1, 8),
    }


def _documents() -> list[AppealDocument]:
    rows = [
        (
            "10000000-0000-0000-0000-000000000001",
            "ALA",
            "water",
            "water leak near a building",
            "water fixed",
            "water-1",
        ),
        (
            "10000000-0000-0000-0000-000000000002",
            "ALA",
            "water",
            "water pipe leak near a building",
            "water fixed",
            "water-2",
        ),
        (
            "10000000-0000-0000-0000-000000000003",
            "ALA",
            "road",
            "road surface damaged near a school",
            "road repaired",
            "road-1",
        ),
        (
            "10000000-0000-0000-0000-000000000004",
            "AST",
            "road",
            "large road pothole near school",
            "road repaired",
            "road-2",
        ),
        (
            "10000000-0000-0000-0000-000000000005",
            "AST",
            "road",
            "large road pothole near school",
            "road repaired",
            "road-3",
        ),
        (
            "10000000-0000-0000-0000-000000000006",
            "AST",
            "waste",
            "waste containers were full",
            "waste collected",
            "waste-1",
        ),
    ]
    unresolved_sources = {
        "10000000-0000-0000-0000-000000000001",
        "10000000-0000-0000-0000-000000000004",
    }
    return [
        AppealDocument(
            request_id=UUID(request_id),
            region_id=region,
            service_id=f"service:{service}",
            topic_id=f"topic:{service}",
            redacted_text=text,
            resolved=request_id not in unresolved_sources,
            outcome_summary=outcome if request_id not in unresolved_sources else None,
            outcome_ref=(
                f"synthetic://resolution/{ref}" if request_id not in unresolved_sources else None
            ),
            data_classification="synthetic",
        )
        for request_id, region, service, text, outcome, ref in rows
    ]


def generate(output: Path) -> None:
    retriever = HybridRetriever(_documents())
    judged = [
        ("10000000-0000-0000-0000-000000000001", "10000000-0000-0000-0000-000000000002", 2),
        ("10000000-0000-0000-0000-000000000004", "10000000-0000-0000-0000-000000000005", 2),
    ]
    hits = 0
    hits20 = 0
    reciprocal_rank = []
    latencies = []
    ndcg_scores = []
    pair_judgements = [
        ("10000000-0000-0000-0000-000000000001", "10000000-0000-0000-0000-000000000002", True),
        ("10000000-0000-0000-0000-000000000004", "10000000-0000-0000-0000-000000000005", True),
        ("10000000-0000-0000-0000-000000000001", "10000000-0000-0000-0000-000000000003", False),
    ]
    expected_pairs = {
        _canonical_pair(left, right)
        for left, right, is_duplicate in pair_judgements
        if is_duplicate
    }
    predicted_pairs: set[tuple[str, str]] = set()
    for query_id, expected_id, _ in judged:
        started = time.perf_counter()
        results = retriever.similar(
            RetrievalQuery(
                request_id=UUID(query_id), region_id="ALA" if query_id.endswith("1") else "AST"
            )
        )
        latencies.append((time.perf_counter() - started) * 1000)
        ranked_ids = [str(item.request_id) for item in results]
        relevance = {candidate: (2 if candidate == expected_id else 0) for candidate in ranked_ids}
        ndcg_scores.append(
            _ndcg_at_10([(candidate, relevance[candidate]) for candidate in ranked_ids])
        )
        if expected_id in ranked_ids[:10]:
            hits += 1
            reciprocal_rank.append(1 / (ranked_ids.index(expected_id) + 1))
        else:
            reciprocal_rank.append(0.0)
        if expected_id in ranked_ids[:20]:
            hits20 += 1
    for left, right, _ in pair_judgements:
        duplicate_ids = {
            str(item.candidate_id)
            for item in retriever.duplicate_candidates(
                RetrievalQuery(
                    request_id=UUID(left), region_id="ALA" if left.endswith("1") else "AST"
                )
            )
        }
        if right in duplicate_ids:
            predicted_pairs.add(_canonical_pair(left, right))
    pair_metrics = _pair_metrics(predicted_pairs, expected_pairs)
    item_ids = {str(document.request_id) for document in _documents()}
    cluster_metrics = _bcubed_f1(item_ids, expected_pairs, predicted_pairs)
    duplicate_results = retriever.duplicate_candidates(
        RetrievalQuery(request_id=UUID("10000000-0000-0000-0000-000000000001"), region_id="ALA")
    )
    report = {
        "synthetic_only": True,
        "warning": "Fixture diagnostics only; no real-world quality claim.",
        "judged_queries": len(judged),
        "recall_at_10": hits / len(judged),
        "recall_at_20": hits20 / len(judged),
        "mrr": sum(reciprocal_rank) / len(reciprocal_rank),
        "ndcg_at_10": round(sum(ndcg_scores) / len(ndcg_scores), 8),
        "latency_ms": {
            "count": len(latencies),
            "max": max(latencies),
            "mean": sum(latencies) / len(latencies),
            "p95": _percentile95(latencies),
        },
        "duplicate_pair_metrics": {
            "expected_count": len(expected_pairs),
            "predicted_count": len(predicted_pairs),
            **pair_metrics,
        },
        "incident_level_b_cubed": {
            "item_count": len(item_ids),
            **cluster_metrics,
        },
        "duplicate_pair": {
            "candidate_count": len(duplicate_results),
            "all_require_human_confirmation": all(
                item.needs_human_confirmation for item in duplicate_results
            ),
            "candidate_ids": [str(item.candidate_id) for item in duplicate_results],
        },
        "fallback": "deterministic hash vector plus lexical overlap; no external model",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", type=Path, default=Path("ml/evaluation/synthetic_m4/retrieval_report.json")
    )
    args = parser.parse_args()
    generate(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
