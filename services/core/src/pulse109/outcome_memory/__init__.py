"""Governed retrieval of evidence-backed, human-confirmed outcomes."""

from .models import (
    EvidenceProvenance,
    OutcomeCandidate,
    OutcomeMemoryQuery,
    OutcomeMemoryResult,
    OutcomeProvenance,
)
from .postgres import (
    OutcomeAssemblyInspection,
    OutcomeCorpusUnavailable,
    PostgresOutcomeMemoryReader,
)
from .service import OutcomeMemory, OutcomeMemoryReader
from .synthetic import SYNTHETIC_LABEL, SyntheticOutcomeMemoryReader

__all__ = [
    "SYNTHETIC_LABEL",
    "EvidenceProvenance",
    "OutcomeAssemblyInspection",
    "OutcomeCandidate",
    "OutcomeCorpusUnavailable",
    "OutcomeMemory",
    "OutcomeMemoryQuery",
    "OutcomeMemoryReader",
    "OutcomeMemoryResult",
    "OutcomeProvenance",
    "PostgresOutcomeMemoryReader",
    "SyntheticOutcomeMemoryReader",
]
