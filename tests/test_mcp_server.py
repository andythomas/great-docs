"""Tests for mcp.py server helpers and tool handlers."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from great_docs._utils import QUARTO_YML_HEADER
from great_docs.mcp import (
    _build_output_dirs,
    _get_project_root,
    _handle_add_page,
    _handle_config,
    _handle_preview,
    _handle_status,
    call_tool,
    list_prompts,
    list_tools,
)


# ---------------------------------------------------------------------------
# _get_project_root
# ---------------------------------------------------------------------------


class TestGetProjectRoot:
    def test_returns_resolved_path_when_given(self, tmp_path: Path):
        result = _get_project_root(str(tmp_path))
        assert result == tmp_path.resolve()

    def test_raises_when_path_does_not_exist(self, tmp_path: Path):
        missing = tmp_path / "nonexistent"
        with pytest.raises(FileNotFoundError):
            _get_project_root(str(missing))

    def test_returns_cwd_when_no_path(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        monkeypatch.chdir(tmp_path)
        result = _get_project_root(None)
        assert result == tmp_path


# ---------------------------------------------------------------------------
# _build_output_dirs
# ---------------------------------------------------------------------------


class TestBuildOutputDirs:
    def _mark_dir(self, path: Path) -> None:
        path.mkdir(parents=True)
        (path / "_quarto.yml").write_text(
            QUARTO_YML_HEADER + "project:\n  type: website\n", encoding="utf-8"
        )

    def test_empty_when_no_build_dirs(self, tmp_path: Path):
        assert _build_output_dirs(tmp_path) == []

    def test_includes_great_docs_dir_first(self, tmp_path: Path):
        (tmp_path / "great-docs").mkdir()
        result = _build_output_dirs(tmp_path)
        assert result[0].name == "great-docs"

    def test_includes_versioned_siblings_after_current(self, tmp_path: Path):
        (tmp_path / "great-docs").mkdir()
        self._mark_dir(tmp_path / "great-docs-0.1")
        result = _build_output_dirs(tmp_path)
        names = [d.name for d in result]
        assert names[0] == "great-docs"
        assert "great-docs-0.1" in names

    def test_only_sibling_dirs_no_current(self, tmp_path: Path):
        self._mark_dir(tmp_path / "great-docs-0.1")
        result = _build_output_dirs(tmp_path)
        assert any(d.name == "great-docs-0.1" for d in result)


# ---------------------------------------------------------------------------
# list_tools
# ---------------------------------------------------------------------------


class TestListTools:
    def test_returns_all_expected_tool_names(self):
        tools = asyncio.run(list_tools())
        names = {t.name for t in tools}
        expected = {
            "gd_build",
            "gd_preview",
            "gd_scan",
            "gd_lint",
            "gd_config",
            "gd_status",
            "gd_add_page",
            "gd_api_diff",
        }
        assert expected == names

    def test_all_tools_have_descriptions(self):
        tools = asyncio.run(list_tools())
        for tool in tools:
            assert tool.description, f"{tool.name} has no description"

    def test_all_tools_have_input_schemas(self):
        tools = asyncio.run(list_tools())
        for tool in tools:
            schema = getattr(tool, "input_schema", None) or getattr(tool, "inputSchema", None)
            assert schema is not None, f"{tool.name} has no input schema"


# ---------------------------------------------------------------------------
# list_prompts
# ---------------------------------------------------------------------------


class TestListPrompts:
    def test_returns_prompts(self):
        prompts = asyncio.run(list_prompts())
        assert len(prompts) > 0

    def test_prompts_have_names_and_descriptions(self):
        prompts = asyncio.run(list_prompts())
        for p in prompts:
            assert p.name
            assert p.description


# ---------------------------------------------------------------------------
# call_tool
# ---------------------------------------------------------------------------


class TestCallTool:
    def test_unknown_tool_returns_error_text(self):
        result = asyncio.run(call_tool("no_such_tool", {}))
        assert len(result) == 1
        assert "Unknown tool" in result[0].text

    def test_exception_in_handler_returns_error_text(self):
        with patch("great_docs.mcp._handle_build", side_effect=RuntimeError("boom")):
            result = asyncio.run(call_tool("gd_build", {}))
        assert "Error" in result[0].text
        assert "boom" in result[0].text


# ---------------------------------------------------------------------------
# _handle_preview
# ---------------------------------------------------------------------------


class TestHandlePreview:
    def test_no_build_dir_returns_instruction(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.chdir(tmp_path)
        result = asyncio.run(_handle_preview({}))
        assert len(result) == 1
        assert "gd_build" in result[0].text

    def test_with_build_dir_returns_url(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        (tmp_path / "great-docs").mkdir()
        monkeypatch.chdir(tmp_path)
        result = asyncio.run(_handle_preview({"port": 4321}))
        assert "4321" in result[0].text
        assert "http://localhost" in result[0].text


# ---------------------------------------------------------------------------
# _handle_config
# ---------------------------------------------------------------------------


class TestHandleConfig:
    def test_show_config_when_file_missing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        result = asyncio.run(_handle_config({}))
        assert "great-docs.yml" in result[0].text

    def test_show_config_returns_yaml_content(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        (tmp_path / "great-docs.yml").write_text("project:\n  name: test\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        result = asyncio.run(_handle_config({}))
        assert "project:" in result[0].text

    def test_generate_when_config_already_exists(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        (tmp_path / "great-docs.yml").write_text("existing: true\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        result = asyncio.run(_handle_config({"generate": True}))
        assert "already exists" in result[0].text

    def test_generate_creates_config(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        mock_docs = MagicMock()
        with patch("great_docs.mcp._get_great_docs", return_value=mock_docs):
            result = asyncio.run(_handle_config({"generate": True}))
        mock_docs.install.assert_called_once()
        assert "Generated" in result[0].text


# ---------------------------------------------------------------------------
# _handle_status
# ---------------------------------------------------------------------------


class TestHandleStatus:
    def test_no_config_shows_not_initialized(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        result = asyncio.run(_handle_status({}))
        assert "not initialized" in result[0].text

    def test_with_config_shows_configuration_checkmark(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        (tmp_path / "great-docs.yml").write_text("project:\n  name: test\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        mock_docs = MagicMock()
        mock_docs._detect_package_name.return_value = "mypackage"
        mock_docs._config.cli_enabled = False
        mock_docs._config.mcp_enabled = False
        mock_docs._config.__getitem__ = lambda self, key: (
            [] if key in ("user_guide", "versions") else None
        )
        mock_docs._config.sections = []
        with patch("great_docs.mcp._get_great_docs", return_value=mock_docs):
            result = asyncio.run(_handle_status({}))
        assert "✓" in result[0].text

    def test_shows_build_directories_when_present(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        (tmp_path / "great-docs").mkdir()
        monkeypatch.chdir(tmp_path)
        result = asyncio.run(_handle_status({}))
        assert "great-docs" in result[0].text

    def test_no_build_shows_run_message(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        result = asyncio.run(_handle_status({}))
        assert "gd_build" in result[0].text


# ---------------------------------------------------------------------------
# _handle_add_page
# ---------------------------------------------------------------------------


class TestHandleAddPage:
    def test_creates_user_guide_page(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        result = asyncio.run(_handle_add_page({"title": "My Guide"}))
        assert (tmp_path / "user_guide" / "my-guide.qmd").exists()
        assert "Created page" in result[0].text

    def test_creates_recipes_page(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        asyncio.run(_handle_add_page({"title": "Quick Recipe", "section": "recipes"}))
        assert (tmp_path / "recipes" / "quick-recipe.qmd").exists()

    def test_creates_custom_page(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        asyncio.run(_handle_add_page({"title": "Special Page", "section": "custom"}))
        assert (tmp_path / "custom" / "special-page.qmd").exists()

    def test_explicit_filename_used(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        asyncio.run(_handle_add_page({"title": "My Title", "filename": "explicit-name"}))
        assert (tmp_path / "user_guide" / "explicit-name.qmd").exists()

    def test_page_already_exists_returns_message(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "user_guide").mkdir()
        (tmp_path / "user_guide" / "my-guide.qmd").write_text("existing", encoding="utf-8")
        result = asyncio.run(_handle_add_page({"title": "My Guide"}))
        assert "already exists" in result[0].text

    def test_page_content_includes_title_frontmatter(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.chdir(tmp_path)
        asyncio.run(_handle_add_page({"title": "Hello World"}))
        content = (tmp_path / "user_guide" / "hello-world.qmd").read_text(encoding="utf-8")
        assert 'title: "Hello World"' in content

    def test_initial_content_written_to_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.chdir(tmp_path)
        asyncio.run(_handle_add_page({"title": "Tutorial", "content": "## Step 1\nDo this."}))
        content = (tmp_path / "user_guide" / "tutorial.qmd").read_text(encoding="utf-8")
        assert "## Step 1" in content
