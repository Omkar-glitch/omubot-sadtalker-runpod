from pydantic import BaseModel, Field
from typing import Optional


class GenerateRequest(BaseModel):
    image_url: Optional[str] = Field(default=None, description="Public URL to the source face image")
    image_b64: Optional[str] = Field(default=None, description="Base64-encoded image (data URL or raw b64)")
    audio_url: Optional[str] = Field(default=None, description="Public URL to the speech audio (wav/mp3)")
    audio_b64: Optional[str] = Field(default=None, description="Base64-encoded audio")
    driver: str = Field(default="sadtalker", pattern="^(sadtalker|liveportrait)$")


class GenerateResponse(BaseModel):
    status: str
    video_url: Optional[str] = None
    message: Optional[str] = None


class HealthResponse(BaseModel):
    ok: bool = True
