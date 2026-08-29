"""Tests targeting missed coverage lines in _harper.py, _apiref/spec.py, _apiref/_format.py."""

from __future__ import annotations

import dataclasses
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# great_docs/_harper.py
# ---------------------------------------------------------------------------


class TestRunHarper:
    def test_only_rules_extends_cmd(self):
        """When only_rules is provided, --only flag is added."""
        from great_docs._harper import run_harper

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="[]", stderr="")
            run_harper(
                [Path("test.md")],
                only_rules=["spelling", "grammar"],
                harper_path="/usr/bin/harper-cli",
            )

        cmd = mock_run.call_args[0][0]
        assert "--only" in cmd
        idx = cmd.index("--only")
        assert cmd[idx + 1] == "spelling,grammar"

    def test_oserror_raises_harper_error(self):
        """OSError from subprocess raises HarperError."""
        from great_docs._harper import HarperError, run_harper

        with patch("subprocess.run", side_effect=OSError("No such file")):
            with pytest.raises(HarperError, match="Failed to run harper-cli"):
                run_harper(
                    [Path("test.md")],
                    harper_path="/nonexistent/harper-cli",
                )

    def test_json_decode_error_raises_harper_error(self):
        """Invalid JSON output raises HarperError."""
        from great_docs._harper import HarperError, run_harper

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="not valid json {{{", stderr="")
            with pytest.raises(HarperError, match="Failed to parse"):
                run_harper(
                    [Path("test.md")],
                    harper_path="/usr/bin/harper-cli",
                )


# ---------------------------------------------------------------------------
# great_docs/_apiref/spec.py
# ---------------------------------------------------------------------------


class TestSpecOptionsDefaultFactory:
    def test_default_factory_field_initialized(self):
        """Fields with default_factory are initialized when not passed."""
        from great_docs._apiref.spec import SpecOptions

        @dataclass(init=False)
        class TestSpec(SpecOptions):
            items: list = field(default_factory=list)

        obj = TestSpec()
        assert obj.items == []
        assert isinstance(obj.items, list)


class TestSpecSectionValidation:
    def test_empty_section_raises(self):
        """Section without title, subtitle, or contents raises."""
        from great_docs._apiref.spec import SpecSection

        with pytest.raises(ValueError, match="must specify a title"):
            SpecSection()

    def test_both_title_and_subtitle_raises(self):
        """Section with both title and subtitle raises."""
        from great_docs._apiref.spec import SpecSection

        with pytest.raises(ValueError, match="cannot specify both"):
            SpecSection(title="Functions", subtitle="Utilities")


# ---------------------------------------------------------------------------
# great_docs/_apiref/_format.py
# ---------------------------------------------------------------------------


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
            # Clear lru_cache so the patched value takes effect
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
