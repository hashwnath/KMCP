"""LogEmailSender — prints magic links to stdout for local dev.

Also persists the most recent message per recipient under
``LOCAL_DATA_DIR/email_outbox.json`` so the frontend can offer a "view
last magic link" dev affordance instead of forcing the user to dig
through docker logs.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from src.common.config import get_config

logger = logging.getLogger(__name__)


class LogEmailSender:
    def _outbox_path(self) -> Path:
        base = Path(get_config().local_data_dir).expanduser().resolve()
        base.mkdir(parents=True, exist_ok=True)
        return base / "email_outbox.json"

    def send(
        self,
        to_address: str,
        subject: str,
        body_text: str,
        from_address: str = "",
    ) -> None:
        # 1) Stdout
        logger.warning(
            "[LOCAL EMAIL] to=%s subject=%s\n%s", to_address, subject, body_text
        )
        # 2) Outbox (atomic write)
        path = self._outbox_path()
        outbox = {}
        if path.exists():
            try:
                outbox = json.loads(path.read_text())
            except Exception:
                outbox = {}
        outbox[to_address] = {
            "to": to_address,
            "from": from_address,
            "subject": subject,
            "body": body_text,
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".outbox-")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(outbox, f, indent=2)
            os.replace(tmp, path)
        except Exception:
            try:
                os.unlink(tmp)
            except FileNotFoundError:
                pass
            raise
