"""Comprehensive unit and integration tests for the audit module, endpoint, and client SDK."""

import http.client
import json
import threading
import time
from typing import Any, Dict
import urllib.request

from auditor import __version__
from auditor.audit import audit_resources, audit_system_security, run_node_audit
from auditor.client import AuditorClient
from auditor.server import create_server


def test_audit_resources_defaults():
    res = audit_resources()
    assert "status" in res
    assert res["status"] in ("healthy", "warning", "critical")
    assert "checks" in res
    check_names = {c["name"] for c in res["checks"]}
    assert "memory_usage" in check_names
    assert "disk_usage" in check_names
    assert "cpu_load" in check_names


def test_audit_resources_threshold_cases():
    mock_telemetry_ok: Dict[str, Any] = {
        "resources": {
            "memory": {"used_percent": 50.0},
            "disk": {"used_percent": 40.0},
            "cpu_count": 4,
            "load_avg": [1.0, 1.0, 1.0],
        }
    }
    res_ok = audit_resources(mock_telemetry_ok)
    assert res_ok["status"] == "healthy"
    for check in res_ok["checks"]:
        assert check["status"] == "ok"

    mock_telemetry_warn_mem: Dict[str, Any] = {
        "resources": {
            "memory": {"used_percent": 88.0},
            "disk": {"used_percent": 50.0},
            "cpu_count": 4,
            "load_avg": [1.0, 1.0, 1.0],
        }
    }
    res_warn = audit_resources(mock_telemetry_warn_mem)
    assert res_warn["status"] == "warning"
    mem_check = next(c for c in res_warn["checks"] if c["name"] == "memory_usage")
    assert mem_check["status"] == "warning"

    mock_telemetry_crit_mem: Dict[str, Any] = {
        "resources": {
            "memory": {"used_percent": 96.0},
            "disk": {"used_percent": 50.0},
            "cpu_count": 4,
            "load_avg": [1.0, 1.0, 1.0],
        }
    }
    res_crit_mem = audit_resources(mock_telemetry_crit_mem)
    assert res_crit_mem["status"] == "critical"

    mock_telemetry_warn_disk: Dict[str, Any] = {
        "resources": {
            "memory": {"used_percent": 50.0},
            "disk": {"used_percent": 82.0},
            "cpu_count": 4,
            "load_avg": [1.0, 1.0, 1.0],
        }
    }
    res_warn_disk = audit_resources(mock_telemetry_warn_disk)
    assert res_warn_disk["status"] == "warning"
    disk_check = next(c for c in res_warn_disk["checks"] if c["name"] == "disk_usage")
    assert disk_check["status"] == "warning"

    mock_telemetry_crit_disk: Dict[str, Any] = {
        "resources": {
            "memory": {"used_percent": 50.0},
            "disk": {"used_percent": 92.0},
            "cpu_count": 4,
            "load_avg": [1.0, 1.0, 1.0],
        }
    }
    res_crit_disk = audit_resources(mock_telemetry_crit_disk)
    assert res_crit_disk["status"] == "critical"

    mock_telemetry_warn_cpu: Dict[str, Any] = {
        "resources": {
            "memory": {"used_percent": 50.0},
            "disk": {"used_percent": 50.0},
            "cpu_count": 2,
            "load_avg": [2.5, 2.0, 1.5],
        }
    }
    res_warn_cpu = audit_resources(mock_telemetry_warn_cpu)
    assert res_warn_cpu["status"] == "warning"
    cpu_check = next(c for c in res_warn_cpu["checks"] if c["name"] == "cpu_load")
    assert cpu_check["status"] == "warning"

    mock_telemetry_crit_cpu: Dict[str, Any] = {
        "resources": {
            "memory": {"used_percent": 50.0},
            "disk": {"used_percent": 50.0},
            "cpu_count": 2,
            "load_avg": [4.5, 3.0, 2.0],
        }
    }
    res_crit_cpu = audit_resources(mock_telemetry_crit_cpu)
    assert res_crit_cpu["status"] == "critical"
    cpu_check = next(c for c in res_crit_cpu["checks"] if c["name"] == "cpu_load")
    assert cpu_check["status"] == "critical"


def test_audit_system_security(monkeypatch):
    monkeypatch.setattr("os.geteuid", lambda: 0)
    sec_root = audit_system_security()
    assert sec_root["status"] == "warning"
    root_check = next(c for c in sec_root["checks"] if c["name"] == "running_as_root")
    assert root_check["passed"] is False

    monkeypatch.setattr("os.geteuid", lambda: 1000)
    sec_non_root = audit_system_security()
    root_check2 = next(c for c in sec_non_root["checks"] if c["name"] == "running_as_root")
    assert root_check2["passed"] is True


def test_run_node_audit():
    audit_data = run_node_audit()
    assert "timestamp" in audit_data
    assert "status" in audit_data
    assert audit_data["status"] in ("healthy", "warning", "critical")
    assert "node" in audit_data
    assert "resources" in audit_data
    assert "security" in audit_data
    assert audit_data["service"]["name"] == "aurora-node-auditor"
    assert audit_data["service"]["version"] == __version__


def test_auditor_client_get_audit(monkeypatch):
    class MockResponse:
        status = 200
        def read(self):
            return (
                b'{"status": "healthy", "service": {"name": "aurora-node-auditor", "version": "0.1.5"},'
                b' "resources": {"status": "healthy"}, "security": {"status": "healthy"}}'
            )
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass

    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=5.0: MockResponse())

    client = AuditorClient("http://127.0.0.1:8787")
    audit = client.get_audit()
    assert audit["status"] == "healthy"
    assert audit["service"]["name"] == "aurora-node-auditor"
    assert audit["resources"]["status"] == "healthy"


def test_server_audit_endpoint_get_and_head():
    server = create_server("127.0.0.1", 18788)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.1)

    try:
        req = urllib.request.urlopen("http://127.0.0.1:18788/audit")
        assert req.status == 200
        data = json.loads(req.read().decode("utf-8"))
        assert "status" in data
        assert "node" in data
        assert "resources" in data
        assert "security" in data
        assert data["service"]["name"] == "aurora-node-auditor"

        conn = http.client.HTTPConnection("127.0.0.1", 18788)
        conn.request("HEAD", "/audit")
        resp = conn.getresponse()
        assert resp.status == 200
        assert resp.getheader("Content-Type") == "application/json; charset=utf-8"
        assert resp.read() == b""
        conn.close()

        client = AuditorClient("http://127.0.0.1:18788")
        client_audit = client.get_audit()
        assert client_audit["status"] in ("healthy", "warning", "critical")
        assert client_audit["service"]["name"] == "aurora-node-auditor"
    finally:
        server.shutdown()
        server.server_close()


def test_audit_cli_main(capsys, monkeypatch):
    """Test CLI main execution with --json and default output."""
    from auditor.audit import main
    import sys

    # Test text output
    monkeypatch.setattr(sys, "argv", ["node-audit"])
    try:
        main()
    except SystemExit as e:
        assert e.code == 0
    captured = capsys.readouterr()
    assert "=== Aurora Node Audit:" in captured.out
    assert "Overall Status:" in captured.out

    # Test json output
    monkeypatch.setattr(sys, "argv", ["node-audit", "--json"])
    try:
        main()
    except SystemExit as e:
        assert e.code == 0
    captured_json = capsys.readouterr()
    data = json.loads(captured_json.out)
    assert data["status"] in ["healthy", "warning", "critical"]
    assert "resources" in data
    assert "security" in data
