"""Tests for the FastAPI route extractor."""
import tempfile
from pathlib import Path
import pytest

from extractors.api.fastapi_extractor import extract_fastapi_routes, extract_api_map


SAMPLE_FASTAPI_APP = '\nfrom fastapi import FastAPI\n\napp = FastAPI()\n\n@app.get("/users")\nasync def list_users():\n    return []\n\n@app.post("/users")\nasync def create_user():\n    return {"id": 1}\n\n@app.get("/users/{user_id}")\nasync def get_user(user_id: int):\n    return {"id": user_id}\n\n@app.delete("/users/{user_id}")\nasync def delete_user(user_id: int):\n    return {"deleted": True}\n'

SAMPLE_WITH_ADD_API_ROUTE = '\nfrom fastapi import FastAPI\n\napp = FastAPI()\n\ndef health():\n    return {"status": "ok"}\n\napp.add_api_route("/health", health, methods=["GET"])\n'


class TestFastAPIExtractor:
    def _make_file(self, content: str) -> tuple[Path, Path]:
        tmp = Path(tempfile.mkdtemp())
        fp = tmp / "app.py"
        fp.write_text(content)
        return fp, tmp
    def test_extract_decorator_routes(self):
        fp, root = self._make_file(SAMPLE_FASTAPI_APP)
        endpoints = extract_fastapi_routes(fp, root)
        assert len(endpoints) == 4
        methods = {e.method for e in endpoints}
        assert "GET" in methods and "POST" in methods
    def test_extract_add_api_route(self):
        fp, root = self._make_file(SAMPLE_WITH_ADD_API_ROUTE)
        endpoints = extract_fastapi_routes(fp, root)
        assert len(endpoints) == 1
        assert endpoints[0].route == "/health"
    def test_handler_location_present(self):
        fp, root = self._make_file(SAMPLE_FASTAPI_APP)
        endpoints = extract_fastapi_routes(fp, root)
        for ep in endpoints:
            if ep.confidence == "high":
                assert ep.handler_location is not None
    def test_evidence_references(self):
        fp, root = self._make_file(SAMPLE_FASTAPI_APP)
        endpoints = extract_fastapi_routes(fp, root)
        for ep in endpoints:
            assert len(ep.evidence) > 0
    def test_empty_file(self):
        fp, root = self._make_file("")
        assert extract_fastapi_routes(fp, root) == []
    def test_non_fastapi_file(self):
        fp, root = self._make_file("x = 1\nprint(x)\n")
        assert extract_fastapi_routes(fp, root) == []
    def test_extract_api_map(self):
        fp, root = self._make_file(SAMPLE_FASTAPI_APP)
        api_map = extract_api_map(root, [fp])
        assert api_map.framework == "fastapi" and len(api_map.endpoints) == 4
