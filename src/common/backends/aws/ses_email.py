"""SES implementation of the EmailSender Protocol."""

from __future__ import annotations

from src.common.aws_clients import get_ses_client
from src.common.config import get_config


class SesEmailSender:
    def send(
        self,
        to_address: str,
        subject: str,
        body_text: str,
        from_address: str = "",
    ) -> None:
        cfg = get_config()
        source = from_address or cfg.ses_from_email
        if not source:
            raise RuntimeError("SES_FROM_EMAIL is not configured")
        get_ses_client().send_email(
            Source=source,
            Destination={"ToAddresses": [to_address]},
            Message={
                "Subject": {"Data": subject},
                "Body": {"Text": {"Data": body_text}},
            },
        )
