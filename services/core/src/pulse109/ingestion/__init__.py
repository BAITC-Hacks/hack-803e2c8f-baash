"""Synthetic JSONL ingestion and data-quality primitives for Pulse 109."""

from .pipeline import ImportResult, ingest_jsonl

__all__ = ["ImportResult", "ingest_jsonl"]
