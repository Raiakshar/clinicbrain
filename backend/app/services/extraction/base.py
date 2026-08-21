from abc import ABC, abstractmethod
from datetime import date
from typing import Literal

from pydantic import BaseModel


class ExtractedDocument(BaseModel):
    document_type: Literal["visit", "prescription", "lab", "letter", "report"]
    event_date: date | None = None
    summary: str = ""
    content_text: str = ""


class ExtractionError(Exception):
    pass


class BaseExtractionProvider(ABC):
    @abstractmethod
    async def extract(self, image: bytes, mime: str) -> ExtractedDocument: ...
