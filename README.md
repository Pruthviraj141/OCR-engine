# OCR-engine

High-performance OCR microservice powered by **Indra OCR** and **FastAPI**, designed for zero-config deployment on Railway with GitHub Actions CI/CD.

## Features

- **Indra OCR Integration**: Runs ONNX-accelerated OCR model directly inside the service.
- **FastAPI Endpoints**:
  - `GET /`: Health check / welcome message.
  - `GET /health`: Healthcheck endpoint for Railway / load balancers.
  - `POST /ocr`: Extracts text from PDF or image documents (`multipart/form-data`).
- **Security**: Protects endpoints with `X-API-Key` header authentication (`OCR_API_TOKEN`).
- **Memory & Resource Guardrails**:
  - Maximum upload size: 8 MB.
  - Maximum pages processed per request: 5 pages.
  - Threadpool execution with concurrency lock to avoid memory exhaustion on resource-constrained instances.
- **Automated CI/CD**: Tests via pytest and deploys to Railway on push to `main`.

---

## Local Development & Setup

### 1. Create and Activate Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt pytest httpx
```

### 3. Run Tests

```bash
pytest -v
```

### 4. Start Local Server

```bash
export OCR_API_TOKEN="your-local-secret"
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Test OCR Endpoint

```bash
curl -X POST "http://localhost:8000/ocr" \
  -H "X-API-Key: your-local-secret" \
  -F "file=@sample.pdf"
```

---

## Deployment (Railway + GitHub Actions)

1. **Connect GitHub Repo to Railway**:
   - Create a project on Railway and link the repository.
   - Railway Railpack automatically detects Python via `.python-version` and `requirements.txt`.
2. **Environment Variables**:
   - Set `OCR_API_TOKEN` in Railway environment variables.
3. **Railway Service Settings**:
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - Healthcheck Path: `/health`
4. **CI/CD Configuration**:
   - Generate a Railway Project Token.
   - In GitHub repository settings: `Settings -> Secrets and variables -> Actions`, add `RAILWAY_TOKEN`.
   - On every push to `main`, GitHub Actions runs tests and triggers automated deployment.
