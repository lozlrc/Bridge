"""Text -> braille cells.

liblouis returns Unicode braille (U+2800-U+28FF). Each glyph's lower 8 bits
encode the dot pattern: bit0=dot1, bit1=dot2, bit2=dot3, bit3=dot4, bit4=dot5,
bit5=dot6, bit6=dot7, bit7=dot8. We use 6-dot cells (mask 0x3F), which keeps
every cell in 0x00-0x3F and leaves 0xFF free as our message terminator.
"""
import os

try:
    import louis
except ImportError:  # pragma: no cover - handled at runtime for demo environments
    louis = None

GRADE_TABLE = {
    "1": ["en-us-g1.ctb"],
    "2": ["en-us-g2.ctb"],
}


def _table() -> list[str]:
    grade = os.getenv("BRAILLE_GRADE", "2").strip()
    return GRADE_TABLE.get(grade, GRADE_TABLE["2"])


def text_to_unicode_braille(text: str) -> str:
    if louis is None:
        raise RuntimeError("liblouis is not installed")
    return louis.translateString(_table(), text)


FALLBACK_ASCII_TO_CELL = {
    " ": 0x00,
    "a": 0x01,
    "b": 0x03,
    "c": 0x09,
    "d": 0x19,
    "e": 0x11,
    "f": 0x0B,
    "g": 0x1B,
    "h": 0x13,
    "i": 0x0A,
    "j": 0x1A,
    "k": 0x05,
    "l": 0x07,
    "m": 0x0D,
    "n": 0x1D,
    "o": 0x15,
    "p": 0x0F,
    "q": 0x1F,
    "r": 0x17,
    "s": 0x0E,
    "t": 0x1E,
    "u": 0x25,
    "v": 0x27,
    "w": 0x3A,
    "x": 0x2D,
    "y": 0x3D,
    "z": 0x35,
    ",": 0x02,
    ";": 0x06,
    ":": 0x12,
    ".": 0x32,
    "!": 0x16,
    "?": 0x26,
    "-": 0x24,
    "'": 0x04,
    "\"": 0x14,
    "/": 0x0C,
}


def _fallback_text_to_cells(text: str) -> bytes:
    cells = bytearray()
    for ch in text.lower():
        if ch.isdigit():
            ch = "abcdefghij"[int(ch) - 1] if ch != "0" else "j"
        cells.append(FALLBACK_ASCII_TO_CELL.get(ch, 0x00))
    return bytes(cells)


def text_to_cells(text: str) -> bytes:
    """Translate `text` and return one byte per braille cell (6-dot, lower 6 bits)."""
    if louis is None:
        return _fallback_text_to_cells(text)

    glyphs = text_to_unicode_braille(text)
    cells = bytearray()
    for ch in glyphs:
        code = ord(ch)
        if 0x2800 <= code <= 0x28FF:
            cells.append(code & 0x3F)
        elif ch == " ":
            cells.append(0x00)
        elif ch == "\n":
            cells.append(0x00)
        # silently skip anything else (control chars, stray ASCII)
    return bytes(cells)
