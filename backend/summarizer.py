"""Lecture transcript -> simplified educational text via Claude Opus 4.7."""
import os

try:
    from anthropic import Anthropic
except ImportError:  # pragma: no cover - handled at runtime for demo environments
    Anthropic = None

MODEL = "claude-opus-4-7"

SYSTEM = (
    "You are an assistive note-taker for a deaf-blind student using a braille display. "
    "You will be given a raw lecture transcript. "
    "Produce only the essential educational takeaway in 1-2 very short sentences. "
    "Rules: plain ASCII only, no markdown, no bullet characters, no emoji. "
    "Use simple vocabulary. Keep only the main point, key definition, or conclusion. "
    "Skip examples, side comments, repetition, names, and filler."
)

MOCK_RESPONSE = (
    "The lecture explains the main idea in simple words. "
    "Set MOCK_CLAUDE=false to use real summarization."
)


def summarize_transcript(transcript: str) -> str:
    if os.getenv("MOCK_CLAUDE", "true").lower() in ("1", "true", "yes"):
        return MOCK_RESPONSE
    if Anthropic is None:
        raise RuntimeError("anthropic is not installed")

    client = Anthropic()
    with client.messages.stream(
        model=MODEL,
        max_tokens=512,
        system=SYSTEM,
        messages=[
            {
                "role": "user",
                "content": (
                    "Rewrite this lecture into only the most essential simple text for a braille device. "
                    "Use 1-2 short sentences and keep only the main takeaway.\n\n"
                    f"{transcript}"
                ),
            }
        ],
    ) as stream:
        msg = stream.get_final_message()

    parts = [b.text for b in msg.content if getattr(b, "type", None) == "text"]
    return "".join(parts).strip()
