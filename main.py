import asyncio
import logging
import os
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict

import indra_ocr
from fastapi import FastAPI, File, Header, HTTPException, UploadFile, status
from starlette.concurrency import run_in_threadpool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ocr-service")

MAX_UPLOAD_BYTES = 8 * 1024 * 1024  # 8 MB
MAX_PAGES = 5
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".tiff", ".bmp"}


def extract_text(ocr_converter: Any, file_path: str, max_pages: int = MAX_PAGES) -> Dict[str, Any]:
    pages = []
    truncated = False
    for page_num, page in ocr_converter.convert(file_path, max_pages=max_pages):
        pages.append(page.text)
        if page_num >= max_pages - 1:
            truncated = True
            break
    return {
        "text": "\n\n".join(pages).strip(),
        "pages_processed": len(pages),
        "truncated": truncated,
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Indra OCR model...")
    app.state.ocr = indra_ocr.load()
    app.state.ocr_lock = asyncio.Lock()
    logger.info("Indra OCR model loaded successfully.")
    yield


app = FastAPI(
    title="Indra OCR Service",
    description="High-performance document OCR API powered by Indra OCR",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    return {"message": "Indra OCR Service is running"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/ocr")
async def ocr_endpoint(
    file: UploadFile = File(...),
    x_api_key: str | None = Header(None, alias="X-API-Key"),
):
    expected_token = os.getenv("OCR_API_TOKEN")
    if expected_token and x_api_key != expected_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )

    extension = Path(file.filename or "").suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Upload a PDF or supported image",
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
                        detail="Maximum upload size is 8 MB",
                    )
                temp.write(chunk)

        if total_bytes == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The uploaded file is empty",
            )

        async with app.state.ocr_lock:
            result = await run_in_threadpool(
                extract_text,
                app.state.ocr,
                temp_path,
            )

        if not result["text"]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No readable text found",
            )

        return result

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("OCR processing failed")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unable to process this document",
        ) from exc
    finally:
        await file.close()
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
