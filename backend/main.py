"""FastAPI backend for the braille education device.

Endpoints:
  POST /image   — JPEG/PNG upload -> simplified text -> braille cells -> device preview
  POST /lecture — audio upload -> simplified text -> braille cells -> device preview
  GET  /health  — liveness check
"""
import os
import re
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

try:
    from .audio import _get_model, transcribe
    from .braille import louis, text_to_cells
    from .serial_out import prepare_device_payload, serial
    from .summarizer import Anthropic as SummaryAnthropic, summarize_transcript
    from .vision import Anthropic as VisionAnthropic, summarize_image
except ImportError:
    from audio import _get_model, transcribe
    from braille import louis, text_to_cells
    from serial_out import prepare_device_payload, serial
    from summarizer import Anthropic as SummaryAnthropic, summarize_transcript
    from vision import Anthropic as VisionAnthropic, summarize_image


def _flag(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).lower() in ("1", "true", "yes")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Warm up Whisper model so first request isn't slow
    app.state.audio_ready = False
    if not _flag("MOCK_TRANSCRIBE", True):
        try:
            _get_model()
            app.state.audio_ready = True
        except Exception:
            app.state.audio_ready = False
    yield


app = FastAPI(title="Accessible Learning Simplifier API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_AUDIO_TYPES = {
    "audio/webm",
    "audio/wav",
    "audio/x-wav",
    "audio/mpeg",
    "audio/mp3",
    "audio/ogg",
    "audio/mp4",
    "audio/x-m4a",
    "audio/aac",
}
ALLOWED_AUDIO_EXTENSIONS = {".webm", ".wav", ".mp3", ".ogg", ".mp4", ".m4a", ".aac"}


@app.get("/health")
def health():
    device_enabled = _flag("ENABLE_DEVICE_IO", False)
    device_format = os.getenv("DEVICE_FORMAT", "braille").strip().lower()
    return {
        "status": "ok",
        "demo_mode": _flag("MOCK_CLAUDE", True) or _flag("MOCK_TRANSCRIBE", True),
        "device_transport": {
            "enabled": device_enabled,
            "mode": "serial" if device_enabled else "preview-only",
            "format": device_format,
        },
        "services": {
            "vision": _flag("MOCK_CLAUDE", True) or VisionAnthropic is not None,
            "lecture_summary": _flag("MOCK_CLAUDE", True) or SummaryAnthropic is not None,
            "transcription": _flag("MOCK_TRANSCRIBE", True) or getattr(app.state, "audio_ready", False),
            "braille": louis is not None,
            "serial": serial is not None,
            "device_preview": True,
        },
    }


def _split_simple_sentences(text: str) -> list[str]:
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text.strip()) if part.strip()]
    return parts or ([text.strip()] if text.strip() else [])


def _trim_words(text: str, max_words: int) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text.strip()
    trimmed = " ".join(words[:max_words]).rstrip(",;:-")
    if trimmed and trimmed[-1] not in ".!?":
        trimmed += "."
    return trimmed


def _essentialize_text(mode: str, text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return cleaned

    sentences = _split_simple_sentences(cleaned)
    if mode == "image":
        essential = " ".join(sentences[:1]) if sentences else cleaned
        return _trim_words(essential, 18)

    essential = " ".join(sentences[:2]) if sentences else cleaned
    return _trim_words(essential, 28)


def _build_response(mode: str, simple_text: str, cells: bytes, device_payload: dict, transcript: str | None = None) -> dict:
    simple_text = _essentialize_text(mode, simple_text)
    simple_sentences = _split_simple_sentences(simple_text)
    response = {
        "mode": mode,
        "simple_text": simple_text,
        "simple_sentences": simple_sentences,
        "summary": simple_text,
        "cell_count": len(cells),
        "braille_preview": device_payload["preview"],
        "device": device_payload,
        # Preserve the previous field name so older frontend code does not break.
        "serial": device_payload,
    }
    if transcript is not None:
        response["transcript"] = transcript
    return response


def _audio_upload_allowed(file: UploadFile) -> bool:
    filename = (file.filename or "").lower()
    extension = os.path.splitext(filename)[1]
    content_type = (file.content_type or "").lower()
    return content_type in ALLOWED_AUDIO_TYPES or extension in ALLOWED_AUDIO_EXTENSIONS


@app.post("/image")
async def process_image(file: UploadFile = File(...)):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(400, f"Unsupported image type: {file.content_type}")

    image_bytes = await file.read()
    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(413, "Image too large (max 10 MB)")

    try:
        simple_text = summarize_image(image_bytes, media_type=file.content_type)
        cells = text_to_cells(simple_text)
        device_payload = prepare_device_payload(simple_text, cells)
    except Exception as exc:
        raise HTTPException(503, f"Image pipeline unavailable: {exc}") from exc

    return _build_response("image", simple_text, cells, device_payload)


@app.post("/lecture")
async def process_lecture(file: UploadFile = File(...)):
    if not _audio_upload_allowed(file):
        raise HTTPException(400, f"Unsupported audio type: {file.content_type}")

    audio_bytes = await file.read()
    if len(audio_bytes) > 50 * 1024 * 1024:
        raise HTTPException(413, "Audio too large (max 50 MB)")

    suffix = "." + (file.filename or "audio.webm").rsplit(".", 1)[-1]
    try:
        transcript = transcribe(audio_bytes, suffix=suffix)
        if not transcript:
            raise HTTPException(422, "Could not transcribe audio — check the recording")

        simple_text = summarize_transcript(transcript)
        cells = text_to_cells(simple_text)
        device_payload = prepare_device_payload(simple_text, cells)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(503, f"Lecture pipeline unavailable: {exc}") from exc

    return _build_response("lecture", simple_text, cells, device_payload, transcript=transcript)
