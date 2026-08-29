"""Tests targeting missed coverage lines in great_docs/_apiref/write.py."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from great_docs._apiref.write import (
    _insert_contents,
    merge_frontmatter,
)


# ---------------------------------------------------------------------------
# merge_frontmatter — unclosed frontmatter raises ValueError
# ---------------------------------------------------------------------------


class TestMergeFrontmatter:
    def test_unclosed_frontmatter_raises(self):
        """Raises ValueError when frontmatter is never closed."""
        content = "---\ntitle: Hello\nNo closing delimiter here.\n"
        with pytest.raises(ValueError, match="never closed"):
            merge_frontmatter(content, {"key": "val"})


# ---------------------------------------------------------------------------
# _insert_contents — sentinel inside dict nested in a list
# ---------------------------------------------------------------------------


class TestInsertContents:
    def test_sentinel_in_dict_nested_in_list(self):
        """Finds sentinel in a dict nested inside a list."""
        structure = [
            "item1",
            {"section": "A", "contents": ["{{ contents }}"]},
        ]
        result = _insert_contents(structure, ["new1", "new2"])
        assert result is True
        assert structure[1]["contents"] == ["new1", "new2"]

    def test_sentinel_in_list_nested_in_list(self):
        """Finds sentinel in a list nested inside a list."""
        structure = [
            "item1",
            ["nested", "{{ contents }}"],
        ]
        result = _insert_contents(structure, ["replaced"])
        assert result is True
        assert structure[1] == ["nested", "replaced"]


# ---------------------------------------------------------------------------
# _page_sidebar_text — page.summary is not None
# ---------------------------------------------------------------------------


class TestPageSidebarText:
    def test_summary_not_none_returns_summary_name(self):
        """When page.summary is set, returns its name."""
        from great_docs._apiref.write import _page_sidebar_text

        page = MagicMock()
        page.summary = MagicMock()
        page.summary.name = "MyWidget"

        result = _page_sidebar_text(page)
        assert result == "MyWidget"


# ---------------------------------------------------------------------------
# _generate_sidebar — second titled section appends current_entry
# ---------------------------------------------------------------------------


class TestGenerateSidebar:
    def test_second_titled_section_appends_previous(self):
        """A second titled section appends the previous current_entry."""
        from great_docs._apiref.content import Page, Section
        from great_docs._apiref.write import _generate_sidebar

        page1 = MagicMock(spec=Page)
        page1.summary = None
        page1.contents = [MagicMock(name="func_a", kind="function")]
        page1.contents[0].name = "func_a"
        page1.contents[0].kind = "function"
        page1.path = "func_a"

        page2 = MagicMock(spec=Page)
        page2.summary = None
        page2.contents = [MagicMock(name="ClassB", kind="class")]
        page2.contents[0].name = "ClassB"
        page2.contents[0].kind = "class"
        page2.path = "ClassB"

        sec1 = MagicMock(spec=Section)
        sec1.title = "Functions"
        sec1.subtitle = None
        sec1.contents = [page1]

        sec2 = MagicMock(spec=Section)
        sec2.title = "Classes"
        sec2.subtitle = None
        sec2.contents = [page2]

        result = _generate_sidebar(
            [sec1, sec2], dir="reference", out_page_suffix=".qmd", sidebar=None
        )

        # Should have two section entries in the sidebar contents
        sidebar_contents = result["website"]["sidebar"][0]["contents"]
        sections = [c for c in sidebar_contents if isinstance(c, dict) and "section" in c]
        assert len(sections) == 2
        assert sections[0]["section"] == "Functions"
        assert sections[1]["section"] == "Classes"


# ---------------------------------------------------------------------------
# write_typing_information — iterates module paths
# ---------------------------------------------------------------------------


class TestWriteTypingInformation:
    def test_iterates_module_paths(self):
        """Calls TypeInformation.write() for each module path."""
        from great_docs._apiref.write import write_typing_information

        mock_api_ref = MagicMock()

        with patch("great_docs._apiref.typing_information.TypeInformation") as MockTI:
            mock_instance = MagicMock()
            MockTI.return_value = mock_instance

            write_typing_information(["pkg.types", "pkg.protocols"], mock_api_ref)

        assert MockTI.call_count == 2
        MockTI.assert_any_call("pkg.types", mock_api_ref)
        MockTI.assert_any_call("pkg.protocols", mock_api_ref)
        assert mock_instance.write.call_count == 2
