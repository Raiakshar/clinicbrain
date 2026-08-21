from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db import get_db
from app.models import User
from app.schemas import SearchItem

router = APIRouter(prefix="/api", tags=["search"])

DOC_SQL = text(
    """
    SELECT d.id, d.patient_id,
           ts_rank(d.search_vector, websearch_to_tsquery('english', :q)) AS rank,
           coalesce(d.extracted->>'summary', left(coalesce(d.ocr_text, ''), 80)) AS title
    FROM documents d
    JOIN patients p ON p.id = d.patient_id
    WHERE p.clinic_id = :clinic_id AND d.search_vector @@ websearch_to_tsquery('english', :q)
    """
)

EVENT_SQL = text(
    """
    SELECT e.id, e.patient_id,
           ts_rank(e.search_vector, websearch_to_tsquery('english', :q)) AS rank,
           coalesce(e.payload->>'summary', e.payload->>'text', left(e.payload::text, 80)) AS title
    FROM timeline_events e
    JOIN patients p ON p.id = e.patient_id
    WHERE p.clinic_id = :clinic_id AND e.search_vector @@ websearch_to_tsquery('english', :q)
    """
)


@router.get("/search", response_model=list[SearchItem])
async def search(
    q: str = Query(min_length=1),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    docs = (await db.execute(DOC_SQL, {"q": q, "clinic_id": user.clinic_id})).all()
    events = (await db.execute(EVENT_SQL, {"q": q, "clinic_id": user.clinic_id})).all()
    items = [({"source": "document"} | dict(r._mapping)) for r in docs] + [
        ({"source": "event"} | dict(r._mapping)) for r in events
    ]
    items.sort(key=lambda x: x["rank"], reverse=True)
    return [
        SearchItem(source=i["source"], id=i["id"], patient_id=i["patient_id"], title=str(i["title"]))
        for i in items[:20]
    ]
