FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg curl \
  && rm -rf /var/lib/apt/lists/* \
  && pip install uv

WORKDIR /app
COPY pyproject.toml ./
RUN uv sync --no-dev

COPY app ./app
COPY migrations ./migrations

ENV STORAGE_DIR=/storage DATABASE_URL=sqlite:////storage/reframe.db
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
