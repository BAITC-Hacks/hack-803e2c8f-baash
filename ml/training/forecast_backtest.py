"""Demand forecasting and surge detection for the situation centre.

Module 3 of the case: the supervisor needs a load forecast to plan shifts and
a surge signal that separates a real spike from ordinary weekly rhythm.

Two questions are answered honestly, each against a baseline a reviewer can
reconstruct by hand.

Forecasting. Daily appeal volume per region. The baseline is seasonal naive:
tomorrow equals the same weekday one week ago. A model earns its place only by
beating that. Evaluation is rolling origin: the model is refit at successive
cut points and scored on the days after each cut, so no future information ever
reaches a forecast. MAE, MAPE and sMAPE are reported per horizon.

Surge detection. A spike is not a threshold on the raw count, because Monday is
always higher than Sunday. The series is decomposed into a weekly component
(median per weekday), a trend (centred rolling median), and a residual. A surge
is a residual above a robust bound, k times the median absolute deviation. This
is the aggregate form of the incident concept: an emerging problem, not a claim
that two specific appeals are the same event.

Staffing. A forecast in appeals per day becomes operators per shift through
average handle time and a target occupancy, so the number turns into a decision.

Standard library plus numpy and scikit-learn. No heavy dependency.

Usage:
    python ml/training/forecast_backtest.py \
        --canonical build/ingest/canonical.jsonl --out ml/evaluation/forecast_v1
"""

from __future__ import annotations

import argparse
import json
import pathlib
from collections import Counter, defaultdict
from datetime import UTC, date, datetime, timedelta

MIN_HISTORY_DAYS = 400
HORIZONS = (7, 14, 30)
BACKTEST_ORIGINS = 6
SURGE_K = 4.0
TREND_WINDOW = 28
AHT_MINUTES = 6.0
SHIFT_HOURS = 8.0
TARGET_OCCUPANCY = 0.85
RANDOM_STATE = 109


def daily_series(path, region):
    counts = Counter()
    for line in open(path, encoding="utf-8"):
        rec = json.loads(line)
        if rec["source"]["region_id"] != region:
            continue
        received = rec["time"]["received_at"]
        if not received:
            continue
        counts[date.fromisoformat(received[:10])] += 1
    if not counts:
        return [], []
    start, end = min(counts), max(counts)
    days, values = [], []
    cur = start
    while cur <= end:
        days.append(cur)
        values.append(counts.get(cur, 0))
        cur += timedelta(days=1)
    return days, values


def region_list(path):
    seen = Counter()
    for line in open(path, encoding="utf-8"):
        rec = json.loads(line)
        if rec["time"]["received_at"]:
            seen[rec["source"]["region_id"]] += 1
    return seen


# --------------------------------------------------------------------------
# forecasting
# --------------------------------------------------------------------------


def seasonal_naive(values, origin, horizon):
    """Same weekday one week ago, carried forward across the horizon."""
    return [values[origin - 7 + (h % 7)] for h in range(horizon)]


def make_features(days, values, idx):
    """Calendar plus lag features known strictly before day idx."""
    d = days[idx]
    return {
        f"dow_{d.weekday()}": 1.0,
        f"month_{d.month}": 1.0,
        "trend": idx,
        "lag_1": values[idx - 1],
        "lag_7": values[idx - 7],
        "lag_14": values[idx - 14],
        "roll_7": sum(values[idx - 7 : idx]) / 7,
        "roll_28": sum(values[idx - 28 : idx]) / 28,
    }


def model_forecast(days, values, origin, horizon):
    """Ridge on calendar and lag features, refit at the origin.

    Multi-step is iterative: each predicted day feeds the next day's lags, so a
    forecast never reads an actual value from after the origin.
    from after the origin.
    """
    import numpy as np
    from sklearn.feature_extraction import DictVectorizer
    from sklearn.linear_model import Ridge

    train_idx = range(28, origin)
    vec = DictVectorizer()
    x = vec.fit_transform([make_features(days, values, i) for i in train_idx])
    y = np.array([values[i] for i in train_idx], dtype="float64")
    model = Ridge(alpha=1.0, random_state=RANDOM_STATE)
    model.fit(x, y)

    history = list(values[:origin])
    day_seq = list(days[:origin])
    preds = []
    for _ in range(horizon):
        nxt = day_seq[-1] + timedelta(days=1)
        day_seq.append(nxt)
        history.append(0)  # placeholder so indexing lines up
        feats = make_features(day_seq, history, len(history) - 1)
        pred = float(model.predict(vec.transform([feats]))[0])
        pred = max(pred, 0.0)
        history[-1] = pred
        preds.append(pred)
    return preds


def metrics(actual, predicted):
    import numpy as np

    a = np.array(actual, dtype="float64")
    p = np.array(predicted, dtype="float64")
    mae = float(np.mean(np.abs(a - p)))
    mask = a > 0
    mape = float(np.mean(np.abs((a[mask] - p[mask]) / a[mask])) * 100) if mask.any() else None
    smape = float(np.mean(2 * np.abs(a - p) / (np.abs(a) + np.abs(p) + 1e-9)) * 100)
    return {
        "mae": round(mae, 2),
        "mape": round(mape, 2) if mape else None,
        "smape": round(smape, 2),
    }


def rolling_backtest(days, values):
    """Refit at evenly spaced origins, forecast forward, average the errors."""
    n = len(values)
    max_h = max(HORIZONS)
    first = max(MIN_HISTORY_DAYS, 60)
    last = n - max_h
    if last <= first:
        return None
    origins = [
        first + int((last - first) * i / (BACKTEST_ORIGINS - 1)) for i in range(BACKTEST_ORIGINS)
    ]

    out = {"origins": len(origins), "horizons": {}}
    for horizon in HORIZONS:
        naive_acc, model_acc = defaultdict(list), defaultdict(list)
        for origin in origins:
            actual = values[origin : origin + horizon]
            for label, forecast in (
                ("naive", seasonal_naive(values, origin, horizon)),
                ("model", model_forecast(days, values, origin, horizon)),
            ):
                m = metrics(actual, forecast)
                acc = naive_acc if label == "naive" else model_acc
                for key, val in m.items():
                    if val is not None:
                        acc[key].append(val)

        def avg(acc):
            return {k: round(sum(v) / len(v), 2) for k, v in acc.items() if v}

        naive_m, model_m = avg(naive_acc), avg(model_acc)
        out["horizons"][f"h{horizon}"] = {
            "seasonal_naive": naive_m,
            "model_ridge": model_m,
            "mae_improvement_pct": round(
                (naive_m["mae"] - model_m["mae"]) / naive_m["mae"] * 100, 1
            )
            if naive_m.get("mae")
            else None,
        }
    return out


# --------------------------------------------------------------------------
# surge detection
# --------------------------------------------------------------------------


def decompose(days, values):
    """Weekly seasonal by weekday median, trend by centred rolling median."""
    import numpy as np

    v = np.array(values, dtype="float64")
    half = TREND_WINDOW // 2
    trend = np.array(
        [np.median(v[max(0, i - half) : min(len(v), i + half + 1)]) for i in range(len(v))]
    )
    detrended = v - trend
    weekday_effect = {}
    for wd in range(7):
        vals = [detrended[i] for i, d in enumerate(days) if d.weekday() == wd]
        weekday_effect[wd] = float(np.median(vals)) if vals else 0.0
    seasonal = np.array([weekday_effect[d.weekday()] for d in days])
    residual = detrended - seasonal
    return trend, seasonal, residual


def detect_surges(days, values):
    import numpy as np

    _, _, residual = decompose(days, values)
    mad = float(np.median(np.abs(residual - np.median(residual)))) or 1.0
    bound = SURGE_K * 1.4826 * mad
    surges = [
        {
            "date": days[i].isoformat(),
            "value": int(values[i]),
            "residual": round(float(residual[i]), 1),
        }
        for i in range(len(values))
        if residual[i] > bound
    ]
    return {
        "robust_bound": round(bound, 1),
        "k": SURGE_K,
        "surge_days": len(surges),
        "surge_rate_pct": round(len(surges) / len(values) * 100, 2),
        "examples": sorted(surges, key=lambda s: -s["residual"])[:8],
    }


def staffing(daily_forecast):
    """Appeals per day to operators per shift."""
    minutes = daily_forecast * AHT_MINUTES
    operator_minutes = SHIFT_HOURS * 60 * TARGET_OCCUPANCY
    return round(minutes / operator_minutes, 1)


def choose_method(backtest):
    """Pick the method that wins the operational 7-day MAE. A model must beat
    seasonal naive to be used; otherwise the honest choice is the baseline."""
    if not backtest:
        return {"method": "seasonal_naive", "reason": "history below minimum"}
    h7 = backtest["horizons"]["h7"]
    naive = h7["seasonal_naive"]["mae"]
    model = h7["model_ridge"]["mae"]
    if model < naive:
        return {
            "method": "model_ridge",
            "h7_mae": model,
            "beats_naive_by_pct": round((naive - model) / naive * 100, 1),
        }
    return {
        "method": "seasonal_naive",
        "h7_mae": naive,
        "reason": "model does not beat the baseline on this series",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--canonical", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--regions", nargs="*", default=None)
    args = parser.parse_args()

    regions = args.regions or [r for r, _ in region_list(args.canonical).most_common()]
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "baseline": "seasonal naive, same weekday one week earlier",
        "candidate": "ridge on calendar and lag features, iterative multi-step",
        "backtest": f"rolling origin, {BACKTEST_ORIGINS} origins, horizons {HORIZONS}",
        "staffing": {
            "aht_minutes": AHT_MINUTES,
            "shift_hours": SHIFT_HOURS,
            "target_occupancy": TARGET_OCCUPANCY,
            "note": "AHT and occupancy are placeholders pending the operator interview.",
        },
        "regions": {},
        "limits": [
            "Volume is proxied by received_at day. Short-history regions forecast weakly.",
            "Surge detection flags aggregate anomalies, not that two appeals are one event.",
            "AHT and target occupancy are assumptions, not measured from the call centre.",
        ],
    }

    for region in regions:
        days, values = daily_series(args.canonical, region)
        if len(values) < MIN_HISTORY_DAYS:
            report["regions"][region] = {"days": len(values), "skipped": "history below minimum"}
            print(f"  {region:<12} skipped, only {len(values)} days")
            continue
        backtest = rolling_backtest(days, values)
        surges = detect_surges(days, values)
        recent_avg = sum(values[-28:]) / 28
        recommendation = choose_method(backtest)
        report["regions"][region] = {
            "days": len(values),
            "period": [days[0].isoformat(), days[-1].isoformat()],
            "mean_per_day": round(sum(values) / len(values), 1),
            "recommended_method": recommendation,
            "backtest": backtest,
            "surges": surges,
            "staffing_recent": {
                "mean_appeals_per_day": round(recent_avg, 1),
                "operators_per_shift": staffing(recent_avg),
            },
        }
        h7 = backtest["horizons"]["h7"] if backtest else {}
        imp = h7.get("mae_improvement_pct")
        print(
            f"  {region:<12} {len(values):>5}d  "
            f"naiveMAE {h7.get('seasonal_naive', {}).get('mae', '-'):>6}  "
            f"modelMAE {h7.get('model_ridge', {}).get('mae', '-'):>6}  "
            f"gain {imp if imp is not None else '-'}%  surges {surges['surge_days']}"
        )

    scored = [v for v in report["regions"].values() if "recommended_method" in v]
    report["summary"] = {
        "regions_scored": len(scored),
        "model_wins": sum(1 for v in scored if v["recommended_method"]["method"] == "model_ridge"),
        "naive_wins": sum(
            1 for v in scored if v["recommended_method"]["method"] == "seasonal_naive"
        ),
        "decision": "forecast each region with the method that wins its own backtest",
    }

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "forecast_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nwritten {out / 'forecast_report.json'}")


if __name__ == "__main__":
    main()
