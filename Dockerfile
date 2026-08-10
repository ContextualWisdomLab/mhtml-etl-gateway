# Operator image: mount MHTML sources and pass DSN at runtime.
# Never bake private CRM absolute paths into the image.
FROM python:3.12-slim

WORKDIR /app

# Non-root runtime user (Semgrep/Trivy DS-0002)
RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin appuser

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir . \
    && chown -R appuser:appuser /app

USER appuser

ENTRYPOINT ["mhtml-etl-gateway"]
CMD ["--help"]
