"""Retrieval evaluation over the regional executor corpus.

Production task: an operator opens a new appeal and wants the resolved cases
that were handled the same way, so the earlier answer can be reused.

There is no citizen text in any export (D-018), so the only corpus available
is 14 397 executor documents written after closure. This script measures
whether a retrieval model recovers the operational structure of that corpus.

Relevance is a proxy, not human judgment. Two documents are relevant to each
other when they share region, topic and service. That is the operational
grouping an operator cares about, and it is derived from metadata rather than
from the text, so a text model cannot see the label it is scored against.

Two limits that must travel with any number this script prints:
  1. Queries are executor texts. Production queries are citizen texts and will
     differ in style and vocabulary.
  2. Proxy relevance rewards recovering the metadata grouping. It does not
     prove an operator would find the result useful.

Usage:
    python ml/training/retrieval_eval.py \
        --corpus ml/datasets/regional_retrieval_corpus_v1.jsonl \
        --out ml/evaluation/retrieval_v1
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import random
from collections import defaultdict
from datetime import UTC, datetime

MIN_QUERY_CHARS = 40
MAX_QUERY_CHARS = 4000
DEFAULT_QUERIES = 2000
TOP_K = 10
RANDOM_STATE = 109


def load_corpus(path):
    docs = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            doc = json.loads(line)
            doc["group"] = (doc["region_id"], doc["topic_label"], doc["service_label"])
            docs.append(doc)
    return docs


def build_query_set(docs, n_queries, seed=RANDOM_STATE):
    """Queries need at least one other document in their group to be scorable."""
    groups = defaultdict(list)
    for idx, doc in enumerate(docs):
        groups[doc["group"]].append(idx)

    eligible = [
        idx
        for idx, doc in enumerate(docs)
        if MIN_QUERY_CHARS <= len(doc["text"]) <= MAX_QUERY_CHARS and len(groups[doc["group"]]) > 1
    ]
    rng = random.Random(seed)  # noqa: S311 - reproducible sampling, not cryptography
    rng.shuffle(eligible)
    queries = eligible[:n_queries]
    relevant = {idx: set(groups[docs[idx]["group"]]) - {idx} for idx in queries}
    return queries, relevant, groups


# --------------------------------------------------------------------------
# metrics
# --------------------------------------------------------------------------


def evaluate(ranked, relevant, k=TOP_K):
    """Recall@1/5/10, MRR@10 and nDCG@10 over the supplied rankings."""
    rec = {1: 0.0, 5: 0.0, 10: 0.0}
    mrr = 0.0
    ndcg = 0.0
    n = len(ranked)
    for qid, order in ranked.items():
        rel = relevant[qid]
        top = order[:k]
        for cut in rec:
            hits = sum(1 for d in top[:cut] if d in rel)
            rec[cut] += min(hits, 1)
        for rank, doc in enumerate(top, start=1):
            if doc in rel:
                mrr += 1.0 / rank
                break
        gain = sum(1.0 / math.log2(r + 1) for r, d in enumerate(top, start=1) if d in rel)
        ideal = sum(1.0 / math.log2(r + 1) for r in range(1, min(len(rel), k) + 1))
        ndcg += gain / ideal if ideal else 0.0
    return {
        "recall_at_1": rec[1] / n,
        "recall_at_5": rec[5] / n,
        "recall_at_10": rec[10] / n,
        "mrr_at_10": mrr / n,
        "ndcg_at_10": ndcg / n,
        "queries": n,
    }


# --------------------------------------------------------------------------
# systems
# --------------------------------------------------------------------------


def rank_random(docs, queries, seed=RANDOM_STATE):
    rng = random.Random(seed)  # noqa: S311 - reproducible sampling, not cryptography
    pool = list(range(len(docs)))
    out = {}
    for qid in queries:
        sample = rng.sample(pool, min(TOP_K + 1, len(pool)))
        out[qid] = [d for d in sample if d != qid][:TOP_K]
    return out


def rank_lexical(docs, queries):
    """Character n-gram TF-IDF. Robust to Russian morphology without a stemmer."""
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer

    texts = [d["text"] for d in docs]
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=2, max_features=200_000)
    matrix = vec.fit_transform(texts)
    out = {}
    for qid in queries:
        scores = (matrix @ matrix[qid].T).toarray().ravel()
        scores[qid] = -1.0
        out[qid] = np.argsort(-scores)[:TOP_K].tolist()
    return out


def rank_embeddings(docs, queries, model_name, batch_size=256, prefix=""):
    """Frozen sentence embeddings. Returns None when the model is unavailable."""
    try:
        import numpy as np
        from sentence_transformers import SentenceTransformer
    except ImportError:
        return None, "sentence-transformers is not installed"

    try:
        model = SentenceTransformer(model_name)
    except Exception as exc:
        return None, f"model load failed: {exc}"

    texts = [prefix + d["text"] for d in docs]
    emb = model.encode(
        texts, batch_size=batch_size, normalize_embeddings=True, show_progress_bar=False
    )
    emb = np.asarray(emb, dtype="float32")
    out = {}
    for qid in queries:
        scores = emb @ emb[qid]
        scores[qid] = -1.0
        out[qid] = np.argsort(-scores)[:TOP_K].tolist()
    return out, None


def slice_report(ranked, relevant, docs, key):
    """Break a result down by a document attribute, for honesty about mixes."""
    buckets = defaultdict(dict)
    for qid, order in ranked.items():
        buckets[docs[qid][key]][qid] = order
    out = {}
    for value, subset in buckets.items():
        if len(subset) < 30:
            continue
        out[value] = evaluate(subset, {q: relevant[q] for q in subset})
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--queries", type=int, default=DEFAULT_QUERIES)
    parser.add_argument("--models", nargs="*", default=["intfloat/multilingual-e5-small"])
    args = parser.parse_args()

    docs = load_corpus(args.corpus)
    queries, relevant, groups = build_query_set(docs, args.queries)
    sizes = [len(v) for v in relevant.values()]
    print(f"corpus {len(docs):,} docs, {len(groups):,} groups")
    print(f"queries {len(queries):,}, median relevant per query {sorted(sizes)[len(sizes) // 2]}")

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "corpus_documents": len(docs),
        "groups": len(groups),
        "relevance": "shared (region, topic, service), proxy rather than human judgment",
        "query_selection": (
            f"{MIN_QUERY_CHARS} to {MAX_QUERY_CHARS} characters, group size above one"
        ),
        "queries": len(queries),
        "systems": {},
        "limits": [
            "Queries are executor texts. Production queries are citizen texts.",
            "Proxy relevance rewards recovering the metadata grouping, not operator usefulness.",
            "No pure Kazakh documents exist in this corpus, so no kk slice can be reported.",
        ],
    }

    ranked = rank_random(docs, queries)
    report["systems"]["S0_random"] = evaluate(ranked, relevant)
    print(f"  {'S0_random':<34} R@10 {report['systems']['S0_random']['recall_at_10']:.4f}")

    lex = rank_lexical(docs, queries)
    report["systems"]["S1_char_tfidf"] = evaluate(lex, relevant)
    report["systems"]["S1_char_tfidf"]["by_region"] = slice_report(lex, relevant, docs, "region_id")
    print(f"  {'S1_char_tfidf':<34} R@10 {report['systems']['S1_char_tfidf']['recall_at_10']:.4f}")

    for model_name in args.models:
        prefix = "query: " if "e5" in model_name else ""
        emb, err = rank_embeddings(docs, queries, model_name, prefix=prefix)
        key = f"S2_{model_name.split('/')[-1]}"
        if emb is None:
            report["systems"][key] = {"skipped": err}
            print(f"  {key:<34} skipped: {err}")
            continue
        report["systems"][key] = evaluate(emb, relevant)
        report["systems"][key]["by_region"] = slice_report(emb, relevant, docs, "region_id")
        print(f"  {key:<34} R@10 {report['systems'][key]['recall_at_10']:.4f}")

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "retrieval_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nwritten {out / 'retrieval_report.json'}")


if __name__ == "__main__":
    main()
