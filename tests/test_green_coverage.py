"""Tests targeting remaining missed coverage lines across multiple green-priority files."""

from __future__ import annotations

import types
from unittest.mock import MagicMock, patch

import griffe as gf
import pytest


# ---------------------------------------------------------------------------
# great_docs/_apiref/_render/mixin_call.py — lines 64, 155, 175
# ---------------------------------------------------------------------------


class TestMixinCallReceives:
    def test_render_receives_section(self):
        """render_receives_section delegates to render_definition_items (line 64)."""
        import great_docs._apiref._render.mixin_call as mod

        cls = vars(mod)["__RenderDocCallMixin"]
        fake_self = types.SimpleNamespace(
            render_definition_items=lambda el: "rendered"
        )
        el = MagicMock(spec=gf.DocstringSectionReceives)
        result = cls.render_receives_section(fake_self, el)
        assert result == "rendered"


class TestMixinCallOverloadNoParams:
    def test_overload_without_parameters_skipped(self):
        """Overload entry without parameters attr is skipped (line 155)."""
        import great_docs._apiref._render.mixin_call as mod

        cls = vars(mod)["__RenderDocCallMixin"]
        fake_obj = MagicMock()
        fake_obj.kind = "function"
        fake_self = types.SimpleNamespace(obj=fake_obj)

        ov_bad = MagicMock(spec=[])  # no 'parameters' attr

        result = cls._render_overload_signatures(fake_self, "func", [ov_bad])
        result_str = str(result)
        assert "func()" in result_str


# ---------------------------------------------------------------------------
# great_docs/_apiref/_render/mixin_members.py — lines 152, 198, 248
# ---------------------------------------------------------------------------


class TestMixinMembersExcludeStr:
    def test_attribute_exclude_as_string(self):
        """When EXCLUSIONS.attributes returns a string, it's wrapped in tuple (line 152)."""
        import great_docs._apiref._render.mixin_members as mod

        cls = vars(mod)["__RenderDocMembersMixin"]
        fake_obj = MagicMock()
        fake_obj.path = "pkg.MyClass"
        mock_doc = MagicMock()
        mock_doc.members = []
        fake_self = types.SimpleNamespace(obj=fake_obj, doc=mock_doc)

        mock_exclusions = MagicMock()
        mock_exclusions.attributes = {"pkg.MyClass": "_internal"}

        with patch("great_docs._apiref._globals.EXCLUSIONS", mock_exclusions):
            result = cls.attributes.func(fake_self)

        assert result == []

    def test_function_exclude_as_string(self):
        """When EXCLUSIONS.functions returns a string, it's wrapped in tuple (line 198)."""
        import great_docs._apiref._render.mixin_members as mod

        cls = vars(mod)["__RenderDocMembersMixin"]
        fake_obj = MagicMock()
        fake_obj.path = "pkg.MyClass"
        mock_doc = MagicMock()
        mock_doc.members = []
        fake_self = types.SimpleNamespace(obj=fake_obj, doc=mock_doc)

        mock_exclusions = MagicMock()
        mock_exclusions.functions = {"pkg.MyClass": "_helper"}

        with patch("great_docs._apiref._globals.EXCLUSIONS", mock_exclusions):
            result = cls.functions.func(fake_self)

        assert result == []

    def test_class_member_pages_exclude_as_string(self):
        """When EXCLUSIONS.classes returns a string (class_member_pages), it's wrapped in tuple (line 248)."""
        import great_docs._apiref._render.mixin_members as mod

        cls = vars(mod)["__RenderDocMembersMixin"]
        fake_obj = MagicMock()
        fake_obj.path = "pkg.Outer"
        mock_doc = MagicMock()
        mock_doc.members = []
        fake_self = types.SimpleNamespace(obj=fake_obj, doc=mock_doc)

        mock_exclusions = MagicMock()
        mock_exclusions.classes = {"pkg.Outer": "InnerPrivate"}

        with patch("great_docs._apiref._globals.EXCLUSIONS", mock_exclusions):
            result = cls.class_member_pages.func(fake_self)

        assert result == []


# ---------------------------------------------------------------------------
# great_docs/_apiref/api_reference.py — lines 277, 279, 286
# ---------------------------------------------------------------------------


class TestMemberName:
    def test_page_returns_first_content_name(self):
        """Page node returns contents[0].name (line 277)."""
        from great_docs._apiref.api_reference import _member_name
        from great_docs._apiref.content import Page

        page = MagicMock(spec=Page)
        page.contents = [MagicMock(name="my_func")]
        page.contents[0].name = "my_func"

        assert _member_name(page) == "my_func"

    def test_link_returns_short_name(self):
        """Link node returns last part of dotted name (line 279)."""
        from great_docs._apiref.api_reference import _member_name
        from great_docs._apiref.content import Link

        link = MagicMock(spec=Link)
        link.name = "pkg.sub.Widget"

        assert _member_name(link) == "Widget"


class TestMemberChildren:
    def test_page_returns_first_content_members(self):
        """Page node returns contents[0].members (line 286)."""
        from great_docs._apiref.api_reference import _member_children
        from great_docs._apiref.content import Page

        inner = MagicMock()
        inner.members = ["child1", "child2"]
        page = MagicMock(spec=Page)
        page.contents = [inner]

        assert _member_children(page) == ["child1", "child2"]


# ---------------------------------------------------------------------------
# great_docs/_builtin/directives/_callouts.py — lines 199, 201, 205
# ---------------------------------------------------------------------------


class TestCollectIndentedBody:
    def test_blank_lines_before_end_of_input(self):
        """Blank lines followed by end-of-input breaks collection (lines 199, 201)."""
        from great_docs._builtin.directives._callouts import collect_indented_body

        lines = [
            "    indented content",
            "",
            "",
        ]
        body, idx = collect_indented_body(lines, start=0, directive_indent=0)
        assert body == ["    indented content"]

    def test_blank_lines_before_dedented_content(self):
        """Blank lines followed by dedented content breaks (line 205)."""
        from great_docs._builtin.directives._callouts import collect_indented_body

        lines = [
            "    indented content",
            "",
            "not indented anymore",
        ]
        body, idx = collect_indented_body(lines, start=0, directive_indent=0)
        assert body == ["    indented content"]


# ---------------------------------------------------------------------------
# great_docs/_go_cli.py — lines 50, 293, 353
# ---------------------------------------------------------------------------


class TestDetectGoProject:
    def test_go_mod_no_module_path_returns_none(self, tmp_path):
        """When go.mod has no module line, returns None (line 50)."""
        from great_docs._go_cli import detect_go_cli_project

        go_mod = tmp_path / "go.mod"
        go_mod.write_text("go 1.21\n", encoding="utf-8")

        assert detect_go_cli_project(tmp_path) is None


class TestParseCobraFlag:
    def test_non_type_token_prepended_to_description(self):
        """When token after name isn't a known type, it joins description (line 293)."""
        from great_docs._go_cli import _parse_cobra_flag

        result = _parse_cobra_flag("  -f, --flag   word  some description")
        assert result is not None
        assert "word" in result["help"]




# ---------------------------------------------------------------------------
# great_docs/pandoc/inlines.py — lines 62, 76, 182
# ---------------------------------------------------------------------------


class TestInlinesEmpty:
    def test_inlines_empty_returns_empty(self):
        """Inlines with no elements returns '' (line 62)."""
        from great_docs.pandoc.inlines import Inlines

        assert str(Inlines(elements=None)) == ""
        assert str(Inlines(elements=[])) == ""

    def test_inlines0_empty_returns_empty(self):
        """Inlines0 with no elements returns '' (line 76)."""
        from great_docs.pandoc.inlines import Inlines0

        assert str(Inlines0(elements=None)) == ""
        assert str(Inlines0(elements=[])) == ""


class TestInlineContentToStrError:
    def test_unsupported_type_raises(self):
        """Unsupported type raises TypeError (line 182)."""
        from great_docs.pandoc.inlines import inlinecontent_to_str

        with pytest.raises(TypeError, match="Could not process type"):
            inlinecontent_to_str(12345)


# ---------------------------------------------------------------------------
# great_docs/_tbl_preview.py — lines 379-380
# ---------------------------------------------------------------------------


class TestFromFeatherPandasFallback:
    def test_pandas_fallback_reads_feather(self, tmp_path):
        """When polars unavailable, falls back to pandas (lines 379-380)."""
        import sys

        from great_docs._tbl_preview import _from_feather

        mock_df = MagicMock()
        mock_from_pandas = MagicMock(
            return_value=(["col1"], ["int64"], [[1]], 1, "feather")
        )
        mock_pd = MagicMock()
        mock_pd.read_feather = MagicMock(return_value=mock_df)

        with (
            patch.dict(sys.modules, {"polars": None, "pandas": mock_pd}),
            patch("great_docs._tbl_preview._from_pandas", mock_from_pandas),
        ):
            result = _from_feather(tmp_path / "data.feather")

        assert result[0] == ["col1"]


# ---------------------------------------------------------------------------
# great_docs/pandoc/blocks.py — line 257
# ---------------------------------------------------------------------------


class TestBlockcontentToStrItemsEmpty:
    def test_block_with_empty_as_list_item(self):
        """fmt('', pfx) returns '' inside sequence iteration (line 257)."""
        from great_docs.pandoc.blocks import Block, blockcontent_to_str_items

        mock_block = MagicMock(spec=Block)
        mock_block.as_list_item = ""
        result = blockcontent_to_str_items([mock_block], "bullet")
        assert result == ""
