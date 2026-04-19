"""Tests for the chunking pipeline."""
import tempfile
from pathlib import Path
import pytest

from rag.chunking.filtering import classify_file, filter_files, detect_language
from rag.chunking.chunker import chunk_file, chunk_repo
from app.schemas import ChunkRecord


class TestFileFiltering:
    def test_classify_python(self):
        assert classify_file(Path("app.py")) == "code"
    def test_classify_yaml(self):
        assert classify_file(Path("config.yaml")) == "config"
    def test_classify_markdown(self):
        assert classify_file(Path("README.md")) == "docs"
    def test_classify_binary_skipped(self):
        assert classify_file(Path("image.png")) is None
    def test_classify_pyc_skipped(self):
        assert classify_file(Path("__pycache__.pyc")) is None
    def test_classify_dockerfile(self):
        assert classify_file(Path("Dockerfile")) == "config"
    def test_detect_language_python(self):
        assert detect_language(Path("app.py")) == "python"
    def test_detect_language_js(self):
        assert detect_language(Path("index.js")) == "javascript"
    def test_detect_language_unknown(self):
        assert detect_language(Path("config.yaml")) is None


class TestChunking:
    def _make_file(self, content: str, name: str = "test.py") -> Path:
        tmp = tempfile.mkdtemp()
        fp = Path(tmp) / name
        fp.write_text(content)
        return fp
    def test_chunk_python_file(self):
        content = 'def hello():\n    return "hello"\n\ndef world():\n    return "world"\n\nclass MyApp:\n    def run(self):\n        pass\n'
        fp = self._make_file(content)
        chunks = chunk_file(fp, fp.parent, "code")
        assert len(chunks) >= 2
        assert chunks[0].symbol is not None
    def test_chunk_empty_file(self):
        fp = self._make_file("", "empty.py")
        assert chunk_file(fp, fp.parent, "code") == []
    def test_chunk_markdown_file(self):
        content = "# Title\n\nSome text\n" * 20
        fp = self._make_file(content, "README.md")
        chunks = chunk_file(fp, fp.parent, "docs")
        assert len(chunks) >= 1
        assert chunks[0].content_type == "docs"
    def test_chunk_metadata(self):
        content = "def foo():\n    pass\n"
        fp = self._make_file(content)
        chunks = chunk_file(fp, fp.parent, "code")
        c = chunks[0]
        assert c.chunk_id
        assert c.language == "python"
