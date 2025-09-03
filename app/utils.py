import base64
import os
import tempfile
import requests
from typing import Optional


def _write_temp(data: bytes, suffix: str) -> str:
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    return path


def fetch_to_file(url: Optional[str] = None, b64: Optional[str] = None, suffix: str = "") -> str:
    if url:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return _write_temp(resp.content, suffix)
    if b64:
        payload = b64
        if "," in payload:
            payload = payload.split(",", 1)[1]
        return _write_temp(base64.b64decode(payload), suffix)
    raise ValueError("Either url or b64 must be provided")
