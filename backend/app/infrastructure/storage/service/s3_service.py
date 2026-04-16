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
        client_kwargs = {
            "service_name": "s3",
            "config": Config(signature_version="s3v4"),
        }

        if settings.AWS_REGION:
            client_kwargs["region_name"] = settings.AWS_REGION

        if settings.AWS_S3_ENDPOINT_URL:
            client_kwargs["endpoint_url"] = settings.AWS_S3_ENDPOINT_URL

        # Let boto3 resolve credentials from the normal AWS provider chain:
        # env vars, shared credentials/config files, IAM role, ECS task role, etc.
        self.s3_client = boto3.client(**client_kwargs)

    def generate_upload_url(self, file_key: str, content_type: str) -> str:
        return self.s3_client.generate_presigned_url(
            ClientMethod="put_object",
            Params={"Bucket": settings.S3_BUCKET_NAME, "Key": file_key,
                    "ContentType": content_type, "ContentLength": MAX_FILE_SIZE},
            ExpiresIn=300,
        )

    def generate_read_url(self, file_key: str) -> str:
        return self.s3_client.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": settings.S3_BUCKET_NAME, "Key": file_key},
            ExpiresIn=3600,
        )


@lru_cache(maxsize=1)
def get_r2_service() -> R2Service:
    return R2Service()
