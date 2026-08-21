from app.services.extraction.base import ExtractedDocument


class FakeProvider:
    async def extract(self, image: bytes, mime: str) -> ExtractedDocument:
        return ExtractedDocument(
            document_type="report",
            event_date=None,
            summary="Chest X-ray report",
            content_text="Impression: No acute cardiopulmonary abnormality. Follow-up in 2 weeks.",
        )
