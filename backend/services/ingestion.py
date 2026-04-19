"""Repository ingestion: accept ZIP upload or local path, extract and enumerate files."""
import hashlib
import shutil
import tempfile
import zipfile
from pathlib import Path

from app import config
from app.schemas import ChunkRecord


def ingest_zip(zip_path: Path, repo_id: str | None = None) -> Path:
    """Extract a ZIP file to the upload directory. Returns the extracted repo root."""
    if repo_id is None:
        repo_id = hashlib.md5(zip_path.read_bytes()).hexdigest()[:12]

    dest = config.UPLOAD_DIR / repo_id
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(dest)

    # If ZIP contains a single top-level directory, unwrap it
    children = list(dest.iterdir())
    if len(children) == 1 and children[0].is_dir():
        unwrapped = children[0]
        # Move contents up
        tmp = dest.with_name(dest.name + "__tmp")
        unwrapped.rename(tmp)
        shutil.rmtree(dest)
        tmp.rename(dest)

    return dest


def ingest_local(local_path: Path, repo_id: str | None = None) -> Path:
    """Copy a local directory into the upload area. Returns the copied repo root."""
    local_path = local_path.resolve()
    if not local_path.exists():
        raise FileNotFoundError(f"Path does not exist: {local_path}")

    if repo_id is None:
        repo_id = local_path.name + "_" + hashlib.md5(str(local_path).encode()).hexdigest()[:8]

    dest = config.UPLOAD_DIR / repo_id
    if dest.exists():
        shutil.rmtree(dest)

    if local_path.is_file() and local_path.suffix == ".zip":
        return ingest_zip(local_path, repo_id)

    shutil.copytree(local_path, dest)
    return dest


def enumerate_files(repo_root: Path) -> list[Path]:
    """List all files in the repo, respecting skip directories."""
    files = []
    for path in repo_root.rglob("*"):
        if not path.is_file():
            continue
        # Skip if any part of the path is in SKIP_DIRS
        parts = path.relative_to(repo_root).parts
        if any(p in config.SKIP_DIRS for p in parts):
            continue
        files.append(path)
    return files
