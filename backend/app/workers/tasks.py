import asyncio

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Document
from app.services.storage import get_storage
from app.workers.celery_app import celery_app


async def _extract(document_id: int) -> None:
    from app.config import settings

    async with SessionLocal() as db:
        doc = (
            await db.scalars(select(Document).where(Document.id == document_id))
        ).first()
        if not doc or doc.status != "pending":
            return
        doc.status = "processing"
        await db.commit()
        try:
            data = get_storage().get(doc.s3_key)
            if settings.extraction_provider == "fake":
                from app.services.extraction.fake import FakeProvider

                provider = FakeProvider()
            else:
                from app.services.extraction.gpt import GPTProvider

                provider = GPTProvider()
            result = await provider.extract(data, doc.mime)
            doc.ocr_text = result.content_text
            doc.extracted = result.model_dump(mode="json")
            doc.status = "needs_review"
            doc.error = None
        except Exception as e:
            doc.status = "failed"
            doc.error = str(e)[:800]
        await db.commit()


@celery_app.task(name="documents.extract")
def extract_document_task(document_id: str) -> None:
    asyncio.run(_extract(int(document_id)))
