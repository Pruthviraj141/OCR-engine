from types import SimpleNamespace
from fastapi.testclient import TestClient
import main


class FakeOCR:
    def convert(self, path):
        # Yield 2 pages to verify page counting and text concatenation
        yield 0, SimpleNamespace(text="First page content")
        yield 1, SimpleNamespace(text="Second page content")


def test_public_api_endpoints(monkeypatch):
    monkeypatch.setattr(
        main.indra_ocr,
        "load",
        lambda **kwargs: FakeOCR(),
    )

    with TestClient(main.app) as client:
        # 1. GET /
        root_res = client.get("/")
        assert root_res.status_code == 200
        assert root_res.json() == {"message": "Indra OCR Service is running"}

        # 2. GET /health
        health_res = client.get("/health")
        assert health_res.status_code == 200
        assert health_res.json() == {"status": "ok"}

        # 3. POST /ocr - No authentication required
        response = client.post(
            "/ocr",
            files={
                "file": (
                    "sample.pdf",
                    b"%PDF-1.4 sample content",
                    "application/pdf",
                )
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["filename"] == "sample.pdf"
        assert data["pages_processed"] == 2
        assert "First page content\n\nSecond page content" in data["text"]


def test_ocr_validation_errors(monkeypatch):
    monkeypatch.setattr(
        main.indra_ocr,
        "load",
        lambda **kwargs: FakeOCR(),
    )

    with TestClient(main.app) as client:
        # Unsupported file extension
        bad_ext = client.post(
            "/ocr",
            files={"file": ("test.exe", b"malicious binary", "application/octet-stream")},
        )
        assert bad_ext.status_code == 415

        # Empty file upload
        empty = client.post(
            "/ocr",
            files={"file": ("empty.pdf", b"", "application/pdf")},
        )
        assert empty.status_code == 400
