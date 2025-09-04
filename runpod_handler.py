import os
import traceback
import runpod

from app.utils import fetch_to_file
from app.pipeline import get_pipeline
from app.storage import maybe_upload


def handler(event):
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

        pipeline = get_pipeline(driver)
        if not pipeline.initialized:
            pipeline.load()

        video_path = pipeline.generate(image_path=image_path, audio_path=audio_path)
        url = maybe_upload(video_path)
        return {"status": "completed", "video_url": url or video_path}
    except Exception as e:
        return {"status": "error", "message": str(e), "trace": traceback.format_exc()}


runpod.serverless.start({"handler": handler})
