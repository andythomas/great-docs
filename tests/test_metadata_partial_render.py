"""
Translations and text direction in pages rendered by Quarto
"""

import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(shutil.which("quarto") is None, reason="Quarto is not installed")


def test_partial_and_direction_reach_the_page(tmp_path: Path):
    """
    Render literal dollar signs and right-to-left text direction

    The partial uses `$$` to escape each literal `$` in the translation bundle.
    """
    project = tmp_path / "proj"
    project.mkdir()
    (project / "metadata.html").write_text(
        '<meta charset="utf-8" />\n<title>$pagetitle$</title>\n'
        '<meta name="gd-i18n" content="a$$b">\n',
        encoding="utf-8",
    )
    (project / "_quarto.yml").write_text(
        "project:\n  type: website\nwebsite:\n  title: t\n"
        "format:\n  html:\n    dir: rtl\n    template-partials:\n      - metadata.html\n",
        encoding="utf-8",
    )
    (project / "index.qmd").write_text("---\ntitle: T\n---\n\nText\n", encoding="utf-8")

    subprocess.run(["quarto", "render"], cwd=project, check=True, capture_output=True)

    page = (project / "_site" / "index.html").read_text(encoding="utf-8")
    assert page.count('<meta name="gd-i18n" content="a$b">') == 1
    assert 'dir="rtl"' in page[page.index("<html") : page.index(">", page.index("<html"))]
