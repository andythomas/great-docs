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


@pytest.mark.parametrize("parser", _PARSERS)
def test_citation_converts_under_every_parser(parser: str):
    """
    Verify every parser converts numbered citation markers

    Numbered citation conversion is parser-independent.
    """
    source = '.. [1] Hoare, C.A.R. (1961). "Algorithm 64: Quicksort."'
    expected = '1. Hoare, C.A.R. (1961). "Algorithm 64: Quicksort."'
    assert _normalized(source, parser) == expected


@pytest.mark.parametrize("parser", _PARSERS)
def test_wrapped_citation_joins_onto_one_line(parser: str):
    """Verify an indented continuation joins its citation"""
    source = '.. [1] Hoare, C.A.R. (1961). "Algorithm 64: Quicksort."\n   Communications of the ACM, 4(7), 321.'
    expected = '1. Hoare, C.A.R. (1961). "Algorithm 64: Quicksort." Communications of the ACM, 4(7), 321.'
    assert _normalized(source, parser) == expected


@pytest.mark.parametrize("parser", _PARSERS)
def test_bare_url_in_a_citation_becomes_a_link(parser: str):
    """Verify Quarto autolinks bare citation URLs"""
    source = ".. [2] https://en.wikipedia.org/wiki/Arithmetic_mean"
    expected = "2. <https://en.wikipedia.org/wiki/Arithmetic_mean>"
    assert _normalized(source, parser) == expected


@pytest.mark.parametrize("parser", _PARSERS)
def test_consecutive_citations_keep_their_numbers(parser: str):
    """Verify consecutive citations retain their labels"""
    source = ".. [1] First source.\n.. [2] Second source."
    assert _normalized(source, parser) == "1. First source.\n2. Second source."


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
