import os
import glob
import subprocess
import tempfile
import sys
from typing import Optional


class BasePipeline:
    def __init__(self):
        self.initialized = False

    def load(self):
        self.initialized = True

    def generate(self, image_path: str, audio_path: str) -> str:
        raise NotImplementedError


class SadTalkerPipeline(BasePipeline):
    def __init__(self, root: Optional[str] = None):
        super().__init__()
        self.root = root or os.environ.get("SADTALKER_ROOT", "/opt/SadTalker")

    def _ensure_models(self):
        ckpt = os.path.join(self.root, "checkpoints")
        gfp = os.path.join(self.root, "gfpgan", "weights")
        if not (os.path.isdir(ckpt) and os.path.isdir(gfp)):
            script = os.path.join(self.root, "scripts", "download_models.sh")
            if not os.path.isfile(script):
                raise FileNotFoundError("SadTalker repo not found or incomplete. Set SADTALKER_ROOT.")
            subprocess.run(["bash", script], cwd=self.root, check=True)

    def load(self):
        if not os.path.isdir(self.root):
            raise FileNotFoundError(
                f"SadTalker root not found at {self.root}. Bake it into the image or mount it."
            )
        self._ensure_models()
        super().load()

    def generate(self, image_path: str, audio_path: str) -> str:
        # Run SadTalker CLI and collect the produced mp4
        outdir = tempfile.mkdtemp(prefix="sadtalker_")
        # Use absolute interpreter; Runpod serverless images don't provide 'python'
        cmd = [
            "/usr/bin/python3", "inference.py",
            "--driven_audio", audio_path,
            "--source_image", image_path,
            "--result_dir", outdir,
            "--still",
            "--preprocess", "full",
            "--enhancer", "gfpgan",
        ]
        subprocess.run(cmd, cwd=self.root, check=True)
        videos = glob.glob(os.path.join(outdir, "**", "*.mp4"), recursive=True)
        if not videos:
            raise RuntimeError("SadTalker produced no output video")
        # Heuristic: pick the newest file
        videos.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        return videos[0]


class LivePortraitPipeline(BasePipeline):
    def load(self):
        # TODO: load LivePortrait models/weights, set self.initialized
        super().load()

    def generate(self, image_path: str, audio_path: str) -> str:
        # TODO: implement LivePortrait inference and return path to output mp4
        raise NotImplementedError("LivePortrait inference not implemented yet")


def get_pipeline(name: str) -> BasePipeline:
    if name == "sadtalker":
        return SadTalkerPipeline()
    if name == "liveportrait":
        return LivePortraitPipeline()
    raise ValueError(f"Unknown driver: {name}")
