import base64
import json

from openai import AsyncOpenAI
from pydantic import ValidationError

from app.config import settings
from app.services.extraction.base import (
    BaseExtractionProvider,
    ExtractedDocument,
    ExtractionError,
)

SYSTEM_PROMPT = (
    "You extract text from photos of medical documents (prescriptions, lab reports, letters). "
    "Respond with ONLY a JSON object with keys: "
    '"document_type" (one of visit|prescription|lab|letter|report), '
    '"event_date" (YYYY-MM-DD or null, the document date), '
    '"summary" (one line summary, max 200 chars), '
    '"content_text" (full extracted text, preserve numbers exactly).'
)


class GPTProvider(BaseExtractionProvider):
    def __init__(self) -> None:
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def extract(self, image: bytes, mime: str) -> ExtractedDocument:
        try:
            data_uri = f"data:{mime};base64,{base64.b64encode(image).decode()}"
            resp = await self.client.chat.completions.create(
                model=settings.openai_model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Extract this medical document."},
                            {"type": "image_url", "image_url": {"url": data_uri}},
                        ],
                    },
                ],
            )
            raw = json.loads(resp.choices[0].message.content or "{}")
            return ExtractedDocument.model_validate(raw)
        except ExtractionError:
            raise
        except (json.JSONDecodeError, ValidationError, KeyError, Exception) as e:
            raise ExtractionError(str(e)) from e


def get_provider():
    if settings.extraction_provider == "fake":
        from app.services.extraction.fake import FakeProvider

        return FakeProvider()
    return GPTProvider()
