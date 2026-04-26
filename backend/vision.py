"""Image -> simple educational text via Claude Opus 4.7 vision."""
import base64
import os

try:
    from anthropic import Anthropic
except ImportError:  # pragma: no cover - handled at runtime for demo environments
    Anthropic = None

MODEL = "claude-opus-4-7"

SYSTEM = (
    "You are an assistive reader for a deaf-blind student. "
    "You will be shown a photo of a textbook page, slide, diagram, or scene. "
    "Produce simplified educational text that can later be sent to a braille device. "
    "Rules: plain ASCII only, no markdown, no emoji, no bullet characters. "
    "Use 1-2 short sentences with simple vocabulary when the image contains educational text or a complex diagram. "
    "If the image has little or no readable text and mainly shows an object, person, animal, or scene, return one short sentence in very simple words. "
    "Lead with the most important fact. Keep only the essential idea. "
    "If the image contains printed text, extract its meaning, do not transliterate verbatim. "
    "If the image is a diagram, describe what it shows and the relationship between parts. "
    "Do not guess hidden details. Keep visual-only descriptions brief. Skip extra detail, decoration, and filler."
)

MOCK_RESPONSE = (
    "The image shows one main idea in simple words. "
    "Set MOCK_CLAUDE=false to use real image analysis."
)


def summarize_image(image_bytes: bytes, media_type: str = "image/jpeg") -> str:
    if os.getenv("MOCK_CLAUDE", "true").lower() in ("1", "true", "yes"):
        return MOCK_RESPONSE
    if Anthropic is None:
        raise RuntimeError("anthropic is not installed")

    client = Anthropic()
    b64 = base64.standard_b64encode(image_bytes).decode("ascii")
    with client.messages.stream(
        model=MODEL,
        max_tokens=512,
        system=SYSTEM,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": media_type, "data": b64},
                    },
                    {
                        "type": "text",
                        "text": (
                            "Rewrite this into only the most essential simple text for a braille device. "
                            "Use 1-2 short sentences at most. "
                            "If there are no important words to read in the image, give one short line that simply says what is shown."
                        ),
                    },
                ],
            }
        ],
    ) as stream:
        msg = stream.get_final_message()

    parts = [b.text for b in msg.content if getattr(b, "type", None) == "text"]
    return "".join(parts).strip()
