# Operator image: mount MHTML sources and pass DSN at runtime.
# Never bake private CRM absolute paths into the image.
FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

ENTRYPOINT ["mhtml-etl-gateway"]
CMD ["--help"]
