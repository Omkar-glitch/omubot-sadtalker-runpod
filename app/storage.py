import os
import time
import json
import base64
from typing import Optional, Tuple


def _gcs_client():
    from google.cloud import storage  # lazy import
    from google.oauth2 import service_account

    sa_json = os.getenv("GCP_SA_JSON")
    if sa_json:
        try:
            info = json.loads(sa_json)
        except Exception:
            try:
                info = json.loads(base64.b64decode(sa_json).decode("utf-8"))
            except Exception:
                info = None
        if info:
            creds = service_account.Credentials.from_service_account_info(info)
            project = info.get("project_id")
            return storage.Client(project=project, credentials=creds)
    # Fallback to default (uses GOOGLE_APPLICATION_CREDENTIALS or metadata)
    return storage.Client()


def _gcs_upload_and_url(local_path: str) -> Tuple[str, str]:
    from google.cloud import storage

    bucket_name = os.getenv("MEDIA_BUCKET")
    if not bucket_name:
        raise RuntimeError("MEDIA_BUCKET env var is required for GCS upload")

    client = _gcs_client()
    bucket = client.bucket(bucket_name)

    # Allow caller to pass desired object prefix; otherwise use timestamped path
    prefix = os.getenv("MEDIA_PREFIX", "avatar-outputs/")
    filename = os.path.basename(local_path)
    object_name = f"{prefix}{int(time.time())}-{filename}"

    blob = bucket.blob(object_name)
    blob.upload_from_filename(local_path, content_type="video/mp4")

    # Signed URL by default; make_public if explicitly requested
    if os.getenv("GCS_PUBLIC", "false").lower() in ("1", "true", "yes"): 
        blob.make_public()
        return object_name, blob.public_url

    # Generate a V4 signed URL
    ttl = int(os.getenv("GCS_SIGNED_URL_TTL", "86400"))  # seconds
    url = blob.generate_signed_url(version="v4", expiration=ttl, method="GET")
    return object_name, url


def maybe_upload(local_path: str) -> Optional[str]:
    provider = os.getenv("UPLOAD_PROVIDER", "none").lower()
    if provider == "gcs":
        _, url = _gcs_upload_and_url(local_path)
        return url
    # no upload; return None to let caller decide what to return
    return None
