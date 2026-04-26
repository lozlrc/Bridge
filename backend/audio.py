from __future__ import annotations

"""Audio file -> transcript string using faster-whisper, with demo-safe fallbacks."""
import os
import tempfile

try:
    from faster_whisper import WhisperModel
except ImportError:  # pragma: no cover - handled at runtime for demo environments
    WhisperModel = None

_model: WhisperModel | None = None
MOCK_TRANSCRIPT = (
    "This is a mock lecture transcript for demo purposes. "
    "The speaker is introducing a lesson, defining the main idea, and giving an example. "
    "Set MOCK_TRANSCRIBE=false and install faster-whisper to enable local transcription."
)


def _get_model() -> WhisperModel:
    if WhisperModel is None:
        raise RuntimeError("faster-whisper is not installed")

    global _model
    if _model is None:
        size = os.getenv("WHISPER_MODEL", "base")
        _model = WhisperModel(size, device="cpu", compute_type="int8")
    return _model


def transcribe(audio_bytes: bytes, suffix: str = ".webm") -> str:
    if os.getenv("MOCK_TRANSCRIBE", "true").lower() in ("1", "true", "yes"):
        return MOCK_TRANSCRIPT

    model = _get_model()
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(audio_bytes)
        tmp_path = f.name

    try:
        segments, _ = model.transcribe(tmp_path, beam_size=5)
        return " ".join(seg.text.strip() for seg in segments).strip()
    finally:
        os.unlink(tmp_path)
