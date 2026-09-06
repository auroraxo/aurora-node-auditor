"""Tests for CLI parsing and entry points."""

import json

from auditor import __version__
from auditor.server import build_parser as build_server_parser
from auditor.telemetry import build_parser as build_telemetry_parser, main as telemetry_main


def test_server_cli_parser_defaults():
    parser = build_server_parser()
    args = parser.parse_args([])
    assert args.host == "127.0.0.1"
    assert args.port == 8787


def test_server_cli_parser_custom_args():
    parser = build_server_parser()
    args = parser.parse_args(["--host", "0.0.0.0", "--port", "9090"])
    assert args.host == "0.0.0.0"
    assert args.port == 9090


def test_server_cli_version(capsys):
    parser = build_server_parser()
    try:
        parser.parse_args(["--version"])
    except SystemExit as exc:
        assert exc.code == 0
    captured = capsys.readouterr()
    assert __version__ in captured.out or __version__ in captured.err


def test_telemetry_cli_parser_help(capsys):
    parser = build_telemetry_parser()
    try:
        parser.parse_args(["--help"])
    except SystemExit as exc:
        assert exc.code == 0
    captured = capsys.readouterr()
    assert "telemetry" in captured.out.lower() or "usage:" in captured.out.lower()


def test_telemetry_cli_version(capsys):
    parser = build_telemetry_parser()
    try:
        parser.parse_args(["--version"])
    except SystemExit as exc:
        assert exc.code == 0
    captured = capsys.readouterr()
    assert __version__ in captured.out or __version__ in captured.err


def test_telemetry_cli_main_output(capsys):
    telemetry_main([])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert "node" in payload
    assert "resources" in payload
    assert "service" in payload
    assert payload["service"]["name"] == "aurora-node-auditor"
    assert payload["service"]["version"] == __version__
