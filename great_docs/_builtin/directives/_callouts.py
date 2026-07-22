"""Canonical Great Docs callout directives and their Quarto representation"""

from __future__ import annotations

import re

import griffe as gf

from great_docs.hooks import on_object_resolved

_CALLOUT_MAP: dict[str, str] = {
    "note": "note",
    "warning": "warning",
    "caution": "caution",
    "danger": "important",
    "important": "important",
    "tip": "tip",
    "hint": "tip",
}

_VERSION_LABELS: dict[str, str] = {
    "versionadded": "Added in version",
    "versionchanged": "Changed in version",
    "deprecated": "Deprecated since version",
}

_VERSION_DIRECTIVES = frozenset(_VERSION_LABELS)
CALLOUT_DIRECTIVES = frozenset(_CALLOUT_MAP) | _VERSION_DIRECTIVES
_DIRECTIVE_NAME_PATTERN = "|".join(
    re.escape(name) for name in sorted(CALLOUT_DIRECTIVES, key=len, reverse=True)
)
_DIRECTIVE_RE = re.compile(
    rf"^(?P<indent>[ \t]*)%(?P<name>{_DIRECTIVE_NAME_PATTERN})"
    r"(?:[ \t]+(?P<inline>.*?))?[ \t]*$"
)


@on_object_resolved(priority=0)  # pyright: ignore[reportArgumentType]
def add_callouts(obj: gf.Object | gf.Alias) -> gf.Object | gf.Alias:
    """
    Render an object's canonical directives as callout sections

    Parameters
    ----------
    obj
        The resolved object.

    Returns
    -------
    The object with canonical directive blocks removed from its source text and
    appended as Quarto callout sections.
    """
    docstring = obj.docstring
    if docstring is None or not any(f"%{name}" in docstring.value for name in CALLOUT_DIRECTIVES):
        return obj

    cleaned, callouts = _extract_callouts(docstring.value)
    if not callouts:
        return obj

    docstring.value = cleaned
    docstring.__dict__.pop("parsed", None)
    docstring.parsed.append(gf.DocstringSectionText("\n\n".join(callouts)))
    return obj


def render_callout(name: str, body: str, inline: str = "") -> str:
    """Render a recognized docstring directive as Quarto callout markup"""
    content = _join_content(inline, body)
    if name in _VERSION_DIRECTIVES:
        parts = content.split(None, 1) if content else []
        version = parts[0] if parts else ""
        description = parts[1] if len(parts) > 1 else ""
        label = _VERSION_LABELS[name]
        title = f"{label} {version}" if version else label
        callout = "warning" if name == "deprecated" else "note"
        body_line = f"\n{description}\n" if description else "\n"
        return f'::: {{.callout-{callout} title="{title}"}}{body_line}:::'

    callout = _CALLOUT_MAP[name]
    body_line = f"\n{content}\n" if content else "\n"
    return f"::: {{.callout-{callout}}}{body_line}:::"


def convert_directives(text: str) -> str:
    """Render canonical callout directives in docstring text as Quarto blocks"""
    lines = text.splitlines()
    converted: list[str] = []
    index = 0

    while index < len(lines):
        match = _DIRECTIVE_RE.match(lines[index])
        if match is None:
            converted.append(lines[index])
            index += 1
            continue

        directive_indent = len(match.group("indent"))
        body_lines, index = _indented_body(lines, index + 1, directive_indent)
        body = "\n".join(_dedent_lines(body_lines))
        converted.extend(
            render_callout(
                match.group("name"),
                body,
                match.group("inline") or "",
            ).splitlines()
        )

    return "\n".join(converted)


def _join_content(inline: str, body: str) -> str:
    """Join inline directive text with its multiline body"""
    parts = [part.strip() for part in (inline, body) if part.strip()]
    return "\n".join(parts)


def _extract_callouts(text: str) -> tuple[str, list[str]]:
    """Separate docstring prose from its rendered canonical callouts"""
    lines = text.splitlines()
    cleaned: list[str] = []
    callouts: list[str] = []
    index = 0

    while index < len(lines):
        match = _DIRECTIVE_RE.match(lines[index])
        if match is None:
            cleaned.append(lines[index])
            index += 1
            continue

        directive_indent = len(match.group("indent"))
        body_lines, index = _indented_body(lines, index + 1, directive_indent)
        body = "\n".join(_dedent_lines(body_lines))
        callouts.append(
            render_callout(
                match.group("name"),
                body,
                match.group("inline") or "",
            )
        )

    cleaned_text = re.sub(r"\n{3,}", "\n\n", "\n".join(cleaned)).strip()
    return cleaned_text, callouts


def _indented_body(
    lines: list[str],
    start: int,
    directive_indent: int,
) -> tuple[list[str], int]:
    """Collect an indented directive body and its first unconsumed line"""
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
