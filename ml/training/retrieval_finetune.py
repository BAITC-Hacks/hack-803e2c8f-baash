"""Fine-tune retrieval embeddings on the regional executor corpus.

Evaluation reports hit_rate@k (the fraction of queries with any relevant
result), MRR and nDCG. It does not call that hit rate recall, which would
require dividing by all relevant documents.

Leakage control is the whole design. Relevance in the evaluation is a shared
(region, topic, service) group. If pairs were mined across the full corpus the
model would be trained on the exact signal it is scored against.

So the split is temporal, mirroring the routing methodology:
  train  documents received before the cut
  eval   documents received after the cut, indexed and queried among themselves

The model never sees an evaluation document, nor any pair drawn from one.

Pair mining on the train side only:
  positive       same region, topic and service, within a time window
  hard negative  same topic, different service, which is the confusion that
                 actually costs an operator time

Usage:
    python ml/training/retrieval_finetune.py \
        --corpus ml/datasets/regional_retrieval_corpus_v1.jsonl \
        --out ml/evaluation/retrieval_ft_v1
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import random
from collections import defaultdict
from datetime import UTC, datetime

MIN_CHARS = 40
MAX_CHARS = 4000
TOP_K = 10
TEST_FRACTION = 0.25
TIME_WINDOW_DAYS = 120
MAX_PAIRS = 12000
RANDOM_STATE = 109


def load(path):
    docs = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            doc = json.loads(line)
            if doc.get("text", "").startswith("[WITHHELD_"):
                raise ValueError("retrieval fine-tuning corpus contains withheld text placeholders")
            if not doc.get("received_at"):
                continue
            if not (MIN_CHARS <= len(doc["text"]) <= MAX_CHARS):
                continue
            doc["ts"] = datetime.fromisoformat(doc["received_at"])
            doc["group"] = (doc["region_id"], doc["topic_label"], doc["service_label"])
            docs.append(doc)
    docs.sort(key=lambda d: d["ts"])
    return docs


def temporal_split(docs):
    cut = int(len(docs) * (1 - TEST_FRACTION))
    return docs[:cut], docs[cut:], docs[cut]["ts"]


def mine_pairs(train, seed=RANDOM_STATE):
    """Positives inside a group and time window, hard negatives across services."""
    rng = random.Random(seed)  # noqa: S311 - reproducible sampling, not cryptography
    by_group = defaultdict(list)
    by_topic = defaultdict(list)
    for doc in train:
        by_group[doc["group"]].append(doc)
        by_topic[(doc["region_id"], doc["topic_label"])].append(doc)

    window = TIME_WINDOW_DAYS * 86400
    pairs = []
    for group, items in by_group.items():
        if len(items) < 2:
            continue
        region, topic, service = group
        siblings = by_topic[(region, topic)]
        for anchor in items:
            near = [
                other
                for other in items
                if other is not anchor
                and abs((other["ts"] - anchor["ts"]).total_seconds()) <= window
            ]
            if not near:
                continue
            positive = rng.choice(near)
            negatives = [s for s in siblings if s["service_label"] != service]
            negative = rng.choice(negatives) if negatives else None
            pairs.append((anchor["text"], positive["text"], negative["text"] if negative else None))
    rng.shuffle(pairs)
    return pairs[:MAX_PAIRS]


# --------------------------------------------------------------------------
# Evaluation definitions are kept identical to retrieval_eval.
# --------------------------------------------------------------------------


def build_queries(docs, limit, seed=RANDOM_STATE):
    groups = defaultdict(list)
    for idx, doc in enumerate(docs):
        groups[doc["group"]].append(idx)
    eligible = [i for i, d in enumerate(docs) if len(groups[d["group"]]) > 1]
    rng = random.Random(seed)  # noqa: S311 - reproducible sampling, not cryptography
    rng.shuffle(eligible)
    queries = eligible[:limit]
    return queries, {q: set(groups[docs[q]["group"]]) - {q} for q in queries}


def evaluate(ranked, relevant, k=TOP_K):
    rec = {1: 0.0, 5: 0.0, 10: 0.0}
    mrr = ndcg = 0.0
    n = len(ranked)
    for qid, order in ranked.items():
        rel = relevant[qid]
        # Exclude self-matches before applying the cutoff, even for callers
        # that provide a ranking without having removed the query document.
        order = [doc for doc in order if doc != qid]
        top = order[:k]
        for cut in rec:
            rec[cut] += 1 if any(d in rel for d in top[:cut]) else 0
        for rank, doc in enumerate(top, start=1):
            if doc in rel:
                mrr += 1.0 / rank
                break
        gain = sum(1.0 / math.log2(r + 1) for r, d in enumerate(top, start=1) if d in rel)
        ideal = sum(1.0 / math.log2(r + 1) for r in range(1, min(len(rel), k) + 1))
        ndcg += gain / ideal if ideal else 0.0
    return {
        "hit_rate_at_1": rec[1] / n,
        "hit_rate_at_5": rec[5] / n,
        "hit_rate_at_10": rec[10] / n,
        "mrr_at_10": mrr / n,
        "ndcg_at_10": ndcg / n,
        "queries": n,
    }


def rank_lexical(docs, queries):
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer

    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=2, max_features=200_000)
    matrix = vec.fit_transform([d["text"] for d in docs])
    out = {}
    for qid in queries:
        scores = (matrix @ matrix[qid].T).toarray().ravel()
        scores[qid] = float("-inf")
        out[qid] = np.argsort(-scores)[:TOP_K].tolist()
    return out


def rank_model(model, docs, queries, prefix=""):
    import numpy as np

    emb = model.encode(
        [prefix + d["text"] for d in docs],
        batch_size=128,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    emb = np.asarray(emb, dtype="float32")
    out = {}
    for qid in queries:
        scores = emb @ emb[qid]
        scores[qid] = float("-inf")
        out[qid] = np.argsort(-scores)[:TOP_K].tolist()
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--base", default="intfloat/multilingual-e5-small")
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--batch", type=int, default=32)
    parser.add_argument("--queries", type=int, default=800)
    parser.add_argument("--device", default="cpu", help="cpu avoids the MPS allocator ceiling")
    parser.add_argument(
        "--max-seq",
        type=int,
        default=128,
        help="corpus median is 68 characters, p90 is 267, so 128 tokens covers it",
    )
    args = parser.parse_args()

    from sentence_transformers import InputExample, SentenceTransformer, losses
    from torch.utils.data import DataLoader

    docs = load(args.corpus)
    train_docs, eval_docs, cut_ts = temporal_split(docs)
    print(f"corpus {len(docs):,}  train {len(train_docs):,}  eval {len(eval_docs):,}")
    print(f"temporal cut at {cut_ts.isoformat()}")

    pairs = mine_pairs(train_docs)
    with_neg = sum(1 for p in pairs if p[2])
    print(f"mined pairs {len(pairs):,}, of which {with_neg:,} carry a hard negative")

    queries, relevant = build_queries(eval_docs, args.queries)
    print(f"eval queries {len(queries):,} over {len(eval_docs):,} indexed documents")

    prefix = "query: " if "e5" in args.base else ""
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "base_model": args.base,
        "device": args.device,
        "max_seq_length": args.max_seq,
        "split": {
            "strategy": "temporal, evaluation documents never appear in training pairs",
            "cut_at": cut_ts.isoformat(),
            "train_documents": len(train_docs),
            "eval_documents": len(eval_docs),
        },
        "training": {
            "pairs": len(pairs),
            "pairs_with_hard_negative": with_neg,
            "loss": "MultipleNegativesRankingLoss",
            "epochs": args.epochs,
            "batch_size": args.batch,
            "positive_rule": f"same region, topic and service within {TIME_WINDOW_DAYS} days",
            "hard_negative_rule": "same region and topic, different service",
        },
        "systems": {},
        "limits": [
            "Queries are executor texts. Production queries are citizen texts.",
            "Proxy relevance is a shared (region, topic, service) group.",
            "No pure Kazakh documents exist, so no kk slice can be reported.",
        ],
    }

    lex = rank_lexical(eval_docs, queries)
    report["systems"]["S1_char_tfidf"] = evaluate(lex, relevant)
    print(f"  {'S1_char_tfidf':<26} nDCG {report['systems']['S1_char_tfidf']['ndcg_at_10']:.4f}")

    model = SentenceTransformer(args.base, device=args.device)
    model.max_seq_length = args.max_seq
    frozen = rank_model(model, eval_docs, queries, prefix)
    report["systems"]["S2_frozen"] = evaluate(frozen, relevant)
    print(f"  {'S2_frozen':<26} nDCG {report['systems']['S2_frozen']['ndcg_at_10']:.4f}")

    examples = [
        InputExample(texts=[prefix + a, prefix + p, prefix + n] if n else [prefix + a, prefix + p])
        for a, p, n in pairs
    ]
    loader = DataLoader(examples, shuffle=True, batch_size=args.batch, drop_last=True)
    model.fit(
        train_objectives=[(loader, losses.MultipleNegativesRankingLoss(model))],
        epochs=args.epochs,
        warmup_steps=int(len(loader) * 0.1),
        show_progress_bar=False,
    )

    tuned = rank_model(model, eval_docs, queries, prefix)
    report["systems"]["S3_finetuned"] = evaluate(tuned, relevant)
    print(f"  {'S3_finetuned':<26} nDCG {report['systems']['S3_finetuned']['ndcg_at_10']:.4f}")

    base = report["systems"]["S2_frozen"]
    lexr = report["systems"]["S1_char_tfidf"]
    tun = report["systems"]["S3_finetuned"]
    report["deltas"] = {
        "finetuned_vs_frozen_ndcg_points": round((tun["ndcg_at_10"] - base["ndcg_at_10"]) * 100, 2),
        "finetuned_vs_lexical_ndcg_points": round(
            (tun["ndcg_at_10"] - lexr["ndcg_at_10"]) * 100, 2
        ),
        "finetuned_vs_frozen_hit_rate_at_1_points": round(
            (tun["hit_rate_at_1"] - base["hit_rate_at_1"]) * 100, 2
        ),
    }

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "retrieval_finetune_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    model.save(str(out / "model"))
    print(f"\ndeltas {report['deltas']}")
    print(f"written {out / 'retrieval_finetune_report.json'}")


if __name__ == "__main__":
    main()
