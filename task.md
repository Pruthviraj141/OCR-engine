## 1. Keep it this simple, bro

Railway can automatically detect Python and build your application with Railpack, so you do not need a Dockerfile. We'll use FastAPI, Indra OCR and GitHub Actions.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.railway.com\&sz=32)

Railway Docs

+1



Actual Indra OCR model running on Railway

PDF/image → extracted text

Automatic deployments after GitHub checks pass

No Dockerfile and no external OCR inference API

## 2. Create these files

Make a GitHub repository called `indra-ocr-service`.

```
indra-ocr-service/
├── main.py
├── requirements.txt
├── .python-version
├── tests/
│   └── test_api.py
└── .github/
    └── workflows/
        └── deploy.yml
```

### `requirements.txt`

```
indra-ocr==1.1.2
fastapi>=0.115,<1.0
uvicorn[standard]>=0.30,<1.0
python-multipart>=0.0.9,<1.0
```

Indra's official Python API supports converting PDFs and images and reading each page's extracted text.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+1



### `.python-version`

```
3.11
```

### `main.py`

This is the complete, simplified API. It loads Indra once, limits uploads to 8 MB and processes up to five pages per request to reduce pressure on the free-tier instance.

```
import asyncio    extension = Path(file.filename or "").suffix.lower()    if extension not in ALLOWED_EXTENSIONS:        raise HTTPException(            status_code=415,            detail="Upload a PDF or supported image",        )    temp_path = None    try:        total_bytes = 0        with tempfile.NamedTemporaryFile(            mode="wb",            delete=False,            suffix=extension,        ) as temp:            temp_path = temp.name            while True:                chunk = await file.read(1024 * 1024)                if not chunk:                    break                total_bytes += len(chunk)                if total_bytes > MAX_UPLOAD_BYTES:                    raise HTTPException(                        status_code=413,                        detail="Maximum upload size is 8 MB",                    )                temp.write(chunk)        if total_bytes == 0:            raise HTTPException(                status_code=400,                detail="The uploaded file is empty",            )        async with app.state.ocr_lock:            result = await run_in_threadpool(                extract_text,                app.state.ocr,                temp_path,            )        if not result["text"]:            raise HTTPException(                status_code=422,                detail="No readable text found",            )        return result    except HTTPException:        raise    except Exception as exc:        logger.exception("OCR processing failed")        raise HTTPException(            status_code=422,            detail="Unable to process this document",        ) from exc    finally:        await file.close()        if temp_path and os.path.exists(temp_path):            os.remove(temp_path)
```

This returns only the extracted text and basic processing information. The API-key check is important because your public endpoint could otherwise be used by anyone to consume your CPU credits.

### `tests/test_api.py`

This small test uses a fake OCR converter, so GitHub Actions can test your API without downloading or running the actual model.

```
from types import SimpleNamespacefrom fastapi.testclient import TestClientimport mainclass FakeOCR:    def convert(self, path, max_pages=100):        yield 0, SimpleNamespace(text="Hello from Indra OCR")def test_health_and_text_extraction(monkeypatch):    monkeypatch.setenv("OCR_API_TOKEN", "test-token")    monkeypatch.setattr(        main.indra_ocr,        "load",        lambda **kwargs: FakeOCR(),    )    with TestClient(main.app) as client:        health = client.get("/health")        assert health.status_code == 200        response = client.post(            "/ocr",            headers={"X-API-Key": "test-token"},            files={                "file": (                    "sample.pdf",                    b"test document",                    "application/pdf",                )            },        )        assert response.status_code == 200        assert response.json()["text"] == "Hello from Indra OCR"
```

### `.github/workflows/deploy.yml`

```
name: Test and Deploy OCR

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt pytest httpx

      - name: Check Python syntax
        run: python -m compileall -q main.py tests

      - name: Run tests
        run: pytest -q

  deploy:
    needs: test
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: "22"

      - name: Install Railway CLI
        run: npm install -g @railway/cli

      - name: Deploy to Railway
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
        run: railway up --service indra-ocr --ci
```

Railway documents `railway up --ci` specifically for automated deployment workflows.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+1



## 3. Deploy it

1. Push the files to GitHub. Create the `main` branch and commit the five files shown above.
2. Create your Railway service. Create a project and connect the `indra-ocr-service` GitHub repository. Let Railway detect Python automatically.
3. Set the start command in Railway's service settings to `uvicorn main:app --host 0.0.0.0 --port $PORT`. Set the healthcheck path to `/health`.
4. Add the API secret. In Railway Variables, set `OCR_API_TOKEN` to a long, randomly generated secret. For example, generate one with `python -c "import secrets; print(secrets.token_urlsafe(32))"` and copy its output.
5. Configure CI/CD. Create a Railway project token, then add it in GitHub under Settings → Secrets and variables → Actions as `RAILWAY_TOKEN`. Disable Railway's automatic GitHub deployments so that GitHub Actions is the only deployment path.
6. Push a new commit to `main`. GitHub Actions tests the application first. If the tests fail, it skips deployment. If they pass, it deploys the code to Railway.

## 4. Verify that it works

After deployment, open your Railway-generated domain:

- `/` should return `{"message":"Indra OCR Service is running"}`.
- `/health` should return `{"status":"ok"}`.
- `/docs` lets you test the `/ocr` endpoint interactively. Supply your `X-API-Key` header and upload a PDF or image.

You can also test it from your terminal:

```
curl -X POST \
  -H "X-API-Key: YOUR_OCR_API_TOKEN" \
  -F "file=@sample.pdf" \
  https://YOUR-RAILWAY-DOMAIN/ocr
```

The response will look like this:

```
{
  "text": "The extracted document text appears here.",
  "pages_processed": 1,
  "truncated": false
}
```

## One important warning about the free plan

Railway's current Free plan has a 0.5 GB RAM limit per service, after a 30-day trial with $5 in credits it provides $1 monthly usage credit.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://railway.com\&sz=32)

Railway

+1



Indra itself is small, but Python, ONNX Runtime and PDF processing use additional memory. No setup can guarantee error-free operation without testing the real model on your actual Railway instance. Start with one to five-page documents, check the startup logs and memory metrics, and increase the limits only after successful tests.

That's it, bro: one small Python API, one Railway service, no Dockerfile, no external OCR API, and GitHub Actions handling the tests and deployments.