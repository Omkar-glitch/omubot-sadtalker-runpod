# Avatar Service (SadTalker/LivePortrait)

This microservice generates talking‑head videos from a source image and a speech audio file. It runs as a standalone HTTP service (FastAPI) designed for GPU environments (Runpod, local CUDA), while keeping the existing D‑ID integration intact. SadTalker is the primary engine; D‑ID remains as a commented fallback in the orchestrator.

## Features
- Pluggable drivers: `sadtalker` (primary), `liveportrait` (optional; requires driving video).
- Simple REST API, health checks, structured logs.
- GPU‑ready Docker image (CUDA 12.1 base), ffmpeg preinstalled.

## Quickstart (HTTP mode)
- SadTalker build (CUDA 11.7): `docker build -f Dockerfile.sadtalker -t avatar-service:sadtalker .`
- Run: `docker run --gpus all -e SADTALKER_ROOT=/opt/SadTalker -p 8001:8001 avatar-service:sadtalker`
- Health: `curl http://localhost:8001/healthz`

## API
- `POST /generate`
  - Body: `{ "image_url"|"image_b64", "audio_url"|"audio_b64", "driver": "sadtalker"|"liveportrait" }`
  - Response: `{ "status": "queued|completed|error", "video_url"?: string, "message"?: string }`
- `GET /healthz` → `{ "ok": true }`

### Optional upload to GCS
- Set env: `UPLOAD_PROVIDER=gcs`, `MEDIA_BUCKET=<bucket>`, optionally `MEDIA_PREFIX=avatar-outputs/`, `GCS_SIGNED_URL_TTL=86400` or `GCS_PUBLIC=true`.
- Service will upload the mp4 to the bucket and return a signed/public URL in `video_url`.

## Orchestrator integration
Set a feature flag/env in the orchestrator to pick a provider (SadTalker default):
- `AVATAR_PROVIDER=sadtalker` (default). Use `d-id` to fallback.
- `AVATAR_SERVICE_BASEURL=http://avatar-service:8001` (when not using D‑ID)
 - If using GCS uploads from the service, no extra change needed. If not, orchestrator should download/file-serve.

Make SadTalker the default path; keep the D‑ID call in place but commented alongside, so reverting is trivial.

## Implementation notes
- This repo ships a skeleton. Model downloads/inits are deferred to driver modules.
- Pin Torch/CUDA versions to avoid dependency issues. Suggested: Python 3.10, Torch 2.1.x + cu121.
- Use HTTP mode on Runpod for simplicity (no worker SDK required).

## Roadmap
- Upload generated mp4 to GCS/S3 and return a signed URL.
- Implement `LivePortraitPipeline` (requires driving video) as optional engine.
- Batch generation (optional), background job queue (optional).

## Orchestrator patch example
Python (FastAPI) pseudo‑diff to set SadTalker as default while keeping D‑ID commented:

```python
provider = os.getenv("AVATAR_PROVIDER", "sadtalker")
if provider == "sadtalker":
    # New path (active)
    resp = requests.post(f"{os.getenv('AVATAR_SERVICE_BASEURL')}/generate", json={
        "image_url": avatar_img_url,
        "audio_url": tts_audio_url,
        "driver": "sadtalker",
    }).json()
    video_url = resp.get("video_url")
else:
    # Previous D‑ID implementation (kept for rollback)
    # video_url = create_did_talking_avatar(image_url=avatar_img_url, audio_url=tts_audio_url)
    raise RuntimeError("D-ID path disabled by default. Set AVATAR_PROVIDER=d-id to re‑enable.")
```
