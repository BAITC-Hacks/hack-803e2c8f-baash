"""Generate synthetic-only M4 judged-set and duplicate diagnostics."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/core/src"))

from pulse109.retrieval.models import AppealDocument, RetrievalQuery  # noqa: E402
from pulse109.retrieval.service import HybridRetriever  # noqa: E402


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
    reciprocal_rank = []
    latencies = []
    for query_id, expected_id, _ in judged:
        started = time.perf_counter()
        results = retriever.similar(
            RetrievalQuery(
                request_id=UUID(query_id), region_id="ALA" if query_id.endswith("1") else "AST"
            )
        )
        latencies.append((time.perf_counter() - started) * 1000)
        ranked_ids = [str(item.request_id) for item in results]
        if expected_id in ranked_ids[:10]:
            hits += 1
            reciprocal_rank.append(1 / (ranked_ids.index(expected_id) + 1))
        else:
            reciprocal_rank.append(0.0)
    duplicate_results = retriever.duplicate_candidates(
        RetrievalQuery(request_id=UUID("10000000-0000-0000-0000-000000000001"), region_id="ALA")
    )
    report = {
        "synthetic_only": True,
        "warning": "Fixture diagnostics only; no real-world quality claim.",
        "judged_queries": len(judged),
        "recall_at_10": hits / len(judged),
        "mrr": sum(reciprocal_rank) / len(reciprocal_rank),
        "latency_ms": {
            "count": len(latencies),
            "max": max(latencies),
            "mean": sum(latencies) / len(latencies),
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
