"""Tests for post-render transformation functions."""

import importlib.util
import sys
from pathlib import Path

import pytest

# Load the post-render script as a module (it's a standalone script, not a package)
_SCRIPT = Path(__file__).resolve().parent.parent / "great_docs" / "assets" / "post-render.py"


def _load_post_render():
    """Import post-render.py as a module so its functions can be tested."""
    spec = importlib.util.spec_from_file_location("post_render", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    # The script runs top-level code (glob, file I/O) that will fail when not
    # inside a build directory.  We only need the function definitions, so we
    # monkey-patch a few things and catch errors at import time.
    return spec, mod


def _get_functions():
    """Post-render helpers available to focused unit tests"""
    import html as _html
    import os as _os
    import re as _re  # noqa: F811

    source = _SCRIPT.read_text()

    # Stub _t so translated labels fall back to English
    def _t(key: str, fallback: str | None = None) -> str:
        return fallback if fallback is not None else key

    # Build a minimal namespace with the imports the functions need
    ns = {
        "html": _html,
        "os": _os,
        "re": _re,
        "__builtins__": __builtins__,
        "_t": _t,
    }

    # Extract function definitions by finding their source blocks
    funcs_to_extract = [
        "translate_sphinx_roles",
        "_postprocess_markdown_content",
    ]

    for func_name in funcs_to_extract:
        # Find the function in the source
        start = source.find(f"def {func_name}(")
        if start == -1:
            raise RuntimeError(f"Could not find {func_name} in {_SCRIPT}")

        # Find the end of the function (next def at same indent level or EOF)
        rest = source[start:]
        lines = rest.split("\n")
        func_lines = [lines[0]]
        for line in lines[1:]:
            # Stop at next top-level def or class
            if (
                line
                and not line[0].isspace()
                and (line.startswith("def ") or line.startswith("class "))
            ):
                break
            func_lines.append(line)

        func_source = "\n".join(func_lines)
        exec(func_source, ns)

    return (
        ns["translate_sphinx_roles"],
        ns["_postprocess_markdown_content"],
    )


(
    translate_sphinx_roles,
    postprocess_markdown_content,
) = _get_functions()


class TestPostprocessMarkdownContent:
    """Tests for markdown cleanup used by generated .md reference pages."""

    def test_removes_source_anchor_and_converts_links(self):
        md = (
            "Usage\n\n"
            '<a href="https://example.com/src.py#L1" target="_blank" rel="noopener">Source</a>\n\n'
            "The workflow is: "
            '<a href="GreatDocs.install.html#great_docs.GreatDocs.install" class="gdls-link gdls-code">install()</a>'
            " then "
            '<a href="GreatDocs.build.html#great_docs.GreatDocs.build" class="gdls-link gdls-code">build()</a>.\n'
        )

        out = postprocess_markdown_content(md, "reference/GreatDocs.md")

        assert "Source</a>" not in out
        assert "[install()](GreatDocs.install.md#great_docs.GreatDocs.install)" in out
        assert "[build()](GreatDocs.build.md#great_docs.GreatDocs.build)" in out
        assert "<a href=" not in out

    def test_simplifies_parameter_signature_artifact(self):
        md = "`project_path``:`` ``str | None`` ``=`` ``None`  \n"

        out = postprocess_markdown_content(md, "reference/GreatDocs.md")

        assert "`project_path`: `str | None` = `None`" in out
        assert "``:``" not in out

    def test_decodes_html_entities_in_markdown(self):
        """HTML entities from pandoc output should be properly decoded."""
        # Common curly quote entities that can end up in markdown
        md = (
            "# What You&rsquo;ll Learn\n\n"
            "Let&rsquo;s get started!\n\n"
            "He said &ldquo;Hello&rdquo; with a smile.\n"
        )

        out = postprocess_markdown_content(md, "user-guide/intro.md")

        # Should decode and normalize to plain ASCII punctuation
        assert "# What You'll Learn" in out
        assert "Let's get started!" in out
        assert 'He said "Hello" with a smile.' in out
        # Should not contain the original HTML entities
        assert "&rsquo;" not in out
        assert "&ldquo;" not in out
        assert "&rdquo;" not in out

    def test_fixes_mojibake_characters(self):
        """UTF-8 mojibake like the three-char sequence should be fixed."""
        # Mojibake: UTF-8 bytes interpreted as Latin-1
        # U+2019 (') is E2 80 99 in UTF-8, but as Latin-1 chars becomes: U+00E2 U+20AC U+2122
        mojibake_apostrophe = "\u00e2\u20ac\u2122"  # This is what â€™ looks like in Python

        md = f"Great Docs automatically discovers and documents your package{mojibake_apostrophe}s public API."

        out = postprocess_markdown_content(md, "user-guide/intro.md")

        # Should have converted mojibake and normalized punctuation to ASCII apostrophe
        assert "package's public API" in out
        # Should not have the mojibake character
        assert mojibake_apostrophe not in out

    def test_normalizes_user_guide_typography_to_ascii(self):
        """Smart punctuation in prose should be normalized for robust raw markdown display."""
        md = (
            "# What You’ll Learn\n\n"
            "1.  **Installation** – Getting Great Docs set up\n"
            "2.  **Quick Start** – Creating your first documentation site\n\n"
            "Let’s get started!\n"
        )

        out = postprocess_markdown_content(md, "user-guide/introduction.md")

        assert "# What You'll Learn" in out
        assert "**Installation** - Getting Great Docs set up" in out
        assert "**Quick Start** - Creating your first documentation site" in out
        assert "Let's get started!" in out
        assert "’" not in out
        assert "–" not in out


class TestTranslateSphinxRoles:
    """Tests for Sphinx cross-reference role translation."""

    def test_py_exc_with_code_tag(self):
        html = "<p>Raises :py:exc:<code>ValueError</code> on failure.</p>"
        result = translate_sphinx_roles(html)
        assert result == "<p>Raises <code>ValueError</code> on failure.</p>"

    def test_py_class_with_code_tag(self):
        html = "<p>Returns a :py:class:<code>datetime.datetime</code> object.</p>"
        result = translate_sphinx_roles(html)
        assert result == "<p>Returns a <code>datetime.datetime</code> object.</p>"

    def test_py_func_adds_parens(self):
        html = "<p>See :py:func:<code>datetime.tzinfo.fromutc</code>.</p>"
        result = translate_sphinx_roles(html)
        assert result == "<p>See <code>datetime.tzinfo.fromutc()</code>.</p>"

    def test_py_meth_adds_parens(self):
        html = "<p>Uses :py:meth:<code>parser.parse</code> internally.</p>"
        result = translate_sphinx_roles(html)
        assert result == "<p>Uses <code>parser.parse()</code> internally.</p>"

    def test_bare_class_role(self):
        html = "<p>Returns a :class:<code>tzinfo</code> subclass.</p>"
        result = translate_sphinx_roles(html)
        assert result == "<p>Returns a <code>tzinfo</code> subclass.</p>"

    def test_bare_func_role_adds_parens(self):
        html = "<p>See :func:<code>get_object</code> for details.</p>"
        result = translate_sphinx_roles(html)
        assert result == "<p>See <code>get_object()</code> for details.</p>"

    def test_const_role(self):
        html = "<p>:py:const:<code>DEFAULTPARSER</code> is used.</p>"
        result = translate_sphinx_roles(html)
        assert result == "<p><code>DEFAULTPARSER</code> is used.</p>"

    def test_attr_role(self):
        html = "<p>The :attr:<code>name</code> attribute.</p>"
        result = translate_sphinx_roles(html)
        assert result == "<p>The <code>name</code> attribute.</p>"

    def test_mod_role(self):
        html = "<p>Provided by :py:mod:<code>dateutil.tz</code>.</p>"
        result = translate_sphinx_roles(html)
        assert result == "<p>Provided by <code>dateutil.tz</code>.</p>"

    def test_backtick_role_in_pre(self):
        html = "<pre><code>Use :func:`get_zonefile_instance` to retrieve</code></pre>"
        result = translate_sphinx_roles(html)
        assert "<code>get_zonefile_instance()</code>" in result

    def test_backtick_class_no_parens(self):
        html = "<pre><code>:class:`MyClass`</code></pre>"
        result = translate_sphinx_roles(html)
        assert "<code>MyClass</code>" in result
        assert "MyClass()" not in result

    def test_multiple_roles_in_one_line(self):
        html = (
            "<p>Takes a :py:class:<code>datetime</code> and returns "
            "a :py:class:<code>timedelta</code>.</p>"
        )
        result = translate_sphinx_roles(html)
        assert ":py:class:" not in result
        assert "<code>datetime</code>" in result
        assert "<code>timedelta</code>" in result

    def test_no_double_parens(self):
        """If the name already has (), don't add more."""
        html = "<p>See :func:<code>foo()</code>.</p>"
        result = translate_sphinx_roles(html)
        assert result == "<p>See <code>foo()</code>.</p>"

    def test_no_change_for_non_role_text(self):
        html = "<p>This is regular text with <code>code</code>.</p>"
        result = translate_sphinx_roles(html)
        assert result == html

    def test_obj_role(self):
        html = "<p>See :py:obj:<code>some_thing</code>.</p>"
        result = translate_sphinx_roles(html)
        assert result == "<p>See <code>some_thing</code>.</p>"

    def test_data_role(self):
        html = "<p>See :py:data:<code>MY_CONST</code>.</p>"
        result = translate_sphinx_roles(html)
        assert result == "<p>See <code>MY_CONST</code>.</p>"

    def test_type_role(self):
        html = "<p>Is :py:type:<code>int</code>.</p>"
        result = translate_sphinx_roles(html)
        assert result == "<p>Is <code>int</code>.</p>"


def _make_autolink(inventory):
    """Create an autolink function bound to a given inventory."""
    import re as _re

    source = _SCRIPT.read_text()
    ns = {
        "re": _re,
        "__builtins__": __builtins__,
        "_interlinks_inventory": inventory,
        "_CALLABLE_ROLES": {"function", "method"},
    }
    for func_name in ("_make_relative_uri", "_resolve_interlink_name", "autolink_code_references"):
        start = source.find(f"def {func_name}(")
        rest = source[start:]
        lines = rest.split("\n")
        func_lines = [lines[0]]
        for line in lines[1:]:
            if (
                line
                and not line[0].isspace()
                and (line.startswith("def ") or line.startswith("class "))
            ):
                break
            func_lines.append(line)
        exec("\n".join(func_lines), ns)
    return ns["autolink_code_references"]


class TestAutolinkCodeReferences:
    """Tests for autolink_code_references."""

    INVENTORY = {
        "mypackage.MyClass": {"uri": "reference/MyClass.html#mypackage.MyClass", "dispname": "-"},
        "mypackage.my_func": {"uri": "reference/my_func.html#mypackage.my_func", "dispname": "-"},
        "mypackage.utils.helper": {
            "uri": "reference/helper.html#mypackage.utils.helper",
            "dispname": "-",
        },
    }

    def _autolink(self, html):
        fn = _make_autolink(self.INVENTORY)
        return fn(html)

    def test_simple_name_match(self):
        result = self._autolink("<p><code>MyClass</code></p>")
        assert (
            '<a href="MyClass.html#mypackage.MyClass" class="gdls-link gdls-code">MyClass</a>'
            in result
        )

    def test_qualified_name_match(self):
        result = self._autolink("<p><code>mypackage.MyClass</code></p>")
        assert (
            '<a href="MyClass.html#mypackage.MyClass" class="gdls-link gdls-code">mypackage.MyClass</a>'
            in result
        )

    def test_name_with_parens(self):
        result = self._autolink("<p><code>my_func()</code></p>")
        assert (
            '<a href="my_func.html#mypackage.my_func" class="gdls-link gdls-code">my_func()</a>'
            in result
        )

    def test_tilde_shortening(self):
        result = self._autolink("<p><code>~~mypackage.MyClass</code></p>")
        assert (
            '<a href="MyClass.html#mypackage.MyClass" class="gdls-link gdls-code">MyClass</a>'
            in result
        )

    def test_tilde_shortening_with_parens(self):
        result = self._autolink("<p><code>~~mypackage.my_func()</code></p>")
        assert (
            '<a href="my_func.html#mypackage.my_func" class="gdls-link gdls-code">my_func()</a>'
            in result
        )

    def test_tilde_dot_shortening(self):
        result = self._autolink("<p><code>~~.mypackage.MyClass</code></p>")
        assert (
            '<a href="MyClass.html#mypackage.MyClass" class="gdls-link gdls-code">.MyClass</a>'
            in result
        )

    def test_tilde_dot_shortening_with_parens(self):
        result = self._autolink("<p><code>~~.mypackage.my_func()</code></p>")
        assert (
            '<a href="my_func.html#mypackage.my_func" class="gdls-link gdls-code">.my_func()</a>'
            in result
        )

    def test_no_match_left_alone(self):
        result = self._autolink("<p><code>unknown_thing</code></p>")
        assert result == "<p><code>unknown_thing</code></p>"

    def test_code_with_args_not_linked(self):
        result = self._autolink("<p><code>my_func(x=1)</code></p>")
        assert "<a" not in result

    def test_code_with_spaces_not_linked(self):
        result = self._autolink("<p><code>a + b</code></p>")
        assert "<a" not in result

    def test_code_with_operator_not_linked(self):
        result = self._autolink("<p><code>-MyClass</code></p>")
        assert "<a" not in result

    def test_gd_no_link_class_skipped(self):
        result = self._autolink('<p><code class="gd-no-link">MyClass</code></p>')
        assert "<a" not in result

    def test_code_in_pre_not_linked(self):
        result = self._autolink("<pre><code>MyClass</code></pre>")
        assert "<a" not in result

    def test_already_inside_link_not_doubled(self):
        result = self._autolink('<a href="foo.html"><code>MyClass</code></a>')
        # Should not wrap in another <a>
        assert result.count("<a ") == 1

    def test_unresolved_tilde_strips_prefix(self):
        result = self._autolink("<p><code>~~unknown.module.Thing</code></p>")
        assert "<a" not in result
        assert "<code>Thing</code>" in result

    def test_unresolved_tilde_dot_strips_prefix(self):
        result = self._autolink("<p><code>~~.unknown.module.Thing()</code></p>")
        assert "<a" not in result
        assert "<code>.Thing()</code>" in result

    def test_empty_inventory(self):
        fn = _make_autolink({})
        html = "<p><code>MyClass</code></p>"
        assert fn(html) == html


# ── Helpers for page_path–aware GDLS tests ──────────────────────────────────


def _extract_make_relative_uri():
    """Extract _make_relative_uri as a standalone callable."""
    source = _SCRIPT.read_text()
    ns = {"__builtins__": __builtins__}
    start = source.find("def _make_relative_uri(")
    rest = source[start:]
    lines = rest.split("\n")
    func_lines = [lines[0]]
    for line in lines[1:]:
        if (
            line
            and not line[0].isspace()
            and (line.startswith("def ") or line.startswith("class "))
        ):
            break
        func_lines.append(line)
    exec("\n".join(func_lines), ns)
    return ns["_make_relative_uri"]


class TestMakeRelativeUri:
    """Direct unit tests for _make_relative_uri."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.fn = _extract_make_relative_uri()

    def test_none_strips_reference_prefix(self):
        """page_path=None strips reference/ prefix (legacy behaviour)."""
        assert self.fn("reference/Foo.html#anchor", None) == "Foo.html#anchor"

    def test_none_non_reference_uri_unchanged(self):
        """page_path=None with non-reference/ URI returns it as-is."""
        assert self.fn("other/page.html", None) == "other/page.html"

    def test_same_directory(self):
        """URI and page in same directory -> sibling-relative."""
        result = self.fn("reference/Foo.html", "reference/Bar.html")
        assert result == "Foo.html"

    def test_parent_directory(self):
        """URI in reference/, page one level up -> reference/ prefix."""
        result = self.fn("reference/Foo.html", "index.html")
        assert result == "reference/Foo.html"

    def test_sibling_directory(self):
        """URI in reference/, page in user-guide/ -> ../reference/."""
        result = self.fn("reference/Foo.html", "user-guide/intro.html")
        assert result == "../reference/Foo.html"

    def test_deeply_nested_page(self):
        """Page 3 levels deep -> three ../ segments."""
        result = self.fn("reference/Foo.html", "blog/2025/01/post.html")
        assert result == "../../../reference/Foo.html"

    def test_preserves_fragment(self):
        """Fragment (#anchor) is preserved through relpath calculation."""
        result = self.fn("reference/Foo.html#pkg.Foo", "user-guide/intro.html")
        assert result == "../reference/Foo.html#pkg.Foo"

    def test_non_reference_uri_from_subdir(self):
        """Non-reference/ URI also gets correct relative path."""
        result = self.fn("changelog.html", "user-guide/intro.html")
        assert result == "../changelog.html"

    def test_same_file(self):
        """URI pointing to the same file -> just the filename."""
        result = self.fn("user-guide/intro.html", "user-guide/intro.html")
        assert result == "intro.html"


def _make_resolve_interlinks(inventory):
    """Create a resolve_interlinks function bound to a given inventory."""
    import re as _re

    source = _SCRIPT.read_text()
    ns = {
        "re": _re,
        "__builtins__": __builtins__,
        "_interlinks_inventory": inventory,
        "_CALLABLE_ROLES": {"function", "method"},
    }
    for func_name in ("_make_relative_uri", "_resolve_interlink_name", "resolve_interlinks"):
        start = source.find(f"def {func_name}(")
        rest = source[start:]
        lines = rest.split("\n")
        func_lines = [lines[0]]
        for line in lines[1:]:
            if (
                line
                and not line[0].isspace()
                and (line.startswith("def ") or line.startswith("class "))
            ):
                break
            func_lines.append(line)
        exec("\n".join(func_lines), ns)
    return ns["resolve_interlinks"]


def _make_autolink_with_path(inventory):
    """Create an autolink function bound to a given inventory (page_path-aware)."""
    import re as _re

    source = _SCRIPT.read_text()
    ns = {
        "re": _re,
        "__builtins__": __builtins__,
        "_interlinks_inventory": inventory,
        "_CALLABLE_ROLES": {"function", "method"},
    }
    for func_name in (
        "_make_relative_uri",
        "_resolve_interlink_name",
        "autolink_code_references",
    ):
        start = source.find(f"def {func_name}(")
        rest = source[start:]
        lines = rest.split("\n")
        func_lines = [lines[0]]
        for line in lines[1:]:
            if (
                line
                and not line[0].isspace()
                and (line.startswith("def ") or line.startswith("class "))
            ):
                break
            func_lines.append(line)
        exec("\n".join(func_lines), ns)
    return ns["autolink_code_references"]


class TestResolveInterlinksPagePath:
    """Tests for resolve_interlinks with page_path for non-reference pages."""

    INVENTORY = {
        "pkg.Engine": {
            "uri": "reference/Engine.html#pkg.Engine",
            "dispname": "-",
            "role": "class",
        },
        "pkg.execute": {
            "uri": "reference/execute.html#pkg.execute",
            "dispname": "-",
            "role": "function",
        },
    }

    def _resolve(self, html, page_path=None):
        fn = _make_resolve_interlinks(self.INVENTORY)
        return fn(html, page_path=page_path)

    def test_reference_page_strips_prefix(self):
        """On a reference page (page_path=None), strips reference/ prefix."""
        html = '<a href="`~pkg.Engine`"></a>'
        result = self._resolve(html, page_path=None)
        assert 'href="Engine.html#pkg.Engine"' in result

    def test_reference_page_explicit_path(self):
        """On a reference page with explicit path, keeps sibling-relative."""
        html = '<a href="`~pkg.Engine`"></a>'
        result = self._resolve(html, page_path="reference/Connection.html")
        assert 'href="Engine.html#pkg.Engine"' in result

    def test_user_guide_page_relative_path(self):
        """On a user-guide page, produces ../reference/ relative path."""
        html = '<a href="`~pkg.Engine`"></a>'
        result = self._resolve(html, page_path="user-guide/intro.html")
        assert 'href="../reference/Engine.html#pkg.Engine"' in result

    def test_user_guide_subdir_relative_path(self):
        """On a deeper user-guide page, produces ../../reference/ path."""
        html = '<a href="`~pkg.Engine`"></a>'
        result = self._resolve(html, page_path="user-guide/advanced/tips.html")
        assert 'href="../../reference/Engine.html#pkg.Engine"' in result

    def test_root_page_relative_path(self):
        """On the site root (e.g. index.html), reference/ is direct child."""
        html = '<a href="`~pkg.Engine`"></a>'
        result = self._resolve(html, page_path="index.html")
        assert 'href="reference/Engine.html#pkg.Engine"' in result

    def test_callable_gets_parens(self):
        """Functions get () appended when using tilde shortening."""
        html = '<a href="`~pkg.execute`"></a>'
        result = self._resolve(html, page_path="user-guide/intro.html")
        assert "execute()" in result
        assert 'href="../reference/execute.html#pkg.execute"' in result

    def test_full_qualified_display(self):
        """Without tilde, full qualified name is shown."""
        html = '<a href="`pkg.Engine`"></a>'
        result = self._resolve(html, page_path="user-guide/intro.html")
        assert "pkg.Engine" in result
        assert 'href="../reference/Engine.html#pkg.Engine"' in result

    def test_custom_text_preserved(self):
        """Custom link text is preserved regardless of page_path."""
        html = '<a href="`~pkg.Engine`">my custom text</a>'
        result = self._resolve(html, page_path="user-guide/intro.html")
        assert "my custom text" in result
        assert 'href="../reference/Engine.html#pkg.Engine"' in result

    def test_unresolved_left_unchanged(self):
        """Unresolved interlink on non-reference page is left as-is."""
        html = '<a href="`~pkg.Unknown`"></a>'
        result = self._resolve(html, page_path="user-guide/intro.html")
        assert result == html

    def test_multiple_interlinks_in_one_page(self):
        """Multiple interlinks in a single page all resolve independently."""
        html = '<p><a href="`~pkg.Engine`"></a> and <a href="`~pkg.execute`"></a></p>'
        result = self._resolve(html, page_path="user-guide/intro.html")
        assert 'href="../reference/Engine.html#pkg.Engine"' in result
        assert 'href="../reference/execute.html#pkg.execute"' in result
        assert "Engine" in result
        assert "execute()" in result

    def test_empty_inventory_returns_unchanged(self):
        """With empty inventory, content is returned unchanged."""
        fn = _make_resolve_interlinks({})
        html = '<a href="`~pkg.Engine`"></a>'
        assert fn(html, page_path="user-guide/intro.html") == html


class TestAutolinkCodeReferencesPagePath:
    """Tests for autolink_code_references with page_path for non-reference pages."""

    INVENTORY = {
        "pkg.Engine": {
            "uri": "reference/Engine.html#pkg.Engine",
            "dispname": "-",
        },
        "pkg.execute": {
            "uri": "reference/execute.html#pkg.execute",
            "dispname": "-",
        },
    }

    def _autolink(self, html, page_path=None):
        fn = _make_autolink_with_path(self.INVENTORY)
        return fn(html, page_path=page_path)

    def test_reference_page_strips_prefix(self):
        """On a reference page (page_path=None), strips reference/ prefix."""
        result = self._autolink("<p><code>Engine</code></p>", page_path=None)
        assert 'href="Engine.html#pkg.Engine"' in result

    def test_user_guide_relative_path(self):
        """On a user-guide page, produces ../reference/ path."""
        result = self._autolink("<p><code>Engine</code></p>", page_path="user-guide/intro.html")
        assert 'href="../reference/Engine.html#pkg.Engine"' in result

    def test_root_page_relative_path(self):
        """On the site root, reference/ is direct child."""
        result = self._autolink("<p><code>Engine</code></p>", page_path="index.html")
        assert 'href="reference/Engine.html#pkg.Engine"' in result

    def test_deep_subdir_relative_path(self):
        """On a deeply nested page, correct number of ../ segments."""
        result = self._autolink("<p><code>Engine</code></p>", page_path="blog/2025/01/post.html")
        assert 'href="../../../reference/Engine.html#pkg.Engine"' in result

    def test_tilde_shortening_with_path(self):
        """~~ shortening works with page_path."""
        result = self._autolink(
            "<p><code>~~pkg.Engine</code></p>", page_path="user-guide/intro.html"
        )
        assert 'href="../reference/Engine.html#pkg.Engine"' in result
        assert ">Engine</a>" in result

    def test_parens_preserved_with_path(self):
        """Name() display is preserved with correct page_path."""
        result = self._autolink("<p><code>execute()</code></p>", page_path="user-guide/intro.html")
        assert 'href="../reference/execute.html#pkg.execute"' in result
        assert "execute()" in result

    def test_pre_block_protected_with_path(self):
        """Code inside <pre> is NOT autolinked even with page_path."""
        result = self._autolink("<pre><code>Engine</code></pre>", page_path="user-guide/intro.html")
        assert "<a" not in result

    def test_gd_no_link_with_path(self):
        """gd-no-link class still suppresses autolinking with page_path."""
        result = self._autolink(
            '<p><code class="gd-no-link">Engine</code></p>',
            page_path="user-guide/intro.html",
        )
        assert "<a" not in result

    def test_already_inside_link_with_path(self):
        """Code already inside an <a> tag is not double-wrapped."""
        result = self._autolink(
            '<a href="foo.html"><code>Engine</code></a>',
            page_path="user-guide/intro.html",
        )
        assert result.count("<a ") == 1

    def test_unresolved_code_unchanged_with_path(self):
        """Unresolved code on non-reference page stays as plain <code>."""
        result = self._autolink(
            "<p><code>UnknownThing</code></p>",
            page_path="user-guide/intro.html",
        )
        assert "<a" not in result
        assert "<code>UnknownThing</code>" in result

    def test_multiple_codes_in_one_page(self):
        """Multiple code references in one page all resolve."""
        result = self._autolink(
            "<p><code>Engine</code> and <code>execute()</code></p>",
            page_path="user-guide/intro.html",
        )
        assert 'href="../reference/Engine.html#pkg.Engine"' in result
        assert 'href="../reference/execute.html#pkg.execute"' in result


# ---------------------------------------------------------------------------
# fix_script_paths — back-to-top.js path resolution
# ---------------------------------------------------------------------------


class TestFixScriptPathsBackToTop:
    """Verify fix_script_paths handles back-to-top.js in subdirectories."""

    def test_back_to_top_listed_in_fix_script_paths(self):
        """back-to-top.js should appear in the fix_script_paths function body."""
        source = _SCRIPT.read_text()
        # Find the fix_script_paths function
        assert "def fix_script_paths():" in source
        # Find the start of the function
        start = source.find("def fix_script_paths():")
        # Find the next top-level definition after it
        rest = source[start:]
        lines = rest.split("\n")
        func_lines = [lines[0]]
        for line in lines[1:]:
            if line and not line[0].isspace() and not line.startswith("#"):
                break
            func_lines.append(line)
        func_body = "\n".join(func_lines)
        assert "back-to-top.js" in func_body

    def test_back_to_top_path_fix_pattern(self):
        """The fix uses the same old/new replacement pattern as other scripts."""
        source = _SCRIPT.read_text()
        # Verify the exact pattern strings exist
        assert "'<script src=\"back-to-top.js\"></script>'" in source
        assert "back-to-top.js" in source


class TestFixScriptPathsKeyboardNav:
    """Verify fix_script_paths handles keyboard-nav.js in subdirectories."""

    def test_keyboard_nav_listed_in_fix_script_paths(self):
        """keyboard-nav.js should appear in the fix_script_paths function body."""
        source = _SCRIPT.read_text()
        assert "def fix_script_paths():" in source
        start = source.find("def fix_script_paths():")
        rest = source[start:]
        lines = rest.split("\n")
        func_lines = [lines[0]]
        for line in lines[1:]:
            if line and not line[0].isspace() and not line.startswith("#"):
                break
            func_lines.append(line)
        func_body = "\n".join(func_lines)
        assert "keyboard-nav.js" in func_body

    def test_keyboard_nav_path_fix_pattern(self):
        """The fix uses the same old/new replacement pattern as other scripts."""
        source = _SCRIPT.read_text()
        assert "'<script src=\"keyboard-nav.js\"></script>'" in source
        assert "keyboard-nav.js" in source
