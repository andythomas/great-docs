import textwrap

import griffe as gf

from great_docs._builtin.directives._seealso import add_seealso


def _obj(doc: str) -> gf.Function:
    """Build a griffe object carrying a numpy-parsed docstring for `doc`"""
    fn = gf.Function("f")
    fn.docstring = gf.Docstring(textwrap.dedent(doc), lineno=1, parent=fn, parser="numpy")
    return fn


def _see_also(
    sections: list[gf.DocstringSection],
) -> gf.DocstringSectionAdmonition | None:
    """Return the See Also admonition from a parsed section list"""
    for section in sections:
        if isinstance(section, gf.DocstringSectionAdmonition) and (
            (section.title or "").lower() == "see also"
        ):
            return section
    return None


def test_seealso_only_injects_section():
    obj = _obj(
        """
        Summary.

        %seealso foo : does foo, bar
        """
    )
    sections = list(obj.docstring.parsed)
    result = add_seealso(obj, sections)

    assert result is sections
    assert "%seealso" not in obj.docstring.value
    section = _see_also(result)
    assert section is not None
    assert section.value.contents == "foo : does foo\nbar"


def test_multiple_seealso_directives_are_combined():
    obj = _obj(
        """
        Summary.

        %seealso foo : does foo
        %seealso bar, baz : does baz
        """
    )
    sections = add_seealso(obj, list(obj.docstring.parsed))

    assert "%seealso" not in obj.docstring.value
    section = _see_also(sections)
    assert section is not None
    assert section.value.contents == "foo : does foo\nbar\nbaz : does baz"


def test_bare_seealso_does_not_consume_following_content():
    obj = _obj(
        """
        Summary.

        %seealso
        Important prose.
        """
    )
    sections = add_seealso(obj, list(obj.docstring.parsed))

    assert "%seealso" not in obj.docstring.value
    assert "Important prose." in obj.docstring.value
    assert all("%seealso" not in str(section.value) for section in sections)


def test_seealso_deduplicates_repeated_new_entries():
    obj = _obj(
        """
        Summary.

        %seealso foo : first, foo : second
        %seealso bar, bar
        """
    )
    sections = add_seealso(obj, list(obj.docstring.parsed))

    section = _see_also(sections)
    assert section is not None
    assert section.value.contents == "foo : first\nbar"


def test_seealso_merges_into_native_and_dedups():
    obj = _obj(
        """
        Summary.

        %seealso bar : new bar, foo : dup foo

        See Also
        --------
        foo : native desc
        """
    )
    sections = add_seealso(obj, list(obj.docstring.parsed))
    see_also_sections = [
        s
        for s in sections
        if isinstance(s, gf.DocstringSectionAdmonition) and (s.title or "").lower() == "see also"
    ]
    # A single merged section, native entry kept, `foo` not duplicated.
    assert len(see_also_sections) == 1
    contents = see_also_sections[0].value.contents
    assert "foo : native desc" in contents
    assert "bar : new bar" in contents
    assert contents.count("foo") == 1


def test_no_seealso_leaves_docstring_untouched():
    obj = _obj(
        """
        Summary.

        Parameters
        ----------
        x : int
        """
    )
    before = obj.docstring.value
    sections = list(obj.docstring.parsed)
    result = add_seealso(obj, sections)

    assert result is sections
    assert obj.docstring.value == before
    assert _see_also(result) is None


def test_add_seealso_registers_on_import():
    from great_docs.hooks import _docstring_parsed

    assert add_seealso in _docstring_parsed.REGISTRY


def test_nodoc_and_seealso_object_is_dropped():
    from great_docs.hooks._object_resolved import emit_object_resolved

    obj = _obj(
        """
        Internal.

        %nodoc
        %seealso foo
        """
    )
    assert emit_object_resolved(obj) is None


def test_seealso_preserves_unknown_sections_and_order():
    obj = _obj(
        """
        Summary.

        %seealso target
        """
    )
    first = gf.DocstringSectionText("Summary.\n\n%seealso target")
    unknown = gf.DocstringSectionAdmonition(kind="custom", text="Keep.", title="Custom")
    sections: list[gf.DocstringSection] = [first, unknown]

    result = add_seealso(obj, sections)

    assert result[0] is first
    assert result[1] is unknown
    assert _see_also(result) is result[2]


def test_seealso_is_idempotent():
    obj = _obj(
        """
        Summary.

        %seealso target : Related.
        """
    )
    sections = add_seealso(obj, list(obj.docstring.parsed))

    result = add_seealso(obj, sections)

    section = _see_also(result)
    assert section is not None
    assert section.value.contents == "target : Related."
