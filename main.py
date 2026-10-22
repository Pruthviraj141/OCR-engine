import asyncio
import logging
import os
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict

import indra_ocr
from fastapi import FastAPI, File, HTTPException, UploadFile, status
from starlette.concurrency import run_in_threadpool

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("indra-ocr-service")

# Configurable max upload size via environment variable (default 25 MB)
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", 25 * 1024 * 1024))
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".tiff", ".tif", ".bmp"}


def process_document(ocr_converter: Any, file_path: str) -> Dict[str, Any]:
    """
    Runs Indra OCR on the document file using the official package convert() API.
    Processes all pages in reading order.
    """
    pages = []
    # indra_ocr.Converter.convert yields (page_number, page_obj)
    for _, page in ocr_converter.convert(file_path):
        if page and page.text:
            pages.append(page.text.strip())

    full_text = "\n\n".join(pages).strip()
    return {
        "pages_processed": len(pages),
        "text": full_text,
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Indra OCR model on CPU (threads=1)...")
    try:
        # Load once during startup, single thread optimized for CPU constrained container
        app.state.ocr = indra_ocr.load(threads=1)
        app.state.ocr_lock = asyncio.Lock()
        logger.info("Indra OCR model loaded successfully.")
    except Exception as exc:
        logger.exception("Failed to initialize Indra OCR model on startup")
        raise exc
    yield


app = FastAPI(
    title="Indra OCR Service",
    description="Minimal self-hosted Indra OCR service running locally on CPU. No API key required.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    return {"message": "Indra OCR Service is running"}


@app.get("/health")
async def health():
    # Return health status for Railway healthchecks
    ocr_ready = hasattr(app.state, "ocr") and app.state.ocr is not None
    if not ocr_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OCR model not loaded",
        )
    return {"status": "ok"}


@app.post("/ocr")
async def ocr_endpoint(file: UploadFile = File(...)):
    filename = file.filename or "unknown"
    extension = Path(filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{extension}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    temp_path = None
    try:
        total_bytes = 0
        with tempfile.NamedTemporaryFile(
            mode="wb",
            delete=False,
            suffix=extension,
        ) as temp:
            temp_path = temp.name
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Maximum upload size is {MAX_UPLOAD_BYTES // (1024 * 1024)} MB",
                    )
                temp.write(chunk)

        if total_bytes == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The uploaded file is empty",
            )

        # Protect server memory by processing one OCR document at a time
        async with app.state.ocr_lock:
            result = await run_in_threadpool(
                process_document,
                app.state.ocr,
                temp_path,
            )

        if not result["text"]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No readable text found in document",
            )

        return {
            "success": True,
            "filename": filename,
            "pages_processed": result["pages_processed"],
            "text": result["text"],
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("OCR document processing failed")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unable to process this document",
        ) from exc
    finally:
        await file.close()
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
