import logging
from functools import lru_cache

import boto3
from botocore.config import Config

from app.core.config import settings

logger = logging.getLogger(__name__)

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "image/jpeg",
    "image/png",
    "image/webp",
}

ALLOWED_EXTENSIONS = {"pdf", "doc", "docx", "jpg", "jpeg", "png", "webp"}

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


class R2Service:
    def __init__(self) -> None:
        self.s3_client = boto3.client(
            service_name="s3",
            endpoint_url=f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            region_name="auto",
            config=Config(signature_version="s3v4"),
        )

    def generate_upload_url(self, file_key: str, content_type: str) -> str:
        """Generate a presigned PUT URL for direct browser upload."""
        return self.s3_client.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": settings.R2_BUCKET_NAME,
                "Key": file_key,
                "ContentType": content_type,
                "ContentLength": MAX_FILE_SIZE,
            },
            ExpiresIn=300,
        )

    def generate_read_url(self, file_key: str) -> str:
        """Generate a presigned GET URL to download/view a file."""
        return self.s3_client.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": settings.R2_BUCKET_NAME, "Key": file_key},
            ExpiresIn=3600,
        )


@lru_cache(maxsize=1)
def get_r2_service() -> R2Service:
    """Lazy-initialize R2Service on first use (not at import time)."""
    return R2Service()
