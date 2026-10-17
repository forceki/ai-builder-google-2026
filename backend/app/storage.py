"""Document storage: Google Cloud Storage, or a local directory for tests and offline work.

GCS auth: a service-account JSON key (HEATMARK_GCS_CREDENTIALS_FILE), or else Application
Default Credentials (`gcloud auth application-default login`, or the runtime's identity when deployed).
"""

import asyncio
import uuid
from datetime import timedelta
from functools import lru_cache
from pathlib import Path

import google.auth.credentials
import google.auth.transport.requests
from google.cloud import storage as gcs

from app.config import get_settings


def new_key(project_no: str, filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    return f"{project_no}/{uuid.uuid4().hex}{suffix}"


async def put(bucket: str, key: str, data: bytes, content_type: str) -> None:
    if get_settings().storage_backend == "local":
        path = _local_path(bucket, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(path.write_bytes, data)
        return
    blob = _gcs().bucket(bucket).blob(key)
    # Keys are unique; refuse to overwrite an existing object.
    await asyncio.to_thread(blob.upload_from_string, data, content_type=content_type, if_generation_match=0)


async def get(bucket: str, key: str) -> bytes:
    if get_settings().storage_backend == "local":
        return await asyncio.to_thread(_local_path(bucket, key).read_bytes)
    blob = _gcs().bucket(bucket).blob(key)
    return await asyncio.to_thread(blob.download_as_bytes)


async def signed_url(bucket: str, key: str, *, filename: str, content_type: str, minutes: int) -> str | None:
    if get_settings().storage_backend == "local":
        return None
    return await asyncio.to_thread(_sign, bucket, key, filename, content_type, minutes)


def _sign(bucket: str, key: str, filename: str, content_type: str, minutes: int) -> str:
    client = _gcs()
    safe_name = filename.replace('"', "").replace("\\", "")
    kwargs = {}
    creds = client._credentials
    if not isinstance(creds, google.auth.credentials.Signing):
        creds.refresh(google.auth.transport.requests.Request())
        kwargs = {"service_account_email": creds.service_account_email, "access_token": creds.token}
    return client.bucket(bucket).blob(key).generate_signed_url(
        version="v4",
        expiration=timedelta(minutes=minutes),
        method="GET",
        response_type=content_type,
        response_disposition=f'inline; filename="{safe_name}"',
        **kwargs,
    )


async def exists(bucket: str, key: str) -> bool:
    if get_settings().storage_backend == "local":
        return _local_path(bucket, key).is_file()
    return await asyncio.to_thread(_gcs().bucket(bucket).blob(key).exists)


@lru_cache
def _gcs() -> gcs.Client:
    s = get_settings()
    if s.gcs_credentials_file:
        return gcs.Client.from_service_account_json(str(s.gcs_credentials_file.expanduser()), project=s.gcp_project)
    return gcs.Client(project=s.gcp_project)


def _local_path(bucket: str, key: str) -> Path:
    root = (get_settings().storage_dir / bucket).resolve()
    path = (root / key).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"storage key escapes bucket: {key!r}")
    return path
