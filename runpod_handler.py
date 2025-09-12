import os
import json
import stat
import traceback
import runpod

from app.utils import fetch_to_file
from app.pipeline import get_pipeline
from app.storage import maybe_upload

LEGACY_EPOCH_URL = "https://github.com/Winfredy/SadTalker/releases/download/v0.0.2/epoch_20.pth"
LEGACY_EPOCH_PATH = "/opt/SadTalker/checkpoints/epoch_20.pth"

# Cache pipelines across invocations (warm container) to avoid re-initialization cost
_PIPELINES = {}

def ensure_legacy_checkpoint():
    try:
        ckpt_dir = os.path.dirname(LEGACY_EPOCH_PATH)
        if not os.path.isfile(LEGACY_EPOCH_PATH):
            os.makedirs(ckpt_dir, exist_ok=True)
            import requests
            r = requests.get(LEGACY_EPOCH_URL, stream=True, timeout=300)
            r.raise_for_status()
            with open(LEGACY_EPOCH_PATH, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)
    except Exception:
        # Best-effort; SadTalker may use safetensors path instead
        pass

def handler(event):
    # Prefer explicit creds from GCP_SA_JSON; unset default file var to avoid invalid /tmp/gcp.json
    try:
        if os.getenv("GCP_SA_JSON"):
            os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
    except Exception:
        pass
    try:
        inp = event.get("input", {})
        # Lightweight readiness/ping that avoids running a full job
        if inp.get("ping"):
            return {
                "status": "ok",
                "engine": inp.get("driver", "sadtalker"),
                "appVersion": os.getenv("APP_VERSION", "")
            }
        driver = inp.get("driver", "sadtalker")
        image_url = inp.get("image_url")
        image_b64 = inp.get("image_b64")
        audio_url = inp.get("audio_url")
        audio_b64 = inp.get("audio_b64")

        image_path = fetch_to_file(url=image_url, b64=image_b64, suffix=".png")
        audio_path = fetch_to_file(url=audio_url, b64=audio_b64, suffix=".wav")

        pipeline = _PIPELINES.get(driver)
        if pipeline is None:
            pipeline = get_pipeline(driver)
            _PIPELINES[driver] = pipeline
        if not pipeline.initialized:
            pipeline.load()

        # Ensure legacy model exists if SadTalker falls back to old checkpoints
        ensure_legacy_checkpoint()

        video_path = pipeline.generate(image_path=image_path, audio_path=audio_path)

        # If an upload_url is provided, PUT the file there (presigned URL), then return view_url
        upload_url = inp.get("upload_url")
        view_url = inp.get("view_url")
        if upload_url:
            import requests
            with open(video_path, "rb") as f:
                resp = requests.put(upload_url, data=f, headers={"Content-Type": inp.get("content_type", "video/mp4")}, timeout=600)
                if resp.status_code not in (200, 201):
                    return {"status": "error", "message": f"Upload failed: {resp.status_code} {resp.text[:200]}"}
            return {"status": "completed", "video_url": view_url or video_path}

        # Fallback: try provider-side upload if configured
        url = maybe_upload(video_path)
        return {"status": "completed", "video_url": url or video_path}
    except Exception as e:
        return {"status": "error", "message": str(e), "trace": traceback.format_exc()}


runpod.serverless.start({"handler": handler})
