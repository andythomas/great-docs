"""
Meta descriptions in pages rendered by Quarto
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

from great_docs._website.seo.description import add_to_page, metadata_value, write_to_pages

pytestmark = pytest.mark.skipif(shutil.which("quarto") is None, reason="Quarto is not installed")

_META_DESCRIPTION = re.compile(r'<meta name="description" content="([^"<>]*)" ?/?>')


def test_descriptions_reach_the_page_intact(tmp_path: Path):
    """
    Render one well-formed description tag per page

    Quarto parses `description-meta` as Markdown and does not escape the
    result, so a value that still held Markdown would break the `<head>`.
    """
    project = tmp_path / "proj"
    project.mkdir()
    quarto_config = {"project": {"type": "website"}, "website": {"title": "t"}}
    (project / "_quarto.yml").write_text(
        "project:\n  type: website\nwebsite:\n  title: t\n", encoding="utf-8"
    )
    pages = {
        "own": "---\ntitle: Own\ndescription: Written by the author\n---\n\nText\n",
        "prose": (
            "---\ntitle: Prose\n---\n\n"
            "Use `sum` with [arrays](a.qmd) *quickly*, at $5 & @home on a_b.\n"
        ),
        "code": "---\ntitle: Code\n---\n\n```python\nx = 1\n```\n",
        "summary": add_to_page(
            "---\ntitle: Summary\n---\n\nText\n",
            metadata_value("Compare `a < b` with [](`~pkg.Frame`) and `**kwargs`") or "",
        ),
    }
    for name, content in pages.items():
        (project / f"{name}.qmd").write_text(content, encoding="utf-8")

    write_to_pages(project, quarto_config, "Site default")
    subprocess.run(["quarto", "render"], cwd=project, check=True, capture_output=True)

    def descriptions(name: str) -> list[str]:
        page = (project / "_site" / f"{name}.html").read_text(encoding="utf-8")
        head = page[: page.index("</head>")]
        assert head.count('name="description"') == len(_META_DESCRIPTION.findall(head))
        return _META_DESCRIPTION.findall(head)

    assert descriptions("own") == ["Written by the author"]
    assert descriptions("prose") == ["Use sum with arrays quickly, at $5 &amp; @home on a_b."]
    assert descriptions("code") == ["Site default"]
    assert descriptions("summary") == ["Compare a b with Frame and **kwargs"]
