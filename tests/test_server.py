"""Integration tests for HTTP server."""

import http.client
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
        # 1. Health endpoint GET
        req = urllib.request.urlopen("http://127.0.0.1:18787/health")
        assert req.status == 200
        health_data = json.loads(req.read().decode("utf-8"))
        assert health_data["status"] == "healthy"
        assert health_data["service"] == "aurora-node-auditor"
        assert health_data["version"] == "0.1.5"

        # 2. Health endpoint HEAD
        conn = http.client.HTTPConnection("127.0.0.1", 18787)
        conn.request("HEAD", "/health")
        resp = conn.getresponse()
        assert resp.status == 200
        assert resp.getheader("Content-Type") == "application/json; charset=utf-8"
        assert resp.read() == b""
        conn.close()

        # 3. Root endpoint HEAD
        conn = http.client.HTTPConnection("127.0.0.1", 18787)
        conn.request("HEAD", "/")
        resp = conn.getresponse()
        assert resp.status == 200
        assert resp.read() == b""
        conn.close()

        # 4. Telemetry endpoint GET & HEAD
        req = urllib.request.urlopen("http://127.0.0.1:18787/telemetry")
        assert req.status == 200
        telemetry = json.loads(req.read().decode("utf-8"))
        assert "resources" in telemetry
        assert "node" in telemetry

        conn = http.client.HTTPConnection("127.0.0.1", 18787)
        conn.request("HEAD", "/telemetry")
        resp = conn.getresponse()
        assert resp.status == 200
        assert resp.read() == b""
        conn.close()

        # 5. Metrics endpoint GET & HEAD (Prometheus format)
        req = urllib.request.urlopen("http://127.0.0.1:18787/metrics")
        assert req.status == 200
        metrics_text = req.read().decode("utf-8")
        assert "node_uptime_seconds" in metrics_text
        assert "node_memory_total_bytes" in metrics_text
        assert "process_rss_bytes" in metrics_text
        assert "process_threads" in metrics_text

        conn = http.client.HTTPConnection("127.0.0.1", 18787)
        conn.request("HEAD", "/metrics")
        resp = conn.getresponse()
        assert resp.status == 200
        assert resp.getheader("Content-Type") == "text/plain; version=0.0.4; charset=utf-8"
        assert resp.read() == b""
        conn.close()

        # 6. 404 endpoint GET & HEAD
        try:
            urllib.request.urlopen("http://127.0.0.1:18787/nonexistent")
            assert False, "Should have raised 404"
        except urllib.error.HTTPError as err:
            assert err.code == 404

        conn = http.client.HTTPConnection("127.0.0.1", 18787)
        conn.request("HEAD", "/nonexistent")
        resp = conn.getresponse()
        assert resp.status == 404
        assert resp.read() == b""
        conn.close()

    finally:
        server.shutdown()
        server.server_close()
