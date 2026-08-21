MAX_SUMMARY = 500
MAX_CONTENT = 100_000


def validate_extraction(summary: str, content_text: str) -> None:
    if not content_text or not content_text.strip():
        raise ValueError("content_text is empty")
    if len(summary) > MAX_SUMMARY:
        raise ValueError(f"summary exceeds {MAX_SUMMARY} chars")
    if len(content_text) > MAX_CONTENT:
        raise ValueError(f"content_text exceeds {MAX_CONTENT} chars")
