"""Smoke test for wheel packaging and isolated entry point execution."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import pytest
from auditor import __version__


def get_project_scripts() -> dict[str, str]:
    """Read console script definitions from pyproject.toml."""
    pyproject_path = Path(__file__).resolve().parent.parent / "pyproject.toml"
    scripts = {}
    in_scripts_section = False

    for raw_line in pyproject_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line == "[project.scripts]":
            in_scripts_section = True
            continue
        if in_scripts_section and line.startswith("["):
            break
        if in_scripts_section and line:
            name, target = line.split("=", maxsplit=1)
            scripts[name.strip()] = target.strip().strip('"')

    return scripts


def test_advertised_scripts_non_empty():
    scripts = get_project_scripts()
    assert set(scripts.keys()) == {
        "aurora-node-auditor",
        "aurora-auditor",
        "auditor-telemetry",
        "node-audit",
        "auditor-check",
    }


def test_wheel_build_and_isolated_install_smoke():
    uv_bin = shutil.which("uv")
    if uv_bin is None:
        pytest.skip("uv is required to build and install the wheel in isolation")

    project_root = Path(__file__).resolve().parent.parent
    scripts = get_project_scripts()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        wheel_dir = tmp_path / "dist"
        build_res = subprocess.run(
            [uv_bin, "build", "--wheel", "--out-dir", str(wheel_dir), str(project_root)],
            capture_output=True,
            text=True,
        )
        assert build_res.returncode == 0, build_res.stderr

        wheels = list(wheel_dir.glob("*.whl"))
        assert len(wheels) == 1

        venv_dir = tmp_path / "venv"
        create_res = subprocess.run(
            [uv_bin, "venv", "--python", sys.executable, str(venv_dir)],
            capture_output=True,
            text=True,
        )
        assert create_res.returncode == 0, create_res.stderr

        venv_python = venv_dir / "bin" / "python"
        install_res = subprocess.run(
            [uv_bin, "pip", "install", "--python", str(venv_python), str(wheels[0])],
            capture_output=True,
            text=True,
        )
        assert install_res.returncode == 0, install_res.stderr

        for script_name in scripts:
            script_path = venv_dir / "bin" / script_name
            assert script_path.is_file()
            assert os.access(script_path, os.X_OK)

            help_res = subprocess.run(
                [str(script_path), "--help"],
                capture_output=True,
                text=True,
            )
            assert help_res.returncode == 0, help_res.stderr
            assert "usage:" in (help_res.stdout + help_res.stderr).lower()

            version_res = subprocess.run(
                [str(script_path), "--version"],
                capture_output=True,
                text=True,
            )
            assert version_res.returncode == 0, version_res.stderr
            assert __version__ in (version_res.stdout + version_res.stderr)

        # Verify installed auditor-telemetry console script execution in isolated environment
        telemetry_bin = venv_dir / "bin" / "auditor-telemetry"
        telemetry_run = subprocess.run(
            [str(telemetry_bin)],
            capture_output=True,
            text=True,
        )
        assert telemetry_run.returncode == 0, telemetry_run.stderr
        assert telemetry_run.stderr.strip() == ""
        payload = json.loads(telemetry_run.stdout)
        assert "node" in payload
        assert "resources" in payload
        assert payload.get("service", {}).get("name") == "aurora-node-auditor"
        assert payload.get("service", {}).get("version") == __version__

        # Verify installed node-audit console script execution
        audit_bin = venv_dir / "bin" / "node-audit"
        audit_run = subprocess.run(
            [str(audit_bin), "--json"],
            capture_output=True,
            text=True,
        )
        assert audit_run.returncode == 0, audit_run.stderr
        audit_payload = json.loads(audit_run.stdout)
        assert "status" in audit_payload
        assert "resources" in audit_payload
        assert "security" in audit_payload
        assert audit_payload.get("service", {}).get("version") == __version__
