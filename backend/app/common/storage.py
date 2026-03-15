"""MinIO / S3 helper – upload, download, and presign asset files."""

from __future__ import annotations

import logging
import tempfile
import uuid
from pathlib import Path
from typing import BinaryIO

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _get_s3_client():
    settings = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=f"http://{settings.minio_endpoint}",
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
        config=BotoConfig(signature_version="s3v4"),
        region_name="us-east-1",
    )


def ensure_bucket_exists() -> None:
    settings = get_settings()
    client = _get_s3_client()
    try:
        client.head_bucket(Bucket=settings.minio_bucket)
    except ClientError:
        client.create_bucket(Bucket=settings.minio_bucket)
        logger.info("Created bucket %s", settings.minio_bucket)


def upload_fileobj(
    fileobj: BinaryIO,
    file_name: str,
    content_type: str = "application/octet-stream",
) -> str:
    """Upload a file-like object to MinIO and return the storage key."""
    settings = get_settings()
    client = _get_s3_client()
    ensure_bucket_exists()

    ext = ""
    if "." in file_name:
        ext = "." + file_name.rsplit(".", 1)[-1]
    storage_key = f"uploads/{uuid.uuid4().hex}{ext}"

    client.upload_fileobj(
        fileobj,
        settings.minio_bucket,
        storage_key,
        ExtraArgs={"ContentType": content_type},
    )
    return storage_key


def download_asset_to_temp(storage_key: str, suffix: str = "") -> Path:
    """Download an object from MinIO to a temp file and return its path."""
    settings = get_settings()
    client = _get_s3_client()
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix or _guess_suffix(storage_key))
    client.download_fileobj(settings.minio_bucket, storage_key, tmp)
    tmp.close()
    return Path(tmp.name)


def generate_presigned_url(storage_key: str, expires: int = 3600) -> str:
    """Generate a presigned URL for reading an object from MinIO."""
    settings = get_settings()
    client = _get_s3_client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.minio_bucket, "Key": storage_key},
        ExpiresIn=expires,
    )


def _guess_suffix(key: str) -> str:
    if "." in key:
        return "." + key.rsplit(".", 1)[-1]
    return ""
