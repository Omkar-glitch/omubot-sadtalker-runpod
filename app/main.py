import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from .schemas import GenerateRequest, GenerateResponse, HealthResponse
from .utils import fetch_to_file
from .pipeline import get_pipeline
from .storage import maybe_upload

app = FastAPI(title="Avatar Service", version="0.1.0")


@app.get("/healthz", response_model=HealthResponse)
def healthz():
    return HealthResponse(ok=True)


@app.post("/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest):
    try:
        image_path = fetch_to_file(url=req.image_url, b64=req.image_b64, suffix=".png")
        audio_path = fetch_to_file(url=req.audio_url, b64=req.audio_b64, suffix=".wav")

        pipeline = get_pipeline(req.driver)
        if not pipeline.initialized:
            pipeline.load()

        try:
            video_path = pipeline.generate(image_path=image_path, audio_path=audio_path)
            url = maybe_upload(video_path)
            return GenerateResponse(status="completed", video_url=url or video_path)
        except NotImplementedError as nie:
            return GenerateResponse(status="error", message=str(nie))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
