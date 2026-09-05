"""Integration tests for HTTP server."""

import json
import threading
import time
import urllib.request
from auditor.server import create_server


def test_server_endpoints():
    server = create_server("127.0.0.1", 18787)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.1)

    try:
        # 1. Health endpoint
        req = urllib.request.urlopen("http://127.0.0.1:18787/health")
        assert req.status == 200
        health_data = json.loads(req.read().decode("utf-8"))
        assert health_data["status"] == "healthy"
        assert health_data["service"] == "aurora-node-auditor"

        # 2. Telemetry endpoint
        req = urllib.request.urlopen("http://127.0.0.1:18787/telemetry")
        assert req.status == 200
        telemetry = json.loads(req.read().decode("utf-8"))
        assert "resources" in telemetry
        assert "node" in telemetry

        # 3. Metrics endpoint (Prometheus format)
        req = urllib.request.urlopen("http://127.0.0.1:18787/metrics")
        assert req.status == 200
        metrics_text = req.read().decode("utf-8")
        assert "node_uptime_seconds" in metrics_text
        assert "node_memory_total_bytes" in metrics_text
        assert "process_rss_bytes" in metrics_text
        assert "process_threads" in metrics_text


        # 4. 404 endpoint
        try:
            urllib.request.urlopen("http://127.0.0.1:18787/nonexistent")
            assert False, "Should have raised 404"
        except urllib.error.HTTPError as err:
            assert err.code == 404

    finally:
        server.shutdown()
        server.server_close()
