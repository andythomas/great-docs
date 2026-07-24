import griffe as gf
import pytest


def _function(parser: str, docstring: str) -> gf.Function:
    """Build a typed function with a docstring in the selected style"""
    obj = gf.Function(
        "convert",
        parameters=gf.Parameters(
            gf.Parameter("value", annotation="int"),
        ),
        returns="str",
    )
    obj.docstring = gf.Docstring(docstring, parent=obj, parser=parser)
    return obj


@pytest.mark.parametrize(
    ("parser", "docstring"),
    [
        (
            "sphinx",
            """
            Convert a value.

            :param value: Value to convert.
            :type value: int
            :returns: Converted text.
            :rtype: str
            :raises ValueError: If the value is invalid.
            """,
        ),
        (
            "google",
            """
            Convert a value.

            Args:
                value: Value to convert.

            Returns:
                (str): Converted text.

            Raises:
                ValueError: If the value is invalid.
            """,
        ),
    ],
)
def test_parser_structures_callable_sections(parser: str, docstring: str):
    obj = _function(parser, docstring)

    kinds = [section.kind for section in obj.docstring.parsed]

    assert gf.DocstringSectionKind.parameters in kinds
    assert gf.DocstringSectionKind.returns in kinds
    assert gf.DocstringSectionKind.raises in kinds
