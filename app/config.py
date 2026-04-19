"""Centralized configuration for RepoCompass."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Project paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(DATA_DIR / "uploads")))
VECTOR_STORE_DIR = Path(os.getenv("VECTOR_STORE_DIR", str(DATA_DIR / "vector_stores")))

# LLM settings
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:8000/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "not-needed")
LLM_MODEL = os.getenv("LLM_MODEL", "mistral-7b-instruct")

# Embedding settings
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# V1 framework target
V1_FRAMEWORK = os.getenv("V1_FRAMEWORK", "fastapi")

# Chunking defaults
CHUNK_MAX_LINES = 80
CHUNK_OVERLAP_LINES = 10
CHUNK_MAX_CHARS = 2000

# File filtering
ALLOWED_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs", ".rb",
    ".yaml", ".yml", ".json", ".toml", ".ini", ".cfg", ".env", ".env.example",
    ".md", ".rst", ".txt",
    ".dockerfile", ".sh", ".bash", ".zsh",
    ".html", ".css", ".scss",
}

SKIP_DIRS = {
    "__pycache__", ".git", ".hg", ".svn", "node_modules", ".tox",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", "venv", ".venv",
    "dist", "build", "egg-info", ".eggs", ".next", ".nuxt",
    "site-packages", ".cache",
}

SKIP_EXTENSIONS = {
    ".pyc", ".pyo", ".so", ".dylib", ".dll", ".exe", ".o", ".a",
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg", ".webp",
    ".mp3", ".mp4", ".avi", ".mov", ".wav", ".flac",
    ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar",
    ".pickle", ".pkl", ".npy", ".npz", ".parquet", ".arrow",
    ".woff", ".woff2", ".ttf", ".eot",
    ".db", ".sqlite", ".sqlite3",
}
