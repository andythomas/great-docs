"""Tests for great_docs._apiref._format."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestFormatName:
    def test_relative_format(self):
        """'relative' format strips the first path component."""
        from great_docs._apiref._format import format_name

        doc = MagicMock()
        doc.name = "my_func"
        obj = MagicMock()
        obj.path = "pkg.submod.my_func"
        doc.obj = obj

        result = format_name(doc, "relative")
        assert result == "submod.my_func"


class TestFormatStr:
    def test_no_ruff_returns_source(self):
        """When HAS_RUFF is False, returns source unchanged."""
        from great_docs._apiref._format import format_str

        with patch("great_docs._apiref._format.HAS_RUFF", False):
            format_str.cache_clear()
            result = format_str("x=1")

        format_str.cache_clear()
        assert result == "x=1"

    def test_ruff_failure_raises_runtime_error(self):
        """When ruff returns non-zero, raises RuntimeError."""
        from great_docs._apiref._format import format_str

        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stderr = "syntax error in input"

        with (
            patch("great_docs._apiref._format.HAS_RUFF", True),
            patch("subprocess.run", return_value=mock_proc),
        ):
            format_str.cache_clear()
            with pytest.raises(RuntimeError, match="syntax error"):
                format_str("def broken(")

        format_str.cache_clear()
