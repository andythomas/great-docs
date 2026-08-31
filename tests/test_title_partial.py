"""Tests for the bundled Quarto metadata partial used for page titles"""

import shutil
import subprocess
from pathlib import Path

import pytest

import great_docs

VENDORED = Path(great_docs.__file__).parent / "assets" / "metadata.html"

# `quarto --paths` returns roots that contain this relative path.
UPSTREAM_RELATIVE = Path("formats") / "html" / "pandoc" / "metadata.html"


def _quarto_partial() -> Path | None:
    """
    Locate the metadata partial of the installed Quarto

    Returns
    -------
    :
        Path to Quarto's installed copy, or `None` if Quarto is unavailable or
        does not report the file.
    """
    if shutil.which("quarto") is None:
        return None

    try:
        result = subprocess.run(
            ["quarto", "--paths"],
            capture_output=True,
            check=False,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError:
        return None

    if result.returncode != 0:
        return None

    for line in result.stdout.splitlines():
        candidate = Path(line.strip()) / UPSTREAM_RELATIVE
        if candidate.is_file():
            return candidate

    return None


def _without_title(content: str) -> list[str]:
    """
    Remove the title element from a metadata partial

    Parameters
    ----------
    content
        Contents of a metadata partial.

    Returns
    -------
    :
        Lines that do not contain `<title>`.
    """
    return [line for line in content.splitlines() if "<title>" not in line]


def test_bundled_partial_contains_title_element():
    """Confirm that the bundled title element remains available for replacement"""
    assert "<title>" in VENDORED.read_text(encoding="utf-8")


@pytest.mark.skipif(
    _quarto_partial() is None,
    reason="Quarto metadata partial is unavailable",
)
def test_bundled_partial_matches_quarto_except_for_title():
    """
    Keep the bundled metadata tags aligned with Quarto

    The build replaces the title element, so this comparison excludes that
    line. If the remaining lines differ, copy them from the installed partial
    without changing the bundled title element.
    """
    theirs = _quarto_partial()
    assert theirs is not None

    assert _without_title(VENDORED.read_text(encoding="utf-8")) == _without_title(
        theirs.read_text(encoding="utf-8")
    ), f"Bundled metadata tags differ from {theirs}"
