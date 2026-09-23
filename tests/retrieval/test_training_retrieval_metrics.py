import json

import pytest

from ml.training import retrieval_eval, retrieval_finetune


def test_retrieval_eval_reports_hit_rate_and_excludes_self_before_cutoff():
    result = retrieval_eval.evaluate(
        {0: [0, 1, 2]},
        {0: {1, 2}},
        k=2,
    )

    assert result["hit_rate_at_1"] == 1.0
    assert result["hit_rate_at_5"] == 1.0
    assert result["hit_rate_at_10"] == 1.0
    assert "recall_at_10" not in result
    # Both relevant documents are retrieved after self is removed, so nDCG
    # is perfect at the requested cutoff.
    assert result["ndcg_at_10"] == 1.0


def test_finetune_eval_uses_same_hit_rate_semantics_and_self_exclusion():
    result = retrieval_finetune.evaluate(
        {0: [0, 3, 1, 2]},
        {0: {1, 2}},
        k=2,
    )

    assert result["hit_rate_at_1"] == 0.0
    assert result["hit_rate_at_5"] == 1.0
    assert result["hit_rate_at_10"] == 1.0
    assert "recall_at_1" not in result


def test_random_baseline_never_returns_query_document():
    docs = [{"text": "doc"} for _ in range(3)]

    ranked = retrieval_eval.rank_random(docs, [0, 1, 2], seed=7)
    assert all(qid not in order for qid, order in ranked.items())


@pytest.mark.parametrize(
    "loader",
    [retrieval_eval.load_corpus, retrieval_finetune.load],
)
def test_corpus_loaders_reject_withheld_text_placeholders(tmp_path, loader):
    corpus = tmp_path / "corpus.jsonl"
    corpus.write_text(
        json.dumps(
            {
                "text": "[WITHHELD_PENDING_PRIVACY_REVIEW]",
                "region_id": "TEST",
                "topic_label": "topic",
                "service_label": "service",
                "received_at": "2026-01-01T00:00:00+00:00",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="withheld text placeholders"):
        loader(corpus)
