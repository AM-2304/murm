FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY README.md .
COPY murm/ murm/

RUN pip install --no-cache-dir -e . \
    && python -c "from chromadb import PersistentClient"

EXPOSE 8000

CMD ["uvicorn", "murm.main:app", "--host", "0.0.0.0", "--port", "8000"]
