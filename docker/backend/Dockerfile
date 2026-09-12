FROM python:3.12-slim

WORKDIR /app

COPY . .

RUN pip install \
    --no-cache-dir \
    -r backend/requirements.txt

RUN adduser \
    --disabled-password \
    appuser

USER appuser

CMD [
    "uvicorn",
    "backend.main:app",
    "--host",
    "0.0.0.0",
    "--port",
    "8000"
]
