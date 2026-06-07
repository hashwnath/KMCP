"""S3 implementation of the ObjectStorage Protocol."""

from __future__ import annotations

from src.common.aws_clients import get_s3_client
from src.common.config import get_config


class S3ObjectStorage:
    def _bucket(self) -> str:
        return get_config().content_bucket

    def put(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> None:
        get_s3_client().put_object(
            Bucket=self._bucket(),
            Key=key,
            Body=data,
            ContentType=content_type,
        )

    def get(self, key: str) -> bytes:
        resp = get_s3_client().get_object(Bucket=self._bucket(), Key=key)
        return resp["Body"].read()

    def delete(self, key: str) -> None:
        get_s3_client().delete_object(Bucket=self._bucket(), Key=key)

    def presigned_upload_url(
        self,
        key: str,
        content_type: str,
        expires_in_seconds: int = 3600,
    ) -> str:
        return get_s3_client().generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": self._bucket(),
                "Key": key,
                "ContentType": content_type,
            },
            ExpiresIn=expires_in_seconds,
        )
