# Aurora Node Auditor

Autonomous Node Inspector & Telemetry Auditor for Kolonie AI Citizens.

## Endpoints

- `GET /` or `GET /health` or `GET /ready`: Fast liveness / readiness probes.
- `GET /telemetry` / `GET /status`: Complete JSON snapshot of node resources, OS vitals, process statistics, and service status.
- `GET /metrics`: Standard Prometheus-compatible exposition format (CPU, memory, disk, process RSS, thread count).

## Running locally

```bash
uv run python3 -m auditor.server --host 127.0.0.1 --port 8787
```

## Running as a systemd service

The service is configured as `aurora-node-auditor.service` on the host, bound to `127.0.0.1:8787` and reverse-proxied through Nginx (`/health`, `/ready`, `/telemetry`, `/metrics`).


## Running Tests
```bash
uv run pytest
```
