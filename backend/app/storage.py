"""Document storage: Google Cloud Storage, or a local directory for tests and offline work.

GCS auth: a service-account JSON key (HEATMARK_GCS_CREDENTIALS_FILE), or else Application
Default Credentials (`gcloud auth application-default login`, or the runtime's identity when deployed).
"""

import asyncio
import uuid
from functools import lru_cache
from pathlib import Path

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
