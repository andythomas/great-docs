"""Typer CLI support for the Python (Click) CLI reference generator.

Typer is a Python CLI framework that is built on top of Click: a `typer.Typer` app is not itself a
`click.Command`/`click.Group`, but it can be turned into one with `typer.main.get_command`. Once
converted, the resulting object is an ordinary Click command tree, so all of the existing Click
introspection in `core.py` (options, arguments, subcommands, `--help` text) and `_api_diff.py` (CLI
snapshots) works unchanged.

These helpers are the single place that knows about Typer. Discovery code should detect candidates
with `is_cli_command()` and normalize them to a Click object with `to_click_command()` before
introspecting. Both degrade gracefully when Typer (or even Click) is not installed.
"""

from __future__ import annotations

from typing import Any


def is_typer_app(obj: Any) -> bool:
    """Return `True` when *obj* is a `typer.Typer` application instance.

    Returns `False` (rather than raising) when Typer is not installed.
    """
    try:
        import typer
    except ImportError:
        return False
    return isinstance(obj, typer.Typer)


def to_click_command(obj: Any) -> Any | None:
    """Coerce *obj* into a Click command, converting Typer apps.

    Parameters
    ----------
    obj
        A candidate CLI object. Already-Click `Command`/`Group` instances are returned unchanged.
        `typer.Typer` apps are converted to their underlying Click command via
        `typer.main.get_command`.

    Returns
    -------
    click.Command | None
        The Click command for *obj*, or `None` when *obj* is neither a Click command nor a Typer app
        (or when the required libraries are missing).
    """
    try:
        import click
    except ImportError:  # pragma: no cover - Click is a hard dependency
        return None

    if isinstance(obj, (click.Command, click.Group)):
        return obj

    try:
        import typer
        from typer.main import get_command
    except ImportError:
        return None

    if isinstance(obj, typer.Typer):
        try:
            return get_command(obj)
        except Exception:  # pragma: no cover - defensive (malformed Typer app)
            return None

    return None


def is_cli_command(obj: Any) -> bool:
    """Return `True` when *obj* is a documentable CLI (Click command or Typer app)."""
    return to_click_command(obj) is not None


# ---------------------------------------------------------------------------
# Duck-typed introspection helpers
#
# Typer vendors its own copy of Click, so a command returned by `typer.main.get_command` is *not* an
# instance of the top-level `click` package's `Command`/`Group`/`Option`/`Argument` classes. These
# helpers introspect commands structurally instead of with `isinstance` against a specific Click, so
# the same extraction code works for both plain Click CLIs and Typer apps (and any future Click
# variant).
# ---------------------------------------------------------------------------


def is_cli_group(cmd: Any) -> bool:
    """Return `True` when *cmd* is a command group (has named subcommands).

    Works for both `click.Group` and Typer's vendored group, which both expose a dict-like
    `commands` mapping. Leaf commands have no such mapping.
    """
    commands = getattr(cmd, "commands", None)
    return commands is not None and hasattr(commands, "items")


def param_kind(param: Any) -> str:
    """Return `"option"`, `"argument"`, or `""` for a Click/Typer parameter.

    Uses Click's `param_type_name` attribute, which both plain Click and Typer's vendored Click set
    on every parameter.
    """
    return getattr(param, "param_type_name", "") or ""
