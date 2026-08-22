from datetime import date

from app.services.extraction.base import ExtractedDocument, LabExtraction


class FakeProvider:
    async def extract(self, image: bytes, mime: str) -> ExtractedDocument:
        return ExtractedDocument(
            document_type="report",
            event_date=None,
            summary="Chest X-ray report",
            content_text="Impression: No acute cardiopulmonary abnormality. Follow-up in 2 weeks.",
        )

    async def extract_labs(self, image: bytes, mime: str) -> LabExtraction:
        return LabExtraction(
            rows=[
                {
                    "test_name": "Hemoglobin",
                    "value": "10.2",
                    "unit": "g/dL",
                    "ref_low": "13.0",
                    "ref_high": "17.0",
                    "taken_at": date(2026, 8, 20),
                },
                {
                    "test_name": "Fasting Glucose",
                    "value": "148",
                    "unit": "mg/dL",
                    "ref_low": "70",
                    "ref_high": "100",
                    "taken_at": date(2026, 8, 20),
                },
                {
                    "test_name": "HbA1c",
                    "value": "7.8",
                    "unit": "%",
                    "ref_low": "4.0",
                    "ref_high": "5.6",
                    "taken_at": date(2026, 8, 20),
                },
                {
                    "test_name": "Total Cholesterol",
                    "value": "180",
                    "unit": "mg/dL",
                    "ref_low": "100",
                    "ref_high": "200",
                    "taken_at": date(2026, 8, 20),
                },
            ]
        )
