import base64
import json

from openai import AsyncOpenAI
from pydantic import ValidationError

from app.config import settings
from app.services.extraction.base import (
    BaseExtractionProvider,
    ExtractedDocument,
    ExtractionError,
    LabExtraction,
)

SYSTEM_PROMPT = (
    "You extract text from photos of medical documents (prescriptions, lab reports, letters). "
    "Respond with ONLY a JSON object with keys: "
    '"document_type" (one of visit|prescription|lab|letter|report), '
    '"event_date" (YYYY-MM-DD or null, the document date), '
    '"summary" (one line summary, max 200 chars), '
    '"content_text" (full extracted text, preserve numbers exactly).'
)

LAB_SYSTEM_PROMPT = (
    "You read photos of medical lab reports. Respond with ONLY a JSON object: "
    '{"rows": [{"test_name": str, "value": str|number|null, "unit": str|null, '
    '"ref_low": str|number|null, "ref_high": str|number|null, "taken_at": "YYYY-MM-DD"|null}]} '
    "Include every test on the report. Copy numbers EXACTLY as printed (keep commas if present). "
    "Use null for anything not printed. Never invent values."
)


class GPTProvider(BaseExtractionProvider):
    def __init__(self) -> None:
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def _vision_json(self, system: str, image: bytes, mime: str) -> dict:
        try:
            data_uri = f"data:{mime};base64,{base64.b64encode(image).decode()}"
            resp = await self.client.chat.completions.create(
                model=settings.openai_model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Extract this medical document."},
                            {"type": "image_url", "image_url": {"url": data_uri}},
                        ],
                    },
                ],
            )
            return json.loads(resp.choices[0].message.content or "{}")
        except Exception as e:
            raise ExtractionError(str(e)) from e

    async def extract(self, image: bytes, mime: str) -> ExtractedDocument:
        raw = await self._vision_json(SYSTEM_PROMPT, image, mime)
        try:
            return ExtractedDocument.model_validate(raw)
        except (ValidationError, KeyError) as e:
            raise ExtractionError(str(e)) from e

    async def extract_labs(self, image: bytes, mime: str) -> LabExtraction:
        raw = await self._vision_json(LAB_SYSTEM_PROMPT, image, mime)
        try:
            return LabExtraction.model_validate(raw)
        except (ValidationError, KeyError) as e:
            raise ExtractionError(str(e)) from e


def get_provider():
    if settings.extraction_provider == "fake":
        from app.services.extraction.fake import FakeProvider

        return FakeProvider()
    return GPTProvider()
