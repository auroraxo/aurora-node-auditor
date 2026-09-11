# syntax=docker/dockerfile:1
FROM python:3.12-slim

LABEL org.opencontainers.image.title="aurora-node-auditor" \
      org.opencontainers.image.description="Zero-dependency telemetry daemon and node auditor: JSON /telemetry /status /health /ready plus Prometheus /metrics" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.source="https://github.com/auroraxo/aurora-node-auditor" \
      org.opencontainers.image.url="https://codebyaurora.com" \
      org.opencontainers.image.authors="Aurora"

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir . && rm -rf /app/src /app/pyproject.toml

USER 65534:65534
EXPOSE 8787

# Liveness without curl in the image: stdlib only, same as the package itself.
HEALTHCHECK --interval=30s --timeout=5s --start-period=3s --retries=3 \
  CMD ["python", "-c", "import urllib.request,sys;sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8787/health',timeout=4).status==200 else 1)"]

ENTRYPOINT ["aurora-auditor"]
CMD ["--host=0.0.0.0", "--port=8787"]
