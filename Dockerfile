FROM python:3.12.15-slim-trixie@sha256:05cda9777409a9c3ffddd94a4c476b79f0769a0b4857f0c7ed9226b6800b0d6f AS build
ENV UV_CACHE_DIR=/tmp/uv-cache UV_PROJECT_ENVIRONMENT=/opt/venv \
    OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 OMP_NUM_THREADS=2
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1=14.2.0-19 \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv==0.12.18
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --locked --no-dev --no-editable
RUN /opt/venv/bin/reco build-bundle --fixture --root /opt/models --select
RUN chmod -R a+rX /opt/models
COPY benchmarks/stage_runtime.py /tmp/stage_runtime.py
RUN python /tmp/stage_runtime.py /runtime \
    --base python:3.12.15-slim-trixie@sha256:05cda9777409a9c3ffddd94a4c476b79f0769a0b4857f0c7ed9226b6800b0d6f

FROM scratch
ENV PATH=/opt/venv/bin:/usr/local/bin PYTHONDONTWRITEBYTECODE=1 \
    OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 OMP_NUM_THREADS=2
WORKDIR /app
COPY --from=build /runtime /
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/readyz', timeout=2)"]
CMD ["uvicorn", "reco.container:application", "--factory", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
