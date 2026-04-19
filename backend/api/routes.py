"""FastAPI routes for repository ingestion and analysis."""
import tempfile
import hashlib
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException

from backend.pipelines.analysis import RepoCompassPipeline

router = APIRouter()
_pipeline = RepoCompassPipeline()


@router.post("/upload")
async def upload_and_analyze(file: UploadFile = File(...)):
    """Upload a ZIP file and run full analysis."""
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only ZIP files are accepted.")

    content = await file.read()
    repo_id = hashlib.md5(content).hexdigest()[:12]

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    tmp.write(content)
    tmp.close()

    result = _pipeline.run(Path(tmp.name), repo_id)
    return result


@router.post("/analyze-path")
async def analyze_path(path: str):
    """Analyze a local repository path."""
    p = Path(path)
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"Path not found: {path}")

    result = _pipeline.run(p)
    return result


@router.post("/ask")
async def ask_repo(repo_id: str, question: str):
    """Ask a question about an indexed repository."""
    answer = _pipeline.ask_repo(repo_id, question)
    return answer
