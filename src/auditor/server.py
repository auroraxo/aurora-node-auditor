"""HTTP Server for Aurora Node Auditor."""

import argparse
import json
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
import sys
from typing import Tuple

from auditor import __version__
from auditor.audit import run_node_audit
from auditor.collector import collect_node_telemetry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("aurora_auditor")


class AuditorRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for auditor endpoints."""

    def _send_json(self, status_code: int, data: dict, send_body: bool = True) -> None:
        payload = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        if send_body:
            self.wfile.write(payload)

    def _send_text(self, status_code: int, text: str, content_type: str = "text/plain", send_body: bool = True) -> None:
        payload = text.encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        if send_body:
            self.wfile.write(payload)

    def _dispatch(self, send_body: bool = True) -> None:
        path = self.path.split("?")[0]
        if path in ("/", "/health", "/ready"):
            self._send_json(200, {
                "status": "healthy",
                "service": "aurora-node-auditor",
                "version": __version__
            }, send_body=send_body)
        elif path in ("/status", "/telemetry", "/kolonie/status"):
            data = collect_node_telemetry()
            self._send_json(200, data, send_body=send_body)
        elif path == "/audit":
            data = run_node_audit()
            self._send_json(200, data, send_body=send_body)
        elif path == "/metrics":
            # Prometheus formatted metric export
            telemetry = collect_node_telemetry()
            lines = [
                "# HELP node_uptime_seconds Total node uptime in seconds",
                "# TYPE node_uptime_seconds gauge",
                f"node_uptime_seconds {telemetry['node']['uptime_seconds']}",
                "# HELP node_cpu_count Logical CPU count",
                "# TYPE node_cpu_count gauge",
                f"node_cpu_count {telemetry['resources']['cpu_count']}",
                "# HELP node_memory_total_bytes Total physical memory in bytes",
                "# TYPE node_memory_total_bytes gauge",
                f"node_memory_total_bytes {telemetry['resources']['memory']['total_bytes']}",
                "# HELP node_memory_available_bytes Available physical memory in bytes",
                "# TYPE node_memory_available_bytes gauge",
                f"node_memory_available_bytes {telemetry['resources']['memory']['available_bytes']}",
                "# HELP node_disk_used_percent Disk usage percentage on root",
                "# TYPE node_disk_used_percent gauge",
                f"node_disk_used_percent {telemetry['resources']['disk'].get('used_percent', 0.0)}",
                "# HELP process_rss_bytes Resident memory size of auditor process in bytes",
                "# TYPE process_rss_bytes gauge",
                f"process_rss_bytes {telemetry['process']['rss_bytes']}",
                "# HELP process_threads Number of active threads in auditor process",
                "# TYPE process_threads gauge",
                f"process_threads {telemetry['process']['threads']}",
            ]
            self._send_text(200, "\n".join(lines) + "\n", content_type="text/plain; version=0.0.4", send_body=send_body)
        else:
            self._send_json(404, {"error": "not_found", "path": path}, send_body=send_body)

    def do_GET(self) -> None:
        self._dispatch(send_body=True)

    def do_HEAD(self) -> None:
        self._dispatch(send_body=False)

    def log_message(self, format: str, *args: Tuple[object, ...]) -> None:
        logger.debug("%s - - [%s] %s", self.address_string(), self.log_date_time_string(), format % args)


def create_server(host: str = "127.0.0.1", port: int = 8787) -> HTTPServer:
    """Create configured HTTPServer instance."""
    return HTTPServer((host, port), AuditorRequestHandler)


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser used by the installed console script."""
    parser = argparse.ArgumentParser(description="Aurora Node Auditor Server")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8787, help="Bind port (default: 8787)")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    server = create_server(args.host, args.port)
    logger.info("Starting aurora-node-auditor on %s:%d", args.host, args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down aurora-node-auditor")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
