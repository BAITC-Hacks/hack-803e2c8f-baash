"""Deterministic CPU vector fallback with no model or network dependency."""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Iterable

TOKEN_RE = re.compile(r"[\w]+", re.UNICODE)


def tokens(text: str) -> frozenset[str]:
    return frozenset(TOKEN_RE.findall(text.casefold()))


class HashVectorProvider:
    """Stable signed-hash embeddings used as an explicit fallback only."""

    def __init__(self, dimensions: int = 64) -> None:
        if dimensions < 8:
            raise ValueError("dimensions must be at least 8")
        self.dimensions = dimensions

    def embed(self, text: str) -> tuple[float, ...]:
        values = [0.0] * self.dimensions
        for token in tokens(text):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] & 1 else -1.0
            values[index] += sign
        norm = math.sqrt(sum(value * value for value in values))
        if norm == 0:
            return tuple(values)
        return tuple(value / norm for value in values)

    def similarity(self, left: str, right: str) -> float:
        left_vector = self.embed(left)
        right_vector = self.embed(right)
        return sum(a * b for a, b in zip(left_vector, right_vector, strict=True))


def lexical_similarity(left: str, right: str) -> float:
    left_tokens = tokens(left)
    right_tokens = tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def stable_rank(values: Iterable[tuple[str, float]]) -> list[tuple[str, float]]:
    return sorted(values, key=lambda item: (-item[1], item[0]))
