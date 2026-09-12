"""Evidence-backed lexical/vector retrieval and duplicate proposals."""

from .router import create_retrieval_router, synthetic_corpus
from .service import HybridRetriever

__all__ = ["HybridRetriever", "create_retrieval_router", "synthetic_corpus"]
