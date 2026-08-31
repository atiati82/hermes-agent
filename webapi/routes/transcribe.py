"""
POST /v1/audio/transcriptions

OpenAI-compatible audio transcription endpoint backed by faster-whisper.
Accepts multipart/form-data with a `file` field (audio bytes).
Optional `language` field forces the language (e.g. "de", "en").
Returns {"text": "..."} on success.
"""

import asyncio
import logging
import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)
router = APIRouter()

SUPPORTED_EXTENSIONS = {".ogg", ".mp3", ".wav", ".m4a", ".webm", ".mp4", ".flac", ".aac"}
DEFAULT_MODEL = os.getenv("HERMES_STT_MODEL", "base")


@router.post("/v1/audio/transcriptions")
async def transcribe_audio(
    file: UploadFile = File(...),
    language: str = Form(default=""),
):
    """Transcribe an audio file using local faster-whisper (free, no API key)."""
    suffix = Path(file.filename or "audio.ogg").suffix.lower() or ".ogg"
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {suffix}")

    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty file")

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        result = await asyncio.to_thread(_transcribe, tmp_path, language or None)
        return JSONResponse({"text": result})
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _transcribe(file_path: str, language: str | None) -> str:
    """Run faster-whisper synchronously (called via to_thread)."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise RuntimeError(
            "faster-whisper is not installed. "
            "Run: pip install 'faster-whisper>=1.0.0,<2'"
        )

    model = WhisperModel(DEFAULT_MODEL, device="auto", compute_type="auto")
    kwargs = {"beam_size": 5}
    if language:
        kwargs["language"] = language

    segments, info = model.transcribe(file_path, **kwargs)
    transcript = " ".join(seg.text.strip() for seg in segments)
    logger.info(
        "Transcribed via local whisper (model=%s, lang=%s, %.1fs)",
        DEFAULT_MODEL, info.language, info.duration,
    )
    return transcript
