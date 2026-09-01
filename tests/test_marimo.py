"""Tests for great_docs._marimo: marimo notebook integration utilities."""

from __future__ import annotations

import sys
from pathlib import Path

from great_docs._marimo import (
    _FALLBACK_VERSION,
    _ISLANDS_CDN,
    _tag_setup_islands,
    get_islands_head_html,
    islands_runtime_version,
    notebook_source,
    parse_marimo_source,
)


# ---------------------------------------------------------------------------
# islands_runtime_version
# ---------------------------------------------------------------------------


class TestIslandsRuntimeVersion:
    def test_returns_installed_version(self, monkeypatch):
        fake_marimo = type(sys)("marimo")
        fake_marimo.__version__ = "1.2.3"
        monkeypatch.setitem(sys.modules, "marimo", fake_marimo)
        assert islands_runtime_version() == "1.2.3"

    def test_fallback_when_marimo_missing(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "marimo", None)
        assert islands_runtime_version() == _FALLBACK_VERSION


# ---------------------------------------------------------------------------
# get_islands_head_html
# ---------------------------------------------------------------------------


class TestGetIslandsHeadHtml:
    def test_explicit_version(self):
        html = get_islands_head_html(version="0.99.0")
        assert f"{_ISLANDS_CDN}@0.99.0/dist/main.js" in html
        assert f"{_ISLANDS_CDN}@0.99.0/dist/style.css" in html
        assert "<marimo-filename hidden>" in html

    def test_version_none_uses_runtime(self, monkeypatch):
        fake_marimo = type(sys)("marimo")
        fake_marimo.__version__ = "5.6.7"
        monkeypatch.setitem(sys.modules, "marimo", fake_marimo)
        html = get_islands_head_html(version=None)
        assert f"{_ISLANDS_CDN}@5.6.7/dist/main.js" in html

    def test_includes_font_and_katex(self):
        html = get_islands_head_html(version="1.0.0")
        assert "fonts.googleapis.com" in html
        assert "katex" in html


# ---------------------------------------------------------------------------
# _tag_setup_islands
# ---------------------------------------------------------------------------


class TestTagSetupIslands:
    def _island(self, *, reactive=True, empty_output=True, label="cell"):
        reactive_attr = 'data-reactive="true"' if reactive else 'data-reactive="false"'
        if empty_output:
            output = "<marimo-cell-output><span></span></marimo-cell-output>"
        else:
            output = "<marimo-cell-output><span>Hello</span></marimo-cell-output>"
        return f'<marimo-island {reactive_attr} data-app-id="main">{output}</marimo-island>'

    def test_empty_input_returns_empty(self):
        assert _tag_setup_islands("") == ""

    def test_leading_empty_cells_tagged(self):
        html = self._island(reactive=True, empty_output=True)
        result = _tag_setup_islands(html)
        assert 'data-gd-setup="true"' in result

    def test_non_empty_cell_not_tagged(self):
        html = self._island(reactive=True, empty_output=False)
        result = _tag_setup_islands(html)
        assert 'data-gd-setup="true"' not in result

    def test_leading_run_stops_at_first_output(self):
        empty = self._island(reactive=True, empty_output=True)
        non_empty = self._island(reactive=True, empty_output=False)
        trailing_empty = self._island(reactive=True, empty_output=True)
        html = empty + non_empty + trailing_empty
        result = _tag_setup_islands(html)
        count = result.count('data-gd-setup="true"')
        assert count == 1

    def test_non_reactive_island_skipped(self):
        init = self._island(reactive=False, empty_output=True)
        empty = self._island(reactive=True, empty_output=True)
        html = init + empty
        result = _tag_setup_islands(html)
        assert result.count('data-gd-setup="true"') == 1

    def test_text_between_islands_preserved(self):
        html = "<p>Before</p>" + self._island() + "<p>After</p>"
        result = _tag_setup_islands(html)
        assert "<p>Before</p>" in result
        assert "<p>After</p>" in result


# ---------------------------------------------------------------------------
# parse_marimo_source
# ---------------------------------------------------------------------------

SAMPLE_NOTEBOOK = """\
import marimo

app = marimo.App()

@app.cell()
def imports():
    import pandas as pd
    import numpy as np
    return pd, np

@app.cell()
def analysis(pd):
    df = pd.DataFrame({"a": [1, 2, 3]})
    return df

@app.cell()
def empty_cell():
    # just a comment
    return
"""


class TestParseMarimoSource:
    def test_parses_cells(self):
        cells = parse_marimo_source(SAMPLE_NOTEBOOK)
        names = [c["name"] for c in cells]
        assert "imports" in names
        assert "analysis" in names

    def test_strips_return_and_trailing_blanks(self):
        cells = parse_marimo_source(SAMPLE_NOTEBOOK)
        analysis = next(c for c in cells if c["name"] == "analysis")
        assert "return" not in analysis["code"]
        assert not analysis["code"].endswith("\n\n")

    def test_dedents_body(self):
        cells = parse_marimo_source(SAMPLE_NOTEBOOK)
        imports = next(c for c in cells if c["name"] == "imports")
        assert imports["code"].startswith("import pandas")

    def test_empty_source_returns_empty(self):
        assert parse_marimo_source("") == []

    def test_cell_without_return(self):
        src = (
            "import marimo\napp = marimo.App()\n\n"
            "@app.cell()\n"
            "def side_effect():\n"
            "    print('hello')\n"
        )
        cells = parse_marimo_source(src)
        assert len(cells) == 1
        assert cells[0]["name"] == "side_effect"
        assert "print" in cells[0]["code"]

    def test_blank_line_before_return_stripped(self):
        src = (
            "import marimo\napp = marimo.App()\n\n"
            "@app.cell()\n"
            "def with_gap():\n"
            "    x = 1\n"
            "\n"
            "    return x\n"
        )
        cells = parse_marimo_source(src)
        gap_cell = next(c for c in cells if c["name"] == "with_gap")
        assert gap_cell["code"] == "x = 1"

    def test_cell_with_only_return_excluded(self):
        src = "import marimo\napp = marimo.App()\n\n@app.cell()\ndef noop():\n    return\n"
        cells = parse_marimo_source(src)
        names = [c["name"] for c in cells]
        assert "noop" not in names


# ---------------------------------------------------------------------------
# notebook_source
# ---------------------------------------------------------------------------


class TestNotebookSource:
    def test_reads_file_content(self, tmp_path):
        nb = tmp_path / "demo.py"
        nb.write_text("import marimo\n", encoding="utf-8")
        assert notebook_source(nb) == "import marimo\n"
