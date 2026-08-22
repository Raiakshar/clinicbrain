import re

MAX_SUMMARY = 500
MAX_CONTENT = 100_000

NUM_RE = re.compile(r"^-?\d{1,7}(\.\d+)?$")


def validate_extraction(summary: str, content_text: str) -> None:
    if not content_text or not content_text.strip():
        raise ValueError("content_text is empty")
    if len(summary) > MAX_SUMMARY:
        raise ValueError(f"summary exceeds {MAX_SUMMARY} chars")
    if len(content_text) > MAX_CONTENT:
        raise ValueError(f"content_text exceeds {MAX_CONTENT} chars")


def clean_number(raw: object) -> float:
    if isinstance(raw, (int, float)):
        return float(raw)
    text = str(raw or "").strip().replace(",", "")
    if not NUM_RE.match(text):
        raise ValueError(f"not a valid number: {raw!r}")
    return float(text)


def compute_flag(value: float, ref_low: float | None, ref_high: float | None) -> str:
    if ref_high is not None and value > ref_high:
        return "high"
    if ref_low is not None and value < ref_low:
        return "low"
    if ref_low is None and ref_high is None:
        return "review"
    return "normal"
