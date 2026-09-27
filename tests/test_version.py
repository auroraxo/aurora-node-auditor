"""Tests for auditor.version module."""

import unittest
from unittest.mock import patch

from auditor.version import get_version, _UNKNOWN


class TestVersionResolution(unittest.TestCase):
    def test_explicit_primary_wins(self):
        self.assertEqual(get_version(primary="9.9.9"), "9.9.9")

    def test_explicit_none_falls_through_to_package_version(self):
        from auditor import __version__
        self.assertEqual(get_version(), __version__)

    def test_fallback_to_importlib_metadata(self):
        # Package import fails, importlib metadata succeeds
        with patch.dict("sys.modules", {"auditor": None}):
            with patch("importlib.metadata.version", return_value="1.2.3"):
                self.assertEqual(get_version(), "1.2.3")

    def test_fallback_to_unknown_when_everything_fails(self):
        with patch.dict("sys.modules", {"auditor": None}):
            with patch("importlib.metadata.version", side_effect=Exception("no dist")):
                self.assertEqual(get_version(), _UNKNOWN)
