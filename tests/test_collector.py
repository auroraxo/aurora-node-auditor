"""Unit tests for metrics collector."""

from auditor.collector import collect_node_telemetry, get_disk_stats, get_memory_stats, get_uptime_seconds


def test_uptime_seconds_positive():
    uptime = get_uptime_seconds()
    assert isinstance(uptime, (int, float))
    assert uptime > 0


def test_memory_stats_structure():
    mem = get_memory_stats()
    assert "total_bytes" in mem
    assert "available_bytes" in mem
    assert "used_percent" in mem
    assert isinstance(mem["used_percent"], (int, float))


def test_disk_stats_structure():
    disk = get_disk_stats("/")
    assert "path" in disk
    assert "total_bytes" in disk
    assert "used_percent" in disk
    assert disk["total_bytes"] > 0


def test_collect_node_telemetry():
    data = collect_node_telemetry()
    assert "timestamp" in data
    assert "node" in data
    assert "resources" in data
    assert "process" in data
    assert "service" in data
    assert data["service"]["name"] == "aurora-node-auditor"
    assert data["service"]["status"] == "healthy"
    assert data["process"]["pid"] > 0


def test_collect_node_telemetry_loadavg_oserror(monkeypatch):
    import os
    def mock_getloadavg_fail():
        raise OSError("Load average unavailable in container environment")

    monkeypatch.setattr(os, "getloadavg", mock_getloadavg_fail)
    data = collect_node_telemetry()
    assert "resources" in data
    assert data["resources"]["load_avg"] == []



def test_process_stats_structure():
    from auditor.collector import get_process_stats
    proc = get_process_stats()
    assert "pid" in proc
    assert "threads" in proc
    assert "rss_bytes" in proc
    assert proc["pid"] > 0
    assert proc["threads"] >= 1

