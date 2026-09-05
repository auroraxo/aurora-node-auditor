"""Tests for CLI parsing and entry point."""

import sys
from auditor.server import build_parser


def test_cli_parser_defaults():
    parser = build_parser()
    args = parser.parse_args([])
    assert args.host == "127.0.0.1"
    assert args.port == 8787


def test_cli_parser_custom_args():
    parser = build_parser()
    args = parser.parse_args(["--host", "0.0.0.0", "--port", "9090"])
    assert args.host == "0.0.0.0"
    assert args.port == 9090


def test_cli_version(capsys):
    parser = build_parser()
    try:
        parser.parse_args(["--version"])
    except SystemExit as exc:
        assert exc.code == 0
    captured = capsys.readouterr()
    assert "0.1.0" in captured.out or "0.1.0" in captured.err
