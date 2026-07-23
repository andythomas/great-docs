"""Built-in reStructuredText directives and their Quarto representation"""

from __future__ import annotations

import re

import griffe as gf

from great_docs._builtin.directives._callouts import (
    CALLOUT_DIRECTIVES,
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
    """Replace RST directives in an object's docstring value with Quarto markup"""
    docstring = obj.docstring
    if docstring is None:
        return obj

    converted = convert_rst_directives(docstring.value)
    if converted != docstring.value:
        docstring.value = converted
    return obj


def convert_rst_directives(text: str) -> str:
    """Render recognized RST directives in docstring text as Quarto markup"""
    lines = text.splitlines()
    converted: list[str] = []
    index = 0

    while index < len(lines):
        match = _DIRECTIVE_RE.match(lines[index])
        if match is None:
            converted.append(lines[index])
            index += 1
            continue

        directive_index = index
        directive_indent = len(match.group("indent"))
        body_lines, index = _indented_body(lines, index + 1, directive_indent)
        inline = match.group("inline") or ""
        if not inline and not body_lines and index < len(lines):
            converted.append(lines[directive_index])
            index = directive_index + 1
            continue

        body = "\n".join(_dedent_lines(body_lines))
        content = _join_content(inline, body)
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


def _join_content(inline: str, body: str) -> str:
    """Join inline directive text with its indented body"""
    parts = [part.strip() for part in (inline, body) if part.strip()]
    return "\n".join(parts)


def _indented_body(
    lines: list[str],
    start: int,
    directive_indent: int,
) -> tuple[list[str], int]:
    """Collect the indented RST body and its first unconsumed source line"""
    body: list[str] = []
    index = start

    while index < len(lines):
        line = lines[index]
        if line.strip():
            indent = len(line) - len(line.lstrip())
            if indent <= directive_indent:
                break
            body.append(line)
            index += 1
            continue

        next_content = index + 1
        while next_content < len(lines) and not lines[next_content].strip():
            next_content += 1
        if next_content >= len(lines):
            break
        next_line = lines[next_content]
        next_indent = len(next_line) - len(next_line.lstrip())
        if next_indent <= directive_indent:
            break
        body.append("")
        index += 1

    return body, index


def _dedent_lines(lines: list[str]) -> list[str]:
    """Align body lines to the least-indented nonblank content"""
    margin = min(
        (len(line) - len(line.lstrip()) for line in lines if line.strip()),
        default=0,
    )
    return [line[margin:] if line.strip() else "" for line in lines]
