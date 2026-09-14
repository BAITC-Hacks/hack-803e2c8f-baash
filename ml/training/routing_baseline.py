"""Routing baselines and a calibrated linear candidate for service assignment.

The task is service routing from what is known at intake. No citizen text
exists in any export (D-018), so the feature set is categorical and temporal
only: topic, region, district, channel, hour, weekday, month.

Everything here answers one question honestly: does a model beat a lookup
table. The lookup table is not a strawman. A topic to service dictionary
already resolves 62.2 percent of the corpus, and Karaganda is 99.9 percent
deterministic, which means that region has no routing task at all.

Splits are temporal inside each region (D-015 context). A global date cut is
impossible because the regions cover different periods: Karaganda ends in
December 2023 while Kostanay and Almaty oblast start in January 2025.

Usage:
    python ml/training/routing_baseline.py --canonical build/ingest/canonical.jsonl \
        --out ml/evaluation/routing_v1
"""

from __future__ import annotations

import argparse
import json
import pathlib
from collections import Counter, defaultdict
from datetime import UTC, datetime

TEST_FRACTION = 0.2
MIN_REGION_ROWS = 500
RANDOM_STATE = 109


def load(path):
    """Stream the canonical records into flat training rows."""
    rows = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            rec = json.loads(line)
            attrs = rec["intake"]["selected_attributes"]
            topic = attrs["topic_label"]
            service = attrs["service_label"]
            received = rec["time"]["received_at"]
            if not topic or not service or not received:
                continue
            stamp = datetime.fromisoformat(received)
            rows.append(
                {
                    "region": rec["source"]["region_id"],
                    "topic": topic,
                    "service": service,
                    "district": rec["location"]["geo_id"] or "",
                    "channel": rec["intake"]["channel"],
                    "language": rec["intake"]["language"],
                    "hour": stamp.hour,
                    "weekday": stamp.weekday(),
                    "month": stamp.month,
                    "ts": stamp,
                }
            )
    return rows


def temporal_split(rows):
    """Cut inside each region so no region lands entirely on one side."""
    by_region = defaultdict(list)
    for row in rows:
        by_region[row["region"]].append(row)
    train, test, cuts = [], [], {}
    for region, items in by_region.items():
        items.sort(key=lambda r: r["ts"])
        cut = int(len(items) * (1 - TEST_FRACTION))
        train.extend(items[:cut])
        test.extend(items[cut:])
        cuts[region] = {
            "cut_at": items[cut]["ts"].isoformat() if cut < len(items) else None,
            "train": cut,
            "test": len(items) - cut,
        }
    return train, test, cuts


def macro_f1(pairs):
    """Macro averaged F1 over the labels present in the evaluated slice."""
    labels = {true for true, _ in pairs} | {pred for _, pred in pairs}
    scores = []
    for label in labels:
        tp = sum(1 for t, p in pairs if t == label and p == label)
        fp = sum(1 for t, p in pairs if t != label and p == label)
        fn = sum(1 for t, p in pairs if t == label and p != label)
        if tp == 0:
            scores.append(0.0)
            continue
        precision = tp / (tp + fp)
        recall = tp / (tp + fn)
        scores.append(2 * precision * recall / (precision + recall))
    return sum(scores) / len(scores) if scores else 0.0


def accuracy(pairs):
    return sum(1 for t, p in pairs if t == p) / len(pairs) if pairs else 0.0


# --------------------------------------------------------------------------
# baselines
# --------------------------------------------------------------------------


def fit_lookup(train, keys):
    """Most frequent service for a key tuple, with progressive backoff."""
    table = defaultdict(Counter)
    for row in train:
        table[tuple(row[k] for k in keys)][row["service"]] += 1
    return {k: c.most_common(1)[0][0] for k, c in table.items()}


def predict_lookup(tables, fallback, row, key_sets):
    for keys, table in zip(key_sets, tables, strict=True):
        hit = table.get(tuple(row[keys_i] for keys_i in keys))
        if hit:
            return hit
    return fallback


def run_baselines(train, test):
    global_top = Counter(r["service"] for r in train).most_common(1)[0][0]
    variants = {
        "B0_global_majority": [],
        "B1_topic": [("topic",)],
        "B2_topic_region": [("topic", "region"), ("topic",)],
        "B3_topic_region_district": [
            ("topic", "region", "district"),
            ("topic", "region"),
            ("topic",),
        ],
    }
    results = {}
    predictions = {}
    for name, key_sets in variants.items():
        tables = [fit_lookup(train, keys) for keys in key_sets]
        preds = [predict_lookup(tables, global_top, r, key_sets) for r in test]
        pairs = list(zip([r["service"] for r in test], preds, strict=True))
        results[name] = {"accuracy": accuracy(pairs), "macro_f1": macro_f1(pairs)}
        predictions[name] = preds
    return results, predictions, global_top


# --------------------------------------------------------------------------
# linear candidate
# --------------------------------------------------------------------------


def run_model(train, test):
    from sklearn.feature_extraction import DictVectorizer
    from sklearn.linear_model import LogisticRegression

    def feats(row):
        return {
            f"topic={row['topic']}": 1,
            f"region={row['region']}": 1,
            f"district={row['district']}": 1,
            f"channel={row['channel']}": 1,
            f"hour={row['hour'] // 4}": 1,
            f"weekday={row['weekday']}": 1,
            f"month={row['month']}": 1,
            f"topic_region={row['topic']}|{row['region']}": 1,
        }

    vec = DictVectorizer()
    x_train = vec.fit_transform([feats(r) for r in train])
    x_test = vec.transform([feats(r) for r in test])
    y_train = [r["service"] for r in train]
    y_test = [r["service"] for r in test]

    clf = LogisticRegression(max_iter=400, n_jobs=-1, random_state=RANDOM_STATE)
    clf.fit(x_train, y_train)
    preds = list(clf.predict(x_test))
    probs = clf.predict_proba(x_test).max(axis=1)
    pairs = list(zip(y_test, preds, strict=True))
    return (
        {"accuracy": accuracy(pairs), "macro_f1": macro_f1(pairs)},
        preds,
        probs.tolist(),
        len(vec.feature_names_),
    )


def coverage_curve(y_true, preds, probs):
    """Accuracy against the share of traffic the model is allowed to route."""
    order = sorted(range(len(probs)), key=lambda i: -probs[i])
    out = []
    for share in (0.3, 0.5, 0.7, 0.9, 1.0):
        take = order[: int(len(order) * share)]
        if not take:
            continue
        correct = sum(1 for i in take if y_true[i] == preds[i])
        out.append(
            {
                "coverage": share,
                "accuracy": correct / len(take),
                "threshold": probs[take[-1]],
            }
        )
    return out


def leave_one_region_out(rows):
    """Train on six regions, evaluate on the seventh. Answers portability."""
    regions = sorted({r["region"] for r in rows})
    out = {}
    for held in regions:
        train = [r for r in rows if r["region"] != held]
        test = [r for r in rows if r["region"] == held]
        if len(test) < MIN_REGION_ROWS:
            out[held] = {"skipped": "region too small"}
            continue
        table = fit_lookup(train, ("topic",))
        fallback = Counter(r["service"] for r in train).most_common(1)[0][0]
        preds = [table.get((r["topic"],), fallback) for r in test]
        pairs = list(zip([r["service"] for r in test], preds, strict=True))
        seen = sum(1 for r in test if (r["topic"],) in table)
        out[held] = {
            "test_rows": len(test),
            "topic_coverage": seen / len(test),
            "accuracy": accuracy(pairs),
            "macro_f1": macro_f1(pairs),
        }
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--canonical", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--sample", type=int, default=None)
    args = parser.parse_args()

    rows = load(args.canonical)
    if args.sample:
        step = max(1, len(rows) // args.sample)
        rows = rows[::step]
    print(f"rows with topic, service and time: {len(rows):,}")

    train, test, cuts = temporal_split(rows)
    print(f"train {len(train):,}  test {len(test):,}")

    baselines, base_preds, _ = run_baselines(train, test)
    for name, res in baselines.items():
        print(f"  {name:<28} acc {res['accuracy']:.4f}  macroF1 {res['macro_f1']:.4f}")

    model, preds, probs, n_feat = run_model(train, test)
    print(
        f"  {'M1_logreg':<28} acc {model['accuracy']:.4f}  macroF1 {model['macro_f1']:.4f}"
    )

    y_test = [r["service"] for r in test]
    per_region = {}
    for region in sorted({r["region"] for r in test}):
        idx = [i for i, r in enumerate(test) if r["region"] == region]
        best_base = base_preds["B3_topic_region_district"]
        per_region[region] = {
            "rows": len(idx),
            "baseline_accuracy": accuracy([(y_test[i], best_base[i]) for i in idx]),
            "model_accuracy": accuracy([(y_test[i], preds[i]) for i in idx]),
            "model_macro_f1": macro_f1([(y_test[i], preds[i]) for i in idx]),
        }

    per_language = {}
    for lang in sorted({r["language"] for r in test}):
        idx = [i for i, r in enumerate(test) if r["language"] == lang]
        if len(idx) < 50:
            continue
        per_language[lang] = {
            "rows": len(idx),
            "model_accuracy": accuracy([(y_test[i], preds[i]) for i in idx]),
            "model_macro_f1": macro_f1([(y_test[i], preds[i]) for i in idx]),
        }

    report = {
        "task": "service routing from intake-available categorical features",
        "generated_at": datetime.now(UTC).isoformat(),
        "rows": len(rows),
        "split": {
            "strategy": "temporal inside each region",
            "test_fraction": TEST_FRACTION,
            "regions": cuts,
        },
        "features": n_feat,
        "baselines": baselines,
        "model": model,
        "coverage_curve": coverage_curve(y_test, preds, probs),
        "per_region": per_region,
        "per_language": per_language,
        "leave_one_region_out": leave_one_region_out(rows),
        "notes": [
            "No citizen text exists, so this ceiling reflects categorical features only.",
            "Karaganda is 99.9 percent deterministic from topic alone and has no routing task.",
            "A model that fails to beat B3 is evidence that routing needs the raw appeal text.",
        ],
    }
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "routing_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nwritten {out / 'routing_report.json'}")


if __name__ == "__main__":
    main()
