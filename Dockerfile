FROM python:3.12.15-slim-bookworm@sha256:34386ef0cb081344d7ec1c103ba398e6e9f64e9ab3a1509accc92a4e24a07258 AS build
ENV UV_CACHE_DIR=/tmp/uv-cache UV_PROJECT_ENVIRONMENT=/opt/venv \
    OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 OMP_NUM_THREADS=2
WORKDIR /app
RUN pip install --no-cache-dir uv==0.12.18
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --locked --no-dev --no-editable
RUN /opt/venv/bin/reco build-bundle --fixture --root /opt/models --select

FROM python:3.12.15-slim-bookworm@sha256:34386ef0cb081344d7ec1c103ba398e6e9f64e9ab3a1509accc92a4e24a07258
ENV PATH=/opt/venv/bin:$PATH PYTHONDONTWRITEBYTECODE=1 \
    OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 OMP_NUM_THREADS=2
WORKDIR /app
COPY --from=build /opt/venv /opt/venv
COPY --from=build /opt/models /opt/models
COPY uv.lock ./
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1=12.2.0-14+deb12u1 \
    && rm -rf /var/lib/apt/lists/*
RUN chmod -R a+rX /opt/models && useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin reco
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/readyz', timeout=2)"
CMD ["uvicorn", "reco.container:application", "--factory", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
