"""A demonstration corpus has to be unmistakable for a real one.

The danger is not that these records are wrong. It is that somebody quotes a
median resolution time from them in a production claim. Every record therefore
carries its synthetic classification in its own provenance, and the reader
refuses to answer a caller that has not accepted synthetic data.
"""

from pulse109.outcome_memory import SYNTHETIC_LABEL
from pulse109.outcome_memory.models import OutcomeMemoryQuery
from pulse109.outcome_memory.synthetic import SyntheticOutcomeMemoryReader, _terms


def query(*, allow_synthetic: bool) -> OutcomeMemoryQuery:
    from uuid import uuid4

    return OutcomeMemoryQuery(
        request_id=uuid4(),
        region_id="ALA",
        service_id="service:water",
        topic_id="topic:water",
        terms=("water",),
        limit=5,
        allow_synthetic=allow_synthetic,
    )


def test_reader_refuses_a_caller_that_did_not_accept_synthetic_data() -> None:
    reader = SyntheticOutcomeMemoryReader("postgresql://unused/unused")
    # No connection is attempted, because the answer is already no.
    assert list(reader.read_resolved_candidates(query(allow_synthetic=False))) == []


def test_an_unreachable_database_yields_nothing_rather_than_raising() -> None:
    """The war room must survive a corpus that is not there."""
    reader = SyntheticOutcomeMemoryReader("postgresql://127.0.0.1:1/nonexistent")
    assert list(reader.read_resolved_candidates(query(allow_synthetic=True))) == []


def test_retrieval_terms_are_controlled_codes() -> None:
    terms = _terms("topic:water", "service:water", "REPAIR_VERIFIED")
    assert terms == ("water", "repair_verified")
    for term in terms:
        assert term.replace("_", "a").isalnum()
        assert term.islower()


def test_terms_never_end_up_empty() -> None:
    assert _terms(None, None, "X") == ("x",)


def test_the_synthetic_label_is_explicit() -> None:
    assert "SYNTHETIC" in SYNTHETIC_LABEL
