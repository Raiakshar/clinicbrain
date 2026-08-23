from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, documents, labs, patients, prescriptions, queue, search, timeline

app = FastAPI(title="ClinicBrain API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

for module in (auth, patients, timeline, documents, labs, prescriptions, queue, search):
    app.include_router(module.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
