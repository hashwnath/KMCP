"""Portable token counting utility.

Attempts to use ``tiktoken`` (accurate, GPT-compatible) but falls back to a
simple word-based estimator when tiktoken is unavailable — e.g. in Lambda
environments where native Rust extensions cannot be installed.
"""

from __future__ import annotations

try:
    import tiktoken as _tiktoken

    _encoder = _tiktoken.get_encoding("cl100k_base")

    def count_tokens(text: str) -> int:
        """Count tokens using tiktoken cl100k_base encoding."""
        return len(_encoder.encode(text))

    def encode(text: str) -> list[int]:
        """Encode text to token IDs."""
        return _encoder.encode(text)

    def decode(tokens: list[int]) -> str:
        """Decode token IDs back to text."""
        return _encoder.decode(tokens)

except ImportError:
    # Fallback: estimate ~0.75 tokens per word (conservative for English text).
    # This is accurate enough for chunking and quota enforcement.
    import re as _re

    def count_tokens(text: str) -> int:  # type: ignore[misc]
        """Estimate token count from word boundaries (tiktoken unavailable)."""
        words = _re.findall(r"\S+", text)
        return max(1, int(len(words) * 1.3))

    def encode(text: str) -> list[int]:  # type: ignore[misc]
        """Stub encoder — returns fake token IDs based on character positions."""
        return list(range(count_tokens(text)))

    def decode(tokens: list[int]) -> str:  # type: ignore[misc]
        """Stub decoder — not supported without tiktoken."""
        raise NotImplementedError("decode() requires tiktoken")
