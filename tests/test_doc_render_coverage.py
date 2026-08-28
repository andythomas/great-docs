"""Tests targeting great_docs/_apiref/_render/doc.py."""

from __future__ import annotations

import types
from unittest.mock import MagicMock, patch

import griffe as gf

import great_docs._apiref._render.doc as docmod
from great_docs._apiref._render.doc import RenderDoc


def _get_private_cls():
    """Access the name-mangled __RenderDoc class."""
    return vars(docmod)["__RenderDoc"]


# ---------------------------------------------------------------------------
# render_annotation — canonical_path starts with "~"
# ---------------------------------------------------------------------------


class TestRenderAnnotationTildePrefix:
    def test_tilde_prefix_returns_canonical_name(self):
        """When canonical_path starts with '~', returns canonical_name."""
        cls = _get_private_cls()

        # Build an ExprSubscript with a tilde path
        ann = MagicMock(spec=gf.ExprSubscript)
        ann.canonical_name = "InitVar"
        # Not an InitVar subscript — use a plain Expr that has ~ path
        ann2 = MagicMock(spec=gf.Expr)
        ann2.canonical_path = "~some.long.path.MyType"
        ann2.canonical_name = "MyType"
        # isinstance checks: not str, not ExprName, is Expr, not ExprSubscript
        # We need a real-ish annotation that passes isinstance checks

        # Simpler: use a plain ExprName for the non-tilde case
        mock_expr = MagicMock(spec=gf.Expr)
        mock_expr.canonical_path = "~mod.sub.Widget"
        mock_expr.canonical_name = "Widget"
        # Make isinstance(mock_expr, gf.ExprSubscript) return False
        # Make isinstance(mock_expr, gf.ExprName) return False
        # Make isinstance(mock_expr, gf.Expr) return True

        # Create a fake attribute obj with annotation
        fake_attr = MagicMock(spec=gf.Attribute)
        fake_attr.annotation = mock_expr
        fake_attr.kind = gf.Kind("attribute")

        fake_self = types.SimpleNamespace(obj=fake_attr)

        result = cls.__dict__["render_annotation"](fake_self, annotation=mock_expr)
        assert "Widget" in result


# ---------------------------------------------------------------------------
# render_modules_section — returns _suppress_section
# ---------------------------------------------------------------------------


class TestRenderModulesSection:
    def test_modules_section_suppressed(self):
        """render_modules_section returns None."""
        cls = _get_private_cls()
        fake_self = types.SimpleNamespace(_suppress_section=lambda el: None)
        el = MagicMock(spec=gf.DocstringSectionModules)

        result = cls.render_modules_section(fake_self, el)
        assert result is None


# ---------------------------------------------------------------------------
# render_example_fragment — unrecognized fragment returns ""
# ---------------------------------------------------------------------------


class TestRenderExampleFragment:
    def test_unrecognized_fragment_returns_empty(self):
        """When fragment is not ExampleCode or ExampleText, returns ''."""
        cls = _get_private_cls()
        fake_self = types.SimpleNamespace()

        # Transform returns something that's neither ExampleCode nor ExampleText
        with patch("great_docs._apiref._render.doc.transform", return_value="unexpected"):
            result = cls._render_example_fragment(fake_self, MagicMock())

        assert result == ""


# ---------------------------------------------------------------------------
# render_admonition_section — returns description
# ---------------------------------------------------------------------------


class TestRenderAdmonitionSection:
    def test_returns_description(self):
        """render_admonition_section returns el.value.description."""
        cls = _get_private_cls()
        fake_self = types.SimpleNamespace()

        el = MagicMock(spec=gf.DocstringSectionAdmonition)
        el.value = MagicMock()
        el.value.description = "Be careful with this function."

        result = cls.render_admonition_section(fake_self, el)
        assert result == "Be careful with this function."


# ---------------------------------------------------------------------------
# render_warnings_section — returns value
# ---------------------------------------------------------------------------


class TestRenderWarningsSection:
    def test_returns_value(self):
        """render_warnings_section returns el.value."""
        from great_docs._apiref._docstring_sections import DocstringSectionWarnings

        cls = _get_private_cls()
        fake_self = types.SimpleNamespace()

        el = MagicMock(spec=DocstringSectionWarnings)
        el.value = "This may cause data loss."

        result = cls.render_warnings_section(fake_self, el)
        assert result == "This may cause data loss."


# ---------------------------------------------------------------------------
# render_notes_section — returns value
# ---------------------------------------------------------------------------


class TestRenderNotesSection:
    def test_returns_value(self):
        """render_notes_section returns el.value."""
        from great_docs._apiref._docstring_sections import DocstringSectionNotes

        cls = _get_private_cls()
        fake_self = types.SimpleNamespace()

        el = MagicMock(spec=DocstringSectionNotes)
        el.value = "Implementation uses Cython internally."

        result = cls.render_notes_section(fake_self, el)
        assert result == "Implementation uses Cython internally."


# ---------------------------------------------------------------------------
# render_see_also_section — empty line skipped
# ---------------------------------------------------------------------------


class TestRenderSeeAlsoSectionSkipEmpty:
    def test_empty_lines_skipped(self):
        """Empty lines in see_also content are skipped."""
        cls = _get_private_cls()
        fake_self = types.SimpleNamespace()

        el = MagicMock()
        el.value = [("func_a", "Description A")]
        # format_see_also returns content with blank lines between items
        with patch(
            "great_docs._apiref._render.doc.format_see_also",
            return_value="foo:description\n\nbar:other description",
        ):
            result = cls.render_see_also_section(fake_self, el)

        result_str = str(result)

        assert "foo" in result_str
        assert "bar" in result_str


# ---------------------------------------------------------------------------
# source_link — compiled extension returns None
# ---------------------------------------------------------------------------


class TestSourceLinkCompiledExtension:
    def test_so_extension_returns_none(self, monkeypatch):
        """When source path ends with .so, returns None."""
        from great_docs._apiref import _globals

        cls = _get_private_cls()

        monkeypatch.setenv("GITHUB_REPO_URL", "https://github.com/user/repo")
        monkeypatch.setenv("GIT_REF", "main")
        _globals.package_info.cache_clear()

        fake_self = types.SimpleNamespace(
            _source_relative_path=lambda: "mymod.cpython-313-x86_64-linux-gnu.so"
        )

        result = cls.__dict__["source_link"].func(fake_self)

        assert result is None

        _globals.package_info.cache_clear()

    def test_pyd_extension_returns_none(self, monkeypatch):
        """When source path ends with .pyd, returns None."""
        from great_docs._apiref import _globals

        cls = _get_private_cls()

        monkeypatch.setenv("GITHUB_REPO_URL", "https://github.com/user/repo")
        monkeypatch.setenv("GIT_REF", "main")
        _globals.package_info.cache_clear()

        fake_self = types.SimpleNamespace(_source_relative_path=lambda: "mymod.pyd")

        result = cls.__dict__["source_link"].func(fake_self)

        assert result is None

        _globals.package_info.cache_clear()


# ---------------------------------------------------------------------------
# _source_relative_path — ValueError from relative_to
# ---------------------------------------------------------------------------


class TestSourceRelativePathValueError:
    def test_relative_to_raises_value_error(self, monkeypatch):
        """When filepath is not relative to PACKAGE_ROOT, falls through."""
        from great_docs._apiref import _globals

        cls = _get_private_cls()

        monkeypatch.delenv("SOURCE_PATH", raising=False)
        monkeypatch.setenv("PACKAGE_ROOT", "/completely/different/root")
        _globals.package_info.cache_clear()

        obj = types.SimpleNamespace(
            filepath="/unrelated/path/to/mod.py",
            relative_package_filepath="mod.py",
        )
        fake_self = types.SimpleNamespace(obj=obj)

        result = cls.__dict__["_source_relative_path"](fake_self)

        # Falls through to legacy fallback (relative_package_filepath)
        assert result == "mod.py"

        _globals.package_info.cache_clear()
