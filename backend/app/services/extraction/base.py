from abc import ABC, abstractmethod
from datetime import date
from typing import Literal

from pydantic import BaseModel


class ExtractedDocument(BaseModel):
    document_type: Literal["visit", "prescription", "lab", "letter", "report"]
    event_date: date | None = None
    summary: str = ""
    content_text: str = ""


class LabRow(BaseModel):
    test_name: str
    value: str | float | None = None
    unit: str | None = None
    ref_low: str | float | None = None
    ref_high: str | float | None = None
    taken_at: date | None = None


class LabExtraction(BaseModel):
    rows: list[LabRow]


class ExtractionError(Exception):
    pass


class BaseExtractionProvider(ABC):
    @abstractmethod
    async def extract(self, image: bytes, mime: str) -> ExtractedDocument: ...

    @abstractmethod
    async def extract_labs(self, image: bytes, mime: str) -> LabExtraction: ...
