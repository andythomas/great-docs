"""Built-in reStructuredText directives and their Quarto representation"""

from __future__ import annotations

import re

import griffe as gf

from great_docs._builtin.directives._callouts import (
    CALLOUT_DIRECTIVES,
    collect_indented_body,
    dedent_lines,
    join_content,
    render_callout,
)
from great_docs.hooks import on_object_resolved
from great_docs.pandoc.blocks import Div
from great_docs.pandoc.components import Attr

_SPECIAL_DIRECTIVES = frozenset({"math", "seealso", "todo"})
_RST_DIRECTIVES = CALLOUT_DIRECTIVES | _SPECIAL_DIRECTIVES
_DIRECTIVE_NAME_PATTERN = "|".join(
    re.escape(name) for name in sorted(_RST_DIRECTIVES, key=len, reverse=True)
)
_DIRECTIVE_RE = re.compile(
    rf"^(?P<indent>[ \t]*)\.\.[ \t]+(?P<name>{_DIRECTIVE_NAME_PATTERN})::"
    r"(?:[ \t]+(?P<inline>.*?))?[ \t]*$"
)


@on_object_resolved(priority=0)  # pyright: ignore[reportArgumentType]
def add_rst_directives(obj: gf.Object | gf.Alias) -> gf.Object | gf.Alias:
    """
    Replace RST directives in an object's docstring value with Quarto markup

    Parameters
    ----------
    obj
        The resolved object.

    Returns
    -------
    The object with supported RST directives replaced in its docstring value.
    """
    docstring = obj.docstring
    if docstring is None or docstring.parser != gf.Parser.sphinx:
        return obj

    converted = convert_rst_directives(docstring.value)
    if converted != docstring.value:
        docstring.value = converted
    return obj


def convert_rst_directives(text: str) -> str:
    """
    Render recognized RST directives in docstring text as Quarto markup

    Parameters
    ----------
    text
        Docstring text containing RST directives.

    Returns
    -------
    The text with supported directives replaced by Quarto markup.
    """
    if ".." not in text:
        return text

    lines = text.splitlines()
    converted: list[str] = []
    index = 0

    while index < len(lines):
        line = lines[index]
        candidate = line.lstrip().startswith("..")
        match = _DIRECTIVE_RE.match(line) if candidate else None
        if match is None:
            converted.append(line)
            index += 1
            continue

        directive_index = index
        directive_indent = len(match.group("indent"))
        body_lines, index = collect_indented_body(lines, index + 1, directive_indent)
        inline = match.group("inline") or ""
        if not inline and not body_lines and index < len(lines):
            converted.append(lines[directive_index])
            index = directive_index + 1
            continue

        body = "\n".join(dedent_lines(body_lines))
        content = join_content(inline, body)
        name = match.group("name")
        if name == "math":
            replacement = f"$$\n{content.strip()}\n$$"
        elif name == "seealso":
            replacement = f"See Also\n--------\n{content.strip()}"
        elif name == "todo":
            replacement = str(
                Div(
                    content=content,
                    attr=Attr(
                        classes=["callout-note"],
                        attributes={"title": "Todo"},
                    ),
                )
            )
        else:
            replacement = render_callout(name, body, inline)
        converted.extend(replacement.splitlines())

    return "\n".join(converted)
