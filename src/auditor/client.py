"""Python Client SDK for Aurora Node Auditor.

Provides convenient programmatic access to Auditor HTTP and telemetry endpoints
for AI agents, monitoring scripts, and infrastructure tools.
"""

import json
from typing import Any, Dict, Optional
import urllib.error
import urllib.request


class AuditorError(Exception):
    """Base exception for Auditor client errors."""
    pass


class AuditorClient:
    """Client for querying an Aurora Node Auditor instance."""

    def __init__(self, base_url: str = "http://127.0.0.1:8787", timeout: float = 5.0) -> None:
        """Initialize the client.

        Args:
            base_url: Base URL of the auditor service (e.g. http://127.0.0.1:8787 or https://codebyaurora.com).
            timeout: Network request timeout in seconds.
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _get_json(self, path: str) -> Dict[str, Any]:
        """Perform a GET request and parse JSON response."""
        try:
            from auditor import __version__
            ua_version = __version__
        except Exception:
            ua_version = "0.1.4"

        url = f"{self.base_url}/{path.lstrip('/')}"
        req = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": f"aurora-node-auditor-client/{ua_version}"
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = resp.read().decode("utf-8")
                return json.loads(data)
        except urllib.error.HTTPError as exc:
            raise AuditorError(f"HTTP {exc.code} fetching {url}: {exc.reason}") from exc
        except urllib.error.URLError as exc:
            raise AuditorError(f"Network error fetching {url}: {exc.reason}") from exc
        except Exception as exc:
            raise AuditorError(f"Unexpected error querying {url}: {str(exc)}") from exc

    def _get_text(self, path: str) -> str:
        """Perform a GET request and return text response."""
        try:
            from auditor import __version__
            ua_version = __version__
        except Exception:
            ua_version = "0.1.4"

        url = f"{self.base_url}/{path.lstrip('/')}"
        req = urllib.request.Request(
            url,
            headers={
                "Accept": "text/plain",
                "User-Agent": f"aurora-node-auditor-client/{ua_version}"
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            raise AuditorError(f"HTTP {exc.code} fetching {url}: {exc.reason}") from exc
        except urllib.error.URLError as exc:
            raise AuditorError(f"Network error fetching {url}: {exc.reason}") from exc
        except Exception as exc:
            raise AuditorError(f"Unexpected error querying {url}: {str(exc)}") from exc

    def get_health(self) -> Dict[str, Any]:
        """Fetch health check status."""
        return self._get_json("/health")

    def is_healthy(self) -> bool:
        """Return True if health check succeeds and returns healthy status."""
        try:
            res = self.get_health()
            return res.get("status") == "healthy"
        except AuditorError:
            return False

    def get_readiness(self) -> Dict[str, Any]:
        """Fetch readiness probe status."""
        return self._get_json("/ready")

    def get_telemetry(self) -> Dict[str, Any]:
        """Fetch full node telemetry snapshot (JSON)."""
        return self._get_json("/telemetry")

    def get_audit(self) -> Dict[str, Any]:
        """Fetch automated node audit snapshot (JSON)."""
        return self._get_json("/audit")

    def get_metrics(self) -> str:
        """Fetch raw Prometheus exposition metrics (text/plain)."""
        return self._get_text("/metrics")
