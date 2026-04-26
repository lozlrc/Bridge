from __future__ import annotations

"""Prepare braille cell bytes for a future ESP32/controller transport.

Frame: <cell_byte>* 0xFF
The device will buffer the message and render one 6-dot cell at a time.
0xFF signals end of message and is safe because valid 6-dot cells are 0x00-0x3F.
By default we stay in preview-only mode until device I/O is explicitly enabled.
"""
import os
import re
import time

try:
    import serial
except ImportError:  # pragma: no cover - handled at runtime for demo environments
    serial = None


END_OF_MESSAGE = 0xFF


def _flag(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).lower() in ("1", "true", "yes")


def _device_format() -> str:
    value = os.getenv("DEVICE_FORMAT", "braille").strip().lower()
    return value if value in {"braille", "text4"} else "braille"


def _serial_baud() -> int:
    default = "115200" if _device_format() == "text4" else "9600"
    return int(os.getenv("SERIAL_BAUD", default))


def _open() -> serial.Serial:
    if serial is None:
        raise RuntimeError("pyserial is not installed")

    port = os.getenv("SERIAL_PORT", "/dev/cu.usbmodem1101")
    baud = _serial_baud()
    s = serial.Serial(port, baud, timeout=2)
    time.sleep(2.0)  # Arduino auto-resets when the port opens
    return s


def send_cells(cells: bytes) -> None:
    with _open() as s:
        s.write(cells)
        s.write(bytes([END_OF_MESSAGE]))
        s.flush()


def _normalize_text4(text: str) -> str:
    cleaned = text.lower().replace("\n", " ")
    cleaned = re.sub(r"[^a-z0-9 !',.\-?#^]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or " "


def _text_to_chunks(text: str, width: int = 4) -> list[str]:
    normalized = _normalize_text4(text)
    return [normalized[i:i + width].ljust(width) for i in range(0, len(normalized), width)]


def send_text_chunks(text: str) -> None:
    chunk_delay_ms = int(os.getenv("SERIAL_CHUNK_DELAY_MS", "2200"))
    with _open() as s:
        for chunk in _text_to_chunks(text):
            s.write((chunk + "\n").encode("ascii"))
            s.flush()
            time.sleep(chunk_delay_ms / 1000)


def _prepare_braille_payload(cells: bytes) -> dict:
    frame = bytes(cells) + bytes([END_OF_MESSAGE])
    preview = " ".join(f"{b:02x}" for b in cells[:32])
    payload = {
        "transport": "serial",
        "format": "braille",
        "enabled": _flag("ENABLE_DEVICE_IO", False),
        "sent": False,
        "cell_count": len(cells),
        "cell_bytes": list(cells),
        "frame_bytes": list(frame),
        "preview": preview,
        "terminator": f"{END_OF_MESSAGE:02x}",
    }

    if not payload["enabled"]:
        payload["reason"] = "Device transport is disabled; preview mode only."
        return payload

    try:
        send_cells(cells)
        payload["sent"] = True
        return payload
    except Exception as e:
        payload["error"] = str(e)
        return payload


def _prepare_text4_payload(text: str) -> dict:
    chunks = _text_to_chunks(text)
    payload = {
        "transport": "serial",
        "format": "text4",
        "enabled": _flag("ENABLE_DEVICE_IO", False),
        "sent": False,
        "normalized_text": _normalize_text4(text),
        "chunk_count": len(chunks),
        "chunks": chunks,
        "preview": " | ".join(chunks[:8]),
        "delimiter": "\\n",
    }

    if not payload["enabled"]:
        payload["reason"] = "Device transport is disabled; preview mode only."
        return payload

    try:
        send_text_chunks(text)
        payload["sent"] = True
        return payload
    except Exception as e:
        payload["error"] = str(e)
        return payload


def prepare_device_payload(text: str, cells: bytes) -> dict:
    """Return a transport payload matching the configured device format."""
    if _device_format() == "text4":
        return _prepare_text4_payload(text)
    return _prepare_braille_payload(cells)
