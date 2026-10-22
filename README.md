# OCR-engine

The simplest reliable, self-hosted Indra OCR service built with **FastAPI** and the official **`indra-ocr`** package, designed for Railway native Python deployment.

## Features

- **Direct Model Execution**: Runs the official `indra-ocr` model locally on the server CPU (no external OCR inference API, no GPU needed).
- **Public API (Zero Authentication)**: No API keys, no bearer tokens, no authorization headers, and no user accounts.
- **Full Document Support**: Extracts text from PDFs (multi-page) and common image formats (`.png`, `.jpg`, `.jpeg`, `.webp`, `.tiff`, `.bmp`).
- **Resource Guardrails**:
  - Model loaded once at startup.
  - Concurrency lock to process requests sequentially on CPU instances without exhausting RAM.
  - Configurable upload limit (`MAX_UPLOAD_BYTES`, defaults to 25 MB).
  - Safe tempfile lifecycle cleanup on success or error.

---

## API Endpoints

### 1. `GET /`
Returns a confirmation that the service is running.
```json
{
  "message": "Indra OCR Service is running"
}
```

### 2. `GET /health`
Health check endpoint for Railway.
```json
{
  "status": "ok"
}
```

### 3. `POST /ocr`
Accepts a PDF or image file as multipart form data with field name `file`.

**Request:**
```bash
curl -X POST "https://YOUR-RAILWAY-DOMAIN/ocr" \
  -F "file=@sample.pdf"
```

**Response Format:**
```json
{
  "success": true,
  "filename": "sample.pdf",
  "pages_processed": 2,
  "text": "All extracted text in reading order..."
}
```

Interactive Swagger documentation is available at `/docs`.

---

## Local Development & Testing

### 1. Virtual Environment Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt pytest httpx
```

### 2. Run Tests
```bash
pytest -v
```

### 3. Start Local Server
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Railway Deployment Settings

1. **Connect GitHub Repository**: Link `OCR-engine` directly to your Railway project. Railway will automatically build via Railpack and trigger deployments on push to `main`.
2. **Start Command**:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port $PORT
   ```
3. **Healthcheck Path**:
   ```
   /health
   ```
4. **Environment Variables**:
   - No required secrets or tokens.
   - Optional: `MAX_UPLOAD_BYTES` (e.g. `26214400` for 25 MB).
