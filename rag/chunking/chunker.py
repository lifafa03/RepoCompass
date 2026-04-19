"""Code-aware chunking: split files into retrievable chunks with metadata."""
import hashlib
import re
from pathlib import Path

from app import config
from app.schemas import ChunkRecord
from rag.chunking.filtering import detect_language


def _make_chunk_id(repo_root: Path, file_path: Path, line_start: int, line_end: int) -> str:
    key = f"{file_path.relative_to(repo_root)}:{line_start}:{line_end}"
    return hashlib.md5(key.encode()).hexdigest()[:16]


def _extract_python_symbols(content: str) -> list[tuple[str, int, int]]:
    """Extract top-level function/class names and their line ranges."""
    symbols = []
    lines = content.split("\n")
    current_name = None
    current_start = None

    for i, line in enumerate(lines):
        stripped = line.strip()
        # Top-level def or class
        if re.match(r"^(class |def |async def )", stripped) and not line.startswith(" ") and not line.startswith("\t"):
            if current_name is not None:
                symbols.append((current_name, current_start, i))
            current_name = stripped.split("(")[0].split(":")[0].strip()
            current_start = i + 1  # 1-indexed

    if current_name is not None:
        symbols.append((current_name, current_start, len(lines)))

    return symbols


def _chunk_by_symbols(content: str, file_path: Path, repo_root: Path,
                       content_type: str, language: str | None) -> list[ChunkRecord]:
    """Chunk Python files by top-level symbols when possible."""
    symbols = _extract_python_symbols(content) if language == "python" else []
    if not symbols:
        return _chunk_by_lines(content, file_path, repo_root, content_type, language)

    chunks = []
    for name, start, end in symbols:
        lines = content.split("\n")
        symbol_lines = lines[start - 1:end]
        if len(symbol_lines) <= config.CHUNK_MAX_LINES:
            chunk_content = "\n".join(symbol_lines)
            chunks.append(ChunkRecord(
                chunk_id=_make_chunk_id(repo_root, file_path, start, end),
                file_path=str(file_path),
                language=language,
                symbol=name,
                line_start=start,
                line_end=end,
                content=chunk_content,
                content_type=content_type,
                repo_relative_path=str(file_path.relative_to(repo_root)),
            ))
        else:
            sub_chunks = _sub_chunk(symbol_lines, start, file_path, repo_root, content_type, language, name)
            chunks.extend(sub_chunks)

    return chunks


def _sub_chunk(lines: list[str], base_line: int, file_path: Path,
               repo_root: Path, content_type: str, language: str | None,
               symbol: str | None = None) -> list[ChunkRecord]:
    """Split lines into overlapping chunks."""
    chunks = []
    max_lines = config.CHUNK_MAX_LINES
    overlap = config.CHUNK_OVERLAP_LINES
    i = 0
    while i < len(lines):
        end = min(i + max_lines, len(lines))
        chunk_lines = lines[i:end]
        line_start = base_line + i
        line_end = base_line + end
        chunk_content = "\n".join(chunk_lines)

        if len(chunk_content) > config.CHUNK_MAX_CHARS:
            chunk_content = chunk_content[:config.CHUNK_MAX_CHARS]

        chunks.append(ChunkRecord(
            chunk_id=_make_chunk_id(repo_root, file_path, line_start, line_end),
            file_path=str(file_path),
            language=language,
            symbol=symbol,
            line_start=line_start,
            line_end=line_end,
            content=chunk_content,
            content_type=content_type,
            repo_relative_path=str(file_path.relative_to(repo_root)),
        ))
        if end >= len(lines):
            break
        i += max_lines - overlap
    return chunks


def _chunk_by_lines(content: str, file_path: Path, repo_root: Path,
                    content_type: str, language: str | None) -> list[ChunkRecord]:
    """Generic line-based chunking with overlap."""
    lines = content.split("\n")
    return _sub_chunk(lines, 1, file_path, repo_root, content_type, language)


def chunk_file(file_path: Path, repo_root: Path, content_type: str) -> list[ChunkRecord]:
    """Chunk a single file into ChunkRecords."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []

    if not content.strip():
        return []

    language = detect_language(file_path)

    if language == "python" and content_type == "code":
        return _chunk_by_symbols(content, file_path, repo_root, content_type, language)

    return _chunk_by_lines(content, file_path, repo_root, content_type, language)


def chunk_repo(repo_root: Path, filtered_files: list[tuple[Path, str]]) -> list[ChunkRecord]:
    """Chunk all filtered files in a repository."""
    all_chunks = []
    for file_path, content_type in filtered_files:
        chunks = chunk_file(file_path, repo_root, content_type)
        all_chunks.extend(chunks)
    return all_chunks
