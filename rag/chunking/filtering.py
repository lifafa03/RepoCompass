"""File filtering: keep relevant source, config, and doc files."""
from pathlib import Path

from app import config


def classify_file(path: Path) -> str | None:
    """Return content_type ('code', 'config', 'docs') or None if file should be skipped."""
    if path.suffix in config.SKIP_EXTENSIONS:
        return None

    if path.suffix not in config.ALLOWED_EXTENSIONS:
        name_lower = path.name.lower()
        if name_lower in ("dockerfile", "makefile", "rakefile", "gemfile", "procfile"):
            return "config"
        return None

    code_exts = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs", ".rb",
                 ".html", ".css", ".scss", ".sh", ".bash", ".zsh"}
    config_exts = {".yaml", ".yml", ".json", ".toml", ".ini", ".cfg", ".env", ".env.example"}
    doc_exts = {".md", ".rst", ".txt"}

    if path.suffix in code_exts:
        return "code"
    elif path.suffix in config_exts:
        return "config"
    elif path.suffix in doc_exts:
        return "docs"
    return None


def filter_files(files: list[Path]) -> list[tuple[Path, str]]:
    """Filter files and return (path, content_type) pairs."""
    result = []
    for f in files:
        try:
            if f.stat().st_size > 1_000_000:
                continue
        except OSError:
            continue

        ct = classify_file(f)
        if ct is not None:
            result.append((f, ct))
    return result


def detect_language(path: Path) -> str | None:
    """Guess language from file extension."""
    ext_map = {
        ".py": "python", ".js": "javascript", ".ts": "typescript",
        ".jsx": "jsx", ".tsx": "tsx", ".java": "java",
        ".go": "go", ".rs": "rust", ".rb": "ruby",
        ".html": "html", ".css": "css", ".scss": "scss",
        ".sh": "shell", ".bash": "shell", ".zsh": "shell",
    }
    return ext_map.get(path.suffix)
