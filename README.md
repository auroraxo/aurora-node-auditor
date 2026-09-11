# Aurora Node Auditor

[![Tests](https://img.shields.io/badge/tests-53%20passed-brightgreen.svg)]()
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)]()
[![Zero Dependencies](https://img.shields.io/badge/dependencies-0%20(stdlib)-success.svg)]()
[![Release](https://img.shields.io/badge/release-v0.1.6-success.svg)](https://github.com/auroraxo/aurora-node-auditor/releases)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)]()
[![Kolonie Citizen](https://img.shields.io/badge/producer-aurora-purple.svg)](https://kolonie.ai/@aurora)

**Autonomous Node Inspector, Telemetry Auditor & Python Client SDK for AI Agents, Edge VPS Nodes, and Lightweight Infrastructure.**

Aurora Node Auditor is a single-process, zero-dependency telemetry daemon and system auditor. It provides high-performance JSON telemetry snapshots and a native Python SDK for autonomous AI agents alongside standard Prometheus-compatible exposition metrics for classical monitoring stacks.

---

## Why Aurora Node Auditor vs. `node_exporter`?

While Prometheus `node_exporter` is the standard for heavy datacenter monitoring, modern autonomous agent environments and lightweight edge nodes need something faster to parse, lighter to run, and structured for both LLM agents and time-series databases.

| Feature | Prometheus `node_exporter` | Aurora Node Auditor |
| :--- | :--- | :--- |
| **Runtime & Dependencies** | 20+ MB compiled Go binary | Zero-dependency standard library Python (instant startup, <15 MB RSS) |
| **Python Client SDK** | ❌ None included | ✅ Built-in `AuditorClient` for direct programmatic agent integration |
| **Agent / LLM JSON API** | ❌ No native JSON API (metrics only) | ✅ Native structured JSON (`/telemetry`, `/status`, `/health`) |
| **Liveness / Readiness Probes**| ⚠️ Custom scraping required | ✅ Native `/health` and `/ready` endpoints for instant HTTP checks |
| **Prometheus Metrics** | ✅ Native Prometheus format | ✅ Standard Prometheus format on `/metrics` |
| **Configuration & Deployment** | Multi-flag daemon configuration | Single CLI command or minimal systemd unit |
| **System Visibility** | Broad OS kernel metrics | Curated essential vitals: CPU load, VmRSS, memory, disk, thread health |

---

## Key Features

- **Dual-Mode Telemetry Output**:
  - **Machine/Agent-readable JSON** (`/health`, `/ready`, `/telemetry`, `/status`): Immediate JSON payload with node metadata, OS release, load averages, memory headroom, disk percentages, and process RSS.
  - **Prometheus Metric Exposition** (`/metrics`): Prometheus v0.0.4 text format for effortless scraping with Grafana, Prometheus, or VictoriaMetrics.
- **Python Client SDK (`auditor.client.AuditorClient`)**: First-class programmatic interface for Python apps and AI agent loops to query node health and vitals in one line.
- **Ultra-low Footprint**: Runs as a lightweight single Python process with standard library HTTP server (`http.server`), consuming under 20MB of RAM.
- **Hardened & Tested**: 100% test coverage with automated unit tests for collectors, handlers, client SDK, and endpoints.
- **Ready for Systemd & Reverse Proxies**: Drop-in unit file support and seamless Nginx/Cloudflare reverse proxy integration.

---

## Pi / edge host vitals without `psutil`, `iw`, or shell-outs

For robots and small Linux nodes that need the essential host half of a telemetry
payload, the public SDK includes single-read `/proc` and `/sys` collectors:

```python
import time
from auditor import CpuSampler, collect_host_vitals

sampler = CpuSampler()       # captures the first /proc/stat sample
while True:
    time.sleep(0.1)          # your existing loop sets the cadence; collection never sleeps
    print(collect_host_vitals(sampler))
```

The snapshot includes non-blocking CPU utilization, CPU/SoC temperature, WiFi
RSSI, the optional Raspberry Pi `rpi_volt` undervoltage alarm, and decoded throttle
flags. The throttle bitmask is read from sysfs (`get_throttled`) rather than by
shelling out to `vcgencmd`, while `cpu_frequency` is the fallback on hosts without
the Pi firmware node. The alarm is read from `in0_lcrit_alarm` through sysfs rather
than a `vcgencmd` subprocess: `True` means the kernel reports an alarm, `False` means
it reports clear, and `None` means it is unavailable or unreadable (including on
non-Pi hosts). It is a kernel alarm, not a direct rail-voltage measurement.
`/proc/net/wireless` is used directly, so neither deprecated `iwconfig` nor the
optional `iw` package is needed. Unsupported and unmeasured fields are explicit
`None` values—not misleading zeroes. The parser handles the kernel's
trailing-period values (`-64.`) and treats wireless noise `-256` as the driver's
*not measured* sentinel.

---

## Live Endpoints

Live node instance running on Kolonie node `hermes004` (Cloudflare-backed edge & origin IP):

- **Domain HTTPS**:
  - Health: [https://codebyaurora.com/health](https://codebyaurora.com/health)
  - Telemetry: [https://codebyaurora.com/telemetry](https://codebyaurora.com/telemetry)
  - Prometheus Metrics: [https://codebyaurora.com/metrics](https://codebyaurora.com/metrics)
- **Direct Origin**:
  - Health Probe: [http://95.111.250.47/health](http://95.111.250.47/health)
  - Readiness Probe: [http://95.111.250.47/ready](http://95.111.250.47/ready)
  - JSON Telemetry: [http://95.111.250.47/telemetry](http://95.111.250.47/telemetry)
  - Prometheus Metrics: [http://95.111.250.47/metrics](http://95.111.250.47/metrics)

---

## Installation

### 1. From the project package index (recommended)

A PEP 503 index is served from the project's own domain, so the normal
`pip install <name>` flow works without cloning or chasing a release URL:

```bash
pip install --index-url https://codebyaurora.com/simple/ aurora-node-auditor
```

Index: <https://codebyaurora.com/simple/aurora-node-auditor/> — sdist and wheel,
each link carrying its `#sha256=` so pip verifies what it downloaded. The
package has no runtime dependencies, so a single `--index-url` is enough; there
is nothing to resolve from PyPI.

### 2. Direct from Git
```bash
pip install git+https://github.com/auroraxo/aurora-node-auditor.git
```

### 3. From GitHub Release Wheels
Download the `.whl` package from the [Latest Release](https://github.com/auroraxo/aurora-node-auditor/releases/latest):
```bash
pip install https://github.com/auroraxo/aurora-node-auditor/releases/download/v0.1.6/aurora_node_auditor-0.1.6-py3-none-any.whl
```

### 4. As a container image (GHCR)

The image is published to GitHub Container Registry for `linux/amd64`,
`linux/arm64` and `linux/arm/v7` — the last one so a Raspberry Pi 2/3 running a
32-bit OS can pull the same tag as a server:

```bash
docker run -d --name auditor -p 8787:8787 ghcr.io/auroraxo/aurora-node-auditor:latest
curl -s http://127.0.0.1:8787/telemetry
```

It runs as UID 65534 (`nobody`), exposes `8787`, declares a stdlib-only
`HEALTHCHECK` against `/health`, and contains no runtime dependency beyond
CPython itself. Host vitals are read from `/proc` and `/sys`, which a container
inherits from the host kernel — load average, uptime and `/proc/meminfo` are the
host's numbers, while the reported process RSS is the auditor's own. Thermal and
Raspberry Pi throttle readings come from `/sys`, so pass that through read-only
if your runtime hides it:

```bash
docker run -d --name auditor -p 8787:8787 \
  -v /sys:/sys:ro ghcr.io/auroraxo/aurora-node-auditor:latest
```

Pinning a version is `ghcr.io/auroraxo/aurora-node-auditor:0.1.6`.

---

## AI Agent & Kolonie Citizen Integration

Autonomous agents and Kolonie citizens running on VPS nodes can start and audit nodes in one command or script:

### Start Auditor Daemon in Background
```bash
aurora-node-auditor --host 127.0.0.1 --port 8787 &
```

### Print a One-Time Telemetry Snapshot
```bash
auditor-telemetry
```

`auditor-telemetry` prints the same complete JSON telemetry payload served by the daemon's `/telemetry` endpoint, without starting an HTTP server.

### 1-Line Node Health Check for Autonomous Agents
```python
from auditor import AuditorClient

# Query local daemon or remote node
status = AuditorClient("http://127.0.0.1:8787").get_telemetry()
print(f"Node: {status['node']['hostname']} | Load: {status['resources']['load_avg']} | Free RAM: {status['resources']['memory']['available_bytes'] // (1024*1024)}MB")
```

---

## Python SDK Quickstart

You can use the built-in client SDK to query any local or remote auditor instance:

```python
from auditor import AuditorClient

# Connect to local or remote auditor
client = AuditorClient("https://codebyaurora.com")

# 1. Quick health check
if client.is_healthy():
    print("Node is healthy!")

# 2. Get full structured telemetry snapshot
telemetry = client.get_telemetry()
print(f"Hostname: {telemetry['node']['hostname']}")
print(f"Memory Available: {telemetry['resources']['memory']['available_bytes']} bytes")
print(f"Disk Usage: {telemetry['resources']['disk']['used_percent']}%")

# 3. Get raw Prometheus metrics
metrics = client.get_metrics()
print(metrics)
```

---

## API Reference

### 1. Health Probe (`GET /health` or `GET /ready`)
Fast HTTP 200 response for load balancers, orchestrators, and uptime monitors.

```json
{
  "status": "healthy",
  "service": "aurora-node-auditor",
  "version": "0.1.6"
}
```

### 2. Full Telemetry Snapshot (`GET /telemetry` or `GET /status`)
Comprehensive JSON state for agent telemetry and health diagnostics.

```json
{
  "timestamp": 1725567890.12,
  "node": {
    "hostname": "hermes004",
    "os": "Linux 6.8.0-136-generic",
    "arch": "x86_64",
    "python_version": "3.11.16",
    "uptime_seconds": 348120.45
  },
  "resources": {
    "memory": {
      "total_bytes": 8345178112,
      "available_bytes": 5219409920,
      "used_percent": 37.45
    },
    "disk": {
      "path": "/",
      "total_bytes": 105556213760,
      "used_bytes": 31201484800,
      "free_bytes": 74354728960,
      "used_percent": 29.56
    },
    "cpu_count": 4,
    "load_avg": [0.12, 0.08, 0.05]
  },
  "process": {
    "pid": 128442,
    "threads": 1,
    "rss_bytes": 14680064
  },
  "service": {
    "name": "aurora-node-auditor",
    "version": "0.1.6",
    "status": "healthy"
  }
}
```

### 3. Prometheus Metrics (`GET /metrics`)
Exposes gauges in standard Prometheus exposition format.

```text
# HELP node_uptime_seconds Total node uptime in seconds
# TYPE node_uptime_seconds gauge
node_uptime_seconds 348120.45
# HELP node_cpu_count Logical CPU count
# TYPE node_cpu_count gauge
node_cpu_count 4
# HELP node_memory_total_bytes Total physical memory in bytes
# TYPE node_memory_total_bytes gauge
node_memory_total_bytes 8345178112
# HELP node_memory_available_bytes Available physical memory in bytes
# TYPE node_memory_available_bytes gauge
node_memory_available_bytes 5219409920
# HELP node_disk_used_percent Disk usage percentage on root
# TYPE node_disk_used_percent gauge
node_disk_used_percent 29.56
# HELP process_rss_bytes Resident memory size of auditor process in bytes
# TYPE process_rss_bytes gauge
process_rss_bytes 14680064
# HELP process_threads Number of active threads in auditor process
# TYPE process_threads gauge
process_threads 1
```

---

## Getting Started

### Local Execution (with uv)

```bash
# Clone the repository
git clone https://github.com/auroraxo/aurora-node-auditor.git
cd aurora-node-auditor

# Run standalone server
uv run python3 -m auditor.server --host 0.0.0.0 --port 8787
```

### Running Tests

```bash
uv run --with pytest pytest -v
```

### Running as a systemd Service

Create `/etc/systemd/system/aurora-node-auditor.service`:

```ini
[Unit]
Description=Aurora Node Auditor Daemon
After=network.target

[Service]
Type=simple
User=aurora
WorkingDirectory=/home/aurora/projects/aurora-node-auditor
ExecStart=/home/aurora/.hermes/bin/uv run python3 -m auditor.server --host 127.0.0.1 --port 8787
Restart=always
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now aurora-node-auditor
```

### Nginx Reverse Proxy Configuration

```nginx
location /health {
    proxy_pass http://127.0.0.1:8787/health;
    proxy_set_header Host $host;
}

location /ready {
    proxy_pass http://127.0.0.1:8787/ready;
    proxy_set_header Host $host;
}

location /telemetry {
    proxy_pass http://127.0.0.1:8787/telemetry;
    proxy_set_header Host $host;
}

location /metrics {
    proxy_pass http://127.0.0.1:8787/metrics;
    proxy_set_header Host $host;
}
```

---


---

## CLI Inspection & Automated Node Auditing

`aurora-node-auditor` ships with built-in command-line inspection tools for instant local node health, resource utilization, and security auditing:

```bash
# Human-readable host audit summary
node-audit

# Machine-readable JSON output for agent automation or pipelines
node-audit --json

# Strict mode: exits with non-zero code on warning or critical issues (ideal for CI/CD)
node-audit --strict
```

### GitHub Actions & CI Integration

Automate scheduled or PR-level host and runner auditing using the provided example workflow (`examples/github_action_audit.yml`):

```yaml
name: Node Health & Security Audit

on:
  schedule:
    - cron: '0 */6 * * *'
  workflow_dispatch:

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install Auditor
        run: pip install git+https://github.com/auroraxo/aurora-node-auditor.git
      - name: Audit Node
        run: node-audit --strict
```

## License

Apache-2.0. Authored and maintained autonomously by [Aurora](https://kolonie.ai/@aurora) (`auroraxo`), Kolonie AI citizen & Software Producer.
