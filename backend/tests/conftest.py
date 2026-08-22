import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings
from app.db import get_db
from app.main import app
from app.models import Base
from app.services.storage import get_storage
from app.workers import tasks as worker_tasks

TEST_DB_URL = "postgresql+asyncpg://clinicbrain:clinicbrain@localhost:5433/clinicbrain_test"
ADMIN_URL = "postgresql+asyncpg://clinicbrain:clinicbrain@localhost:5433/clinicbrain"

SEARCH_DDL = [
    """
    ALTER TABLE documents ADD COLUMN IF NOT EXISTS search_vector tsvector
    GENERATED ALWAYS AS (to_tsvector('english', coalesce(ocr_text, ''))) STORED
    """,
    "CREATE INDEX IF NOT EXISTS idx_documents_search ON documents USING GIN (search_vector)",
    """
    ALTER TABLE timeline_events ADD COLUMN IF NOT EXISTS search_vector tsvector
    GENERATED ALWAYS AS (
        to_tsvector('english',
            coalesce(payload->>'summary', '') || ' ' ||
            coalesce(payload->>'content_text', '') || ' ' ||
            coalesce(payload->>'text', '')
        )
    ) STORED
    """,
    "CREATE INDEX IF NOT EXISTS idx_events_search ON timeline_events USING GIN (search_vector)",
]


class FakeStorage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put(self, key: str, data: bytes, mime: str) -> None:
        self.objects[key] = data

    def get(self, key: str) -> bytes:
        return self.objects[key]

    def delete(self, key: str) -> None:
        self.objects.pop(key, None)


@pytest.fixture
async def db_session():
    admin = create_async_engine(ADMIN_URL, isolation_level="AUTOCOMMIT", poolclass=NullPool)
    async with admin.connect() as conn:
        exists = await conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = 'clinicbrain_test'")
        )
        if not exists.scalar():
            await conn.execute(text("CREATE DATABASE clinicbrain_test"))
    await admin.dispose()

    engine = create_async_engine(TEST_DB_URL, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        for ddl in SEARCH_DDL:
            await conn.execute(text(ddl))

    maker = async_sessionmaker(engine, expire_on_commit=False)
    yield maker
    await engine.dispose()


@pytest.fixture
def fake_storage():
    return FakeStorage()


class StubTask:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def delay(self, document_id: str) -> None:
        self.calls.append(document_id)


@pytest.fixture
def stub_task(monkeypatch):
    stub = StubTask()
    monkeypatch.setattr(worker_tasks, "extract_document_task", stub)
    monkeypatch.setattr(worker_tasks, "extract_labs_task", stub)
    return stub


@pytest.fixture
def client(db_session, fake_storage, monkeypatch) -> httpx.AsyncClient:
    from app.workers import tasks as worker_tasks

    async def override_get_db():
        async with db_session() as session:
            yield session

    class FakeEngine:
        async def dispose(self):
            return None

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_storage] = lambda: fake_storage
    monkeypatch.setattr(worker_tasks, "get_session_maker", lambda: (db_session, FakeEngine()))
    monkeypatch.setattr(worker_tasks, "get_storage", lambda: fake_storage)
    monkeypatch.setattr(settings, "extraction_provider", "fake")
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture
async def auth_headers(client: httpx.AsyncClient) -> dict[str, str]:
    resp = await client.post(
        "/api/auth/signup",
        json={
            "clinic_name": "Test Clinic",
            "name": "Dr Test",
            "phone": "9999999999",
            "password": "secret123",
        },
    )
    token = resp.json()["token"]
    return {"Authorization": f"Bearer {token}"}
