"""RepoCompass FastAPI backend."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import router as analysis_router

app = FastAPI(
    title="RepoCompass",
    version="0.1.0",
    description="Multi-Agent RAG Web App for Codebase Architecture Explainers and API Mapping",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analysis_router, prefix="/api", tags=["analysis"])


@app.get("/health")
async def health():
    return {"status": "ok"}
