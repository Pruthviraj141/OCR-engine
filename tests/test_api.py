from types import SimpleNamespace
from fastapi.testclient import TestClient
import main


class FakeOCR:
    def convert(self, path, max_pages=100):
        yield 0, SimpleNamespace(text="Hello from Indra OCR")


def test_health_and_text_extraction(monkeypatch):
    monkeypatch.setenv("OCR_API_TOKEN", "test-token")
    monkeypatch.setattr(
        main.indra_ocr,
        "load",
        lambda **kwargs: FakeOCR(),
    )

    with TestClient(main.app) as client:
        # Test root endpoint
        root = client.get("/")
        assert root.status_code == 200
        assert root.json() == {"message": "Indra OCR Service is running"}

        # Test health endpoint
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json() == {"status": "ok"}

        # Test OCR endpoint unauthorized
        unauth = client.post(
            "/ocr",
            files={"file": ("sample.pdf", b"test content", "application/pdf")},
        )
        assert unauth.status_code == 401

        # Test OCR endpoint with valid key
        response = client.post(
            "/ocr",
            headers={"X-API-Key": "test-token"},
            files={
                "file": (
                    "sample.pdf",
                    b"test document",
                    "application/pdf",
                )
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["text"] == "Hello from Indra OCR"
        assert data["pages_processed"] == 1
        assert data["truncated"] is False
