"""Email sender Protocol (magic-link auth, future digests)."""

from __future__ import annotations

from typing import Protocol


class EmailSender(Protocol):
    """Minimal email sender contract."""

    def send(
        self,
        to_address: str,
        subject: str,
        body_text: str,
        from_address: str = "",
    ) -> None: ...
