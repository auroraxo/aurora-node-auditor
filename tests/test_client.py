"""Tests for the Aurora Auditor client module."""

import pytest
from auditor.client import AuditorClient, AuditorError


def test_auditor_client_init_default():
    client = AuditorClient("http://127.0.0.1:8787")
    assert client.base_url == "http://127.0.0.1:8787"
    assert client.timeout == 5.0


def test_auditor_client_normalize_url():
    client = AuditorClient("http://127.0.0.1:8787/")
    assert client.base_url == "http://127.0.0.1:8787"


def test_auditor_client_get_health(monkeypatch):
    import urllib.request

    class MockResponse:
        status = 200
        def read(self):
            return b'{"status": "healthy", "service": "aurora-node-auditor", "version": "0.1.0"}'
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass

    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=5.0: MockResponse())

    client = AuditorClient("http://127.0.0.1:8787")
    health = client.get_health()
    assert health["status"] == "healthy"
    assert health["service"] == "aurora-node-auditor"
    assert health["version"] == "0.1.0"


def test_auditor_client_is_healthy(monkeypatch):
    import urllib.request

    class MockResponse:
        status = 200
        def read(self):
            return b'{"status": "healthy"}'
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass

    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=5.0: MockResponse())

    client = AuditorClient("http://127.0.0.1:8787")
    assert client.is_healthy() is True


def test_auditor_client_get_readiness(monkeypatch):
    import urllib.request

    class MockResponse:
        status = 200
        def read(self):
            return b'{"status": "healthy", "service": "aurora-node-auditor"}'
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass

    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=5.0: MockResponse())

    client = AuditorClient("http://127.0.0.1:8787")
    ready = client.get_readiness()
    assert ready["status"] == "healthy"


def test_auditor_client_get_telemetry(monkeypatch):
    import urllib.request

    class MockResponse:
        status = 200
        def read(self):
            return b'{"node": {"hostname": "test-node"}, "service": {"status": "healthy"}}'
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass

    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=5.0: MockResponse())

    client = AuditorClient("http://127.0.0.1:8787")
    tel = client.get_telemetry()
    assert tel["node"]["hostname"] == "test-node"


def test_auditor_client_get_metrics(monkeypatch):
    import urllib.request

    class MockResponse:
        status = 200
        def read(self):
            return b'# HELP node_uptime_seconds\nnode_uptime_seconds 123.45\n'
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass

    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=5.0: MockResponse())

    client = AuditorClient("http://127.0.0.1:8787")
    metrics = client.get_metrics()
    assert "node_uptime_seconds" in metrics


def test_auditor_client_error_handling(monkeypatch):
    import urllib.request
    import urllib.error

    def mock_urlopen_fail(req, timeout=5.0):
        raise urllib.error.URLError("Connection refused")

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen_fail)

    client = AuditorClient("http://127.0.0.1:8787")
    with pytest.raises(AuditorError) as exc_info:
        client.get_health()
    assert "Connection refused" in str(exc_info.value)
    assert client.is_healthy() is False


def test_auditor_client_http_error(monkeypatch):
    import urllib.request
    import urllib.error

    def mock_http_error(req, timeout=5.0):
        raise urllib.error.HTTPError(req.full_url, 500, "Internal Server Error", {}, None)

    monkeypatch.setattr(urllib.request, "urlopen", mock_http_error)

    client = AuditorClient("http://127.0.0.1:8787")
    with pytest.raises(AuditorError) as exc_info:
        client.get_telemetry()
    assert "HTTP 500" in str(exc_info.value)
