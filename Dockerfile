# Operator image: mount MHTML sources and pass DSN at runtime.
# Never bake private CRM absolute paths into the image.
# Pin base image digest (Scorecard / DS pinned-dependencies).
FROM python:3.12-slim@sha256:229a2c5bfa27522db7815ea81f9bed70af17ccb9de9fc7ad142b1877b5830d36

WORKDIR /app

# Non-root runtime user (Semgrep/Trivy DS-0002)
RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin appuser

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir . \
    && chown -R appuser:appuser /app

USER appuser

# Container health signal for orchestrators (Strix / CIS baseline).
# CLI image: verify the installed entrypoint responds.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD mhtml-etl-gateway --help >/dev/null || exit 1

ENTRYPOINT ["mhtml-etl-gateway"]
CMD ["--help"]
