"""End-to-end case walkthrough that composes the three modules on real data.

This is the product thesis made executable: one appeal flows through the whole
operational contour and every downstream number comes from a real artifact
built earlier, not a mock.

  intake        an appeal arrives with region, a topic hint and a timestamp
  routing       predict the responsible service, with a confidence decision
                that either auto-routes or hands the case to an operator
  assist        retrieve resolved cases handled the same way, real executor
                texts ranked by the fine-tuned model where it is present
  situation     is this appeal part of a surge for its region and day
  forecast      the load forecast and the staffing it implies

One honesty boundary, stated in the trace itself: no citizen text exists in the
data (D-018), so the intake free text is illustrative and marked as such. Every
number after it, the routing decision, the retrieved cases, the surge, the
forecast, is computed from real records and real models.

Usage:
    python ml/training/demo_scenario.py \
        --canonical build/ingest/canonical.jsonl \
        --corpus ml/datasets/regional_retrieval_corpus_v1.jsonl \
        --reports ml/evaluation --out ml/evaluation/demo_v1
"""

from __future__ import annotations

import argparse
import json
import pathlib
from collections import Counter
from datetime import UTC, datetime

TOP_K = 3
CONFIDENCE_ROUTE = 0.60  # at or above, propose the route. below, send to operator


def load_canonical(path):
    rows = []
    for line in open(path, encoding="utf-8"):
        rec = json.loads(line)
        a = rec["intake"]["selected_attributes"]
        received = rec["time"]["received_at"]
        if not a["topic_label"] or not a["service_label"] or not received:
            continue
        rows.append(
            {
                "region": rec["source"]["region_id"],
                "topic": a["topic_label"],
                "service": a["service_label"],
                "received": received[:10],
            }
        )
    return rows


def routing_decision(rows, region, topic):
    """Distribution of services for (region, topic), the real routing table."""
    dist = Counter(r["service"] for r in rows if r["region"] == region and r["topic"] == topic)
    if not dist:
        dist = Counter(r["service"] for r in rows if r["topic"] == topic)
    total = sum(dist.values()) or 1
    ranked = [{"service": s, "confidence": round(c / total, 3)} for s, c in dist.most_common(TOP_K)]
    top = ranked[0]["confidence"] if ranked else 0.0
    decision = "auto_route_proposed" if top >= CONFIDENCE_ROUTE else "send_to_operator"
    return {
        "top_services": ranked,
        "confidence": top,
        "decision": decision,
        "threshold": CONFIDENCE_ROUTE,
        "seen_cases": total,
    }


def load_retriever(model_dir):
    if not pathlib.Path(model_dir).exists():
        return None
    try:
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer(model_dir, device="cpu")
    except Exception:
        return None


def similar_cases(corpus, region, topic, model):
    """Resolved cases for the same region and topic, ranked by the model."""
    pool = [d for d in corpus if d["region_id"] == region and d["topic_label"] == topic]
    if len(pool) < 2:
        pool = [d for d in corpus if d["topic_label"] == topic]
    if not pool:
        return [], "none"
    if model is None:
        pool = sorted(pool, key=lambda d: -len(d["text"]))
        return pool[:TOP_K], "lexical_fallback"
    import numpy as np

    query = f"query: обращение по теме {topic}, регион {region}"
    texts = ["query: " + d["text"] for d in pool]
    emb = np.asarray(model.encode(texts, normalize_embeddings=True), dtype="float32")
    qv = np.asarray(model.encode([query], normalize_embeddings=True), dtype="float32")[0]
    scores = emb @ qv
    order = np.argsort(-scores)[:TOP_K]
    return [pool[i] for i in order], "fine_tuned_e5"


def surge_context(forecast_report, region, appeal_day):
    reg = forecast_report["regions"].get(region, {})
    surges = reg.get("surges", {})
    days = {s["date"]: s for s in surges.get("examples", [])}
    hit = days.get(appeal_day)
    return {
        "region": region,
        "day": appeal_day,
        "is_flagged_surge_example": hit is not None,
        "surge_detail": hit,
        "region_surge_days": surges.get("surge_days"),
        "robust_bound": surges.get("robust_bound"),
    }


def forecast_context(forecast_report, region):
    reg = forecast_report["regions"].get(region, {})
    return {
        "recommended_method": reg.get("recommended_method", {}).get("method"),
        "staffing": reg.get("staffing_recent"),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--canonical", required=True)
    parser.add_argument("--corpus", required=True)
    parser.add_argument("--reports", default="ml/evaluation")
    parser.add_argument("--out", required=True)
    parser.add_argument("--region", default="PAVLODAR")
    parser.add_argument("--day", default="2024-06-21", help="a real surge day by default")
    parser.add_argument("--topic", default=None)
    args = parser.parse_args()

    rows = load_canonical(args.canonical)
    corpus = [json.loads(line) for line in open(args.corpus, encoding="utf-8")]
    forecast_report = json.loads(
        pathlib.Path(args.reports, "forecast_v1", "forecast_report.json").read_text()
    )

    day_rows = [r for r in rows if r["region"] == args.region and r["received"] == args.day]
    if args.topic:
        topic = args.topic
    elif day_rows:
        topic = Counter(r["topic"] for r in day_rows).most_common(1)[0][0]
    else:
        topic = Counter(r["topic"] for r in rows if r["region"] == args.region).most_common(1)[0][0]

    model = load_retriever(str(pathlib.Path(args.reports, "retrieval_ft_v1", "model")))
    cases, retriever = similar_cases(corpus, args.region, topic, model)
    routing = routing_decision(rows, args.region, topic)
    surge = surge_context(forecast_report, args.region, args.day)
    forecast = forecast_context(forecast_report, args.region)

    trace = {
        "generated_at": datetime.now(UTC).isoformat(),
        "honesty_boundary": (
            "Intake free text is illustrative because no citizen text exists in the data (D-018). "
            "Every downstream result is computed from real records and models."
        ),
        "step_1_intake": {
            "region": args.region,
            "day": args.day,
            "topic_hint": topic,
            "appeals_that_day_this_topic": sum(1 for r in day_rows if r["topic"] == topic),
            "illustrative_citizen_text": f"[иллюстративно] Обращение по теме «{topic}»",
        },
        "step_2_routing": routing,
        "step_3_assist": {
            "retriever": retriever,
            "similar_resolved_cases": [
                {
                    "service": c["service_label"],
                    "received_at": c.get("received_at", "")[:10],
                    "resolution_excerpt": c["text"][:200],
                }
                for c in cases
            ],
        },
        "step_4_situation": surge,
        "step_5_forecast": forecast,
    }

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "demo_trace.json").write_text(
        json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"region {args.region}  day {args.day}  topic {topic}")
    print(
        f"  routing   {routing['decision']} at {routing['confidence']:.2f} "
        f"over {routing['seen_cases']} cases"
    )
    print(f"  assist    {len(cases)} similar cases via {retriever}")
    print(
        f"  situation surge-example={surge['is_flagged_surge_example']}, "
        f"region has {surge['region_surge_days']} surge days"
    )
    staff = forecast["staffing"] or {}
    print(
        f"  forecast  {staff.get('mean_appeals_per_day', '-')}/day -> "
        f"{staff.get('operators_per_shift', '-')} operators/shift"
    )
    print(f"written {out / 'demo_trace.json'}")


if __name__ == "__main__":
    main()
