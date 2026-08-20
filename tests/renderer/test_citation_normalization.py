import griffe as gf
import pytest

from great_docs._builtin.normalization._citations import normalize_citations

_PARSERS = ("numpy", "google", "sphinx")


def _function(text: str, parser: str) -> gf.Function:
    """Build a function whose docstring uses the selected parser"""
    obj = gf.Function("process")
    obj.docstring = gf.Docstring("", parent=obj, parser=parser)
    obj.docstring.value = text
    return obj


def _normalized(text: str, parser: str) -> str:
    """Return the docstring text after citation normalisation"""
    result = normalize_citations(_function(text, parser))
    assert result.docstring is not None
    return result.docstring.value


def _normalized_for(name: str, text: str, parser: str) -> str:
    """Return normalised docstring text for an object with the given name"""
    obj = gf.Function(name)
    obj.docstring = gf.Docstring("", parent=obj, parser=parser)
    obj.docstring.value = text
    result = normalize_citations(obj)
    assert result.docstring is not None
    return result.docstring.value


@pytest.mark.parametrize("parser", _PARSERS)
def test_citation_converts_under_every_parser(parser: str):
    """
    Verify every parser converts numbered citation markers

    Numbered citation conversion is parser-independent.
    """
    source = '.. [1] Hoare, C.A.R. (1961). "Algorithm 64: Quicksort."'
    expected = '1. []{#cite-process-1}Hoare, C.A.R. (1961). "Algorithm 64: Quicksort."'
    assert _normalized(source, parser) == expected


@pytest.mark.parametrize("parser", _PARSERS)
def test_wrapped_citation_joins_onto_one_line(parser: str):
    """Verify an indented continuation joins its citation"""
    source = '.. [1] Hoare, C.A.R. (1961). "Algorithm 64: Quicksort."\n   Communications of the ACM, 4(7), 321.'
    expected = '1. []{#cite-process-1}Hoare, C.A.R. (1961). "Algorithm 64: Quicksort." Communications of the ACM, 4(7), 321.'
    assert _normalized(source, parser) == expected


@pytest.mark.parametrize("parser", _PARSERS)
def test_bare_url_in_a_citation_becomes_a_link(parser: str):
    """Verify Quarto autolinks bare citation URLs"""
    source = ".. [2] https://en.wikipedia.org/wiki/Arithmetic_mean"
    expected = "2. []{#cite-process-2}<https://en.wikipedia.org/wiki/Arithmetic_mean>"
    assert _normalized(source, parser) == expected


@pytest.mark.parametrize("parser", _PARSERS)
def test_markdown_link_in_a_citation_keeps_its_closing_parenthesis(parser: str):
    """Verify autolinking preserves a Markdown link's closing parenthesis"""
    source = ".. [1] Author, [Title](https://example.com/paper) 2020."
    expected = "1. []{#cite-process-1}Author, [Title](<https://example.com/paper>) 2020."
    assert _normalized(source, parser) == expected


@pytest.mark.parametrize("parser", _PARSERS)
def test_consecutive_citations_keep_their_numbers(parser: str):
    """Verify consecutive citations retain their labels"""
    source = ".. [1] First source.\n.. [2] Second source."
    expected = "1. []{#cite-process-1}First source.\n2. []{#cite-process-2}Second source."
    assert _normalized(source, parser) == expected


@pytest.mark.parametrize("parser", _PARSERS)
def test_text_without_citations_passes_through(parser: str):
    """Verify text without citations remains unchanged"""
    source = "Compute the mean.\n\nSee the module docs for details."
    assert _normalized(source, parser) == source


@pytest.mark.parametrize("parser", _PARSERS)
def test_alphabetic_label_is_left_alone(parser: str):
    """
    Verify alphabetic citation labels remain unchanged

    Markdown ordered lists require numeric labels, so conversion handles only
    numbered citations.
    """
    source = '.. [CIT2002] Cormen, T.H. et al. (2009). "Introduction to Algorithms".'
    assert _normalized(source, parser) == source


def test_docstringless_object_is_returned_unchanged():
    """Verify an object without a docstring remains unchanged"""
    obj = gf.Function("process")
    assert normalize_citations(obj) is obj


@pytest.mark.parametrize("parser", _PARSERS)
def test_indented_citation_keeps_its_indentation(parser: str):
    """Verify nested citations retain their indentation"""
    source = (
        "Parameters\n"
        "----------\n"
        "x\n"
        "    Something clever.\n"
        "\n"
        "    .. [1] Hoare, C. A. R. (1961). Algorithm 64: Quicksort.\n"
    )
    expected = (
        "Parameters\n"
        "----------\n"
        "x\n"
        "    Something clever.\n"
        "\n"
        "    1. []{#cite-process-1}Hoare, C. A. R. (1961). Algorithm 64: Quicksort.\n"
    )
    assert _normalized(source, parser) == expected


@pytest.mark.parametrize("parser", _PARSERS)
def test_consecutive_indented_citations_stay_separate(parser: str):
    """Verify adjacent nested citations remain separate"""
    source = (
        "Parameters\n"
        "----------\n"
        "x\n"
        "    Something clever.\n"
        "\n"
        "    .. [1] Hoare, C. A. R. (1961). Algorithm 64: Quicksort.\n"
        "    .. [2] Knuth, D. (1998). The Art of Computer Programming.\n"
    )
    expected = (
        "Parameters\n"
        "----------\n"
        "x\n"
        "    Something clever.\n"
        "\n"
        "    1. []{#cite-process-1}Hoare, C. A. R. (1961). Algorithm 64: Quicksort.\n"
        "    2. []{#cite-process-2}Knuth, D. (1998). The Art of Computer Programming.\n"
    )
    assert _normalized(source, parser) == expected


@pytest.mark.parametrize("parser", _PARSERS)
def test_indented_continuation_joins_when_more_indented_than_its_marker(parser: str):
    """Verify a nested continuation joins only its citation"""
    source = (
        "    .. [1] Hoare, C.A.R. (1961). \"Algorithm 64: Quicksort.\"\n"
        '       Communications of the ACM, 4(7), 321.\n'
    )
    expected = (
        '    1. []{#cite-process-1}Hoare, C.A.R. (1961). "Algorithm 64: Quicksort." '
        "Communications of the ACM, 4(7), 321.\n"
    )
    assert _normalized(source, parser) == expected


@pytest.mark.parametrize("parser", _PARSERS)
def test_citation_with_body_on_the_following_line_converts(parser: str):
    """Verify a citation can start its body on the following line"""
    source = ".. [1]\n   Hoare, C. A. R. (1961). Algorithm 64.\n"
    expected = "1. []{#cite-process-1}Hoare, C. A. R. (1961). Algorithm 64.\n"
    assert _normalized(source, parser) == expected


@pytest.mark.parametrize("parser", _PARSERS)
def test_indented_citation_does_not_swallow_the_following_text(parser: str):
    """Verify a nested citation preserves the following section"""
    source = (
        "Parameters\n"
        "----------\n"
        "x\n"
        "    Something clever.\n"
        "\n"
        "    .. [1] Hoare, C. A. R. (1961). Algorithm 64: Quicksort.\n"
        "\n"
        "Returns\n"
        "-------\n"
        "int\n"
        "    A description.\n"
    )
    result = _normalized(source, parser)
    assert "Returns" in result
    assert "A description." in result
    assert ".. [" not in result


@pytest.mark.parametrize("parser", _PARSERS)
def test_single_reference_links_both_ways(parser: str):
    """
    Verify one reference and its citation link in both directions

    The citation uses a linked caret to return to the single reference.
    """
    source = "See [1]_ for details.\n\n.. [1] Hoare, C.A.R. (1961)."
    expected = (
        "See [[1]](#cite-process-1){#ref-process-1-1} for details.\n\n"
        "1. []{#cite-process-1}"
        '[^](#ref-process-1-1){.gd-linkback-text .gd-linkback-caret role="doc-backlink"} '
        "Hoare, C.A.R. (1961)."
    )
    assert _normalized(source, parser) == expected


@pytest.mark.parametrize("parser", _PARSERS)
def test_repeated_references_get_lettered_backlinks(parser: str):
    """
    Verify repeated references receive distinct backlinks

    The citation uses an inert caret followed by one lettered link for each
    reference in source order.
    """
    source = "Based on [1]_. Refined in [1]_.\n\n.. [1] Hoare, C.A.R. (1961)."
    result = _normalized(source, parser)

    assert "[[1]](#cite-process-1){#ref-process-1-1}" in result
    assert "[[1]](#cite-process-1){#ref-process-1-2}" in result
    assert "[^]{.gd-linkback-text .gd-linkback-caret}" in result
    assert (
        '[a](#ref-process-1-1){.gd-linkback-text .gd-linkback-letter '
        'role="doc-backlink"}'
    ) in result
    assert (
        '[b](#ref-process-1-2){.gd-linkback-text .gd-linkback-letter '
        'role="doc-backlink"}'
    ) in result
    assert "[^](#ref-process-1-1)" not in result


@pytest.mark.parametrize("parser", _PARSERS)
def test_uncited_citation_carries_no_marker(parser: str):
    """Verify an unreferenced citation has no backlink marker"""
    source = ".. [1] Hoare, C.A.R. (1961)."
    assert _normalized(source, parser) == "1. []{#cite-process-1}Hoare, C.A.R. (1961)."


@pytest.mark.parametrize("parser", _PARSERS)
def test_forward_reference_links(parser: str):
    """
    Verify a reference can precede its citation

    References sections usually follow the prose that cites them.
    """
    source = (
        "Notes\n-----\nBased on [1]_.\n\n"
        "References\n----------\n.. [1] Smith, J. (2020)."
    )
    result = _normalized(source, parser)
    assert "[[1]](#cite-process-1){#ref-process-1-1}" in result
    assert '[^](#ref-process-1-1){.gd-linkback-text' in result


@pytest.mark.parametrize("parser", _PARSERS)
def test_unmatched_reference_is_left_alone(parser: str):
    """
    Verify an undefined reference remains literal

    Linking it would hide the missing citation.
    """
    source = "See [1]_ and [7]_.\n\n.. [1] Hoare, C.A.R. (1961)."
    result = _normalized(source, parser)
    assert "[[1]](#cite-process-1){#ref-process-1-1}" in result
    assert "[7]_" in result


@pytest.mark.parametrize("parser", _PARSERS)
def test_reference_without_any_citation_is_left_alone(parser: str):
    """Verify references remain unchanged when no citations are defined"""
    source = "See [1]_ for details."
    assert _normalized(source, parser) == source


@pytest.mark.parametrize("parser", _PARSERS)
def test_anchors_differ_between_objects(parser: str):
    """
    Verify separate objects use distinct citation anchors

    A class page can render several members that each define `.. [1]`.
    Including the object path prevents their anchors from colliding.
    """
    source = "See [1]_.\n\n.. [1] Hoare, C.A.R. (1961)."
    first = _normalized_for("quicksort", source, parser)
    second = _normalized_for("binary_search", source, parser)

    assert "#cite-quicksort-1" in first
    assert "#cite-binary_search-1" in second
    assert "quicksort" not in second


@pytest.mark.parametrize("parser", _PARSERS)
def test_dotted_object_path_becomes_a_valid_anchor(parser: str):
    """
    Verify dotted object paths produce selector-safe anchors

    Replace dots with hyphens so CSS treats them as text rather than class
    selectors. The `cite-` prefix also prevents a leading digit.
    """
    module = gf.Module("gdtest_long_docs")
    obj = gf.Function("transform_data", parent=module)
    obj.docstring = gf.Docstring("", parent=obj, parser=parser)
    obj.docstring.value = "See [1]_.\n\n.. [1] Smith, J. (2020)."
    result = normalize_citations(obj)
    assert result.docstring is not None
    assert "#cite-gdtest_long_docs-transform_data-1" in result.docstring.value


@pytest.mark.parametrize("parser", _PARSERS)
def test_anchor_slug_does_not_collapse_distinct_paths(parser: str):
    """
    Verify case and separator differences produce distinct anchors

    Keep case and underscores so `pkg.foo_bar` and `pkg_foo.bar`, and `Foo.Bar`
    and `foo.bar`, cannot collapse to the same anchor.
    """
    source = "See [1]_.\n\n.. [1] Hoare, C.A.R. (1961)."

    def _for(dotted_path: str) -> str:
        parts = dotted_path.split(".")
        module = gf.Module(parts[0])
        obj = gf.Function(parts[1], parent=module)
        obj.docstring = gf.Docstring("", parent=obj, parser=parser)
        obj.docstring.value = source
        result = normalize_citations(obj)
        assert result.docstring is not None
        return result.docstring.value

    underscore_first = _for("pkg.foo_bar")
    underscore_second = _for("pkg_foo.bar")
    assert "#cite-pkg-foo_bar-1" in underscore_first
    assert "#cite-pkg_foo-bar-1" in underscore_second
    assert underscore_first != underscore_second

    case_first = _for("Foo.Bar")
    case_second = _for("foo.bar")
    assert "#cite-Foo-Bar-1" in case_first
    assert "#cite-foo-bar-1" in case_second
    assert case_first != case_second

    digit_led = _for("123pkg.thing")
    assert "#cite-123pkg-thing-1" in digit_led

    for value in (underscore_first, underscore_second, case_first, case_second, digit_led):
        anchor_id = value.split("#", 1)[1].split("}", 1)[0]
        assert not anchor_id[0].isdigit()


@pytest.mark.parametrize(
    ("index", "expected"),
    [(0, "a"), (1, "b"), (25, "z"), (26, "aa"), (27, "ab"), (51, "az"), (52, "ba")],
)
def test_occurrence_label_sequence(index: int, expected: str):
    """Verify backlink labels continue after `z`"""
    from great_docs._builtin.normalization._citations import _occurrence_label

    assert _occurrence_label(index) == expected
