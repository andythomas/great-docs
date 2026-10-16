"""
Social card metadata rendered from site and page options
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest
from yaml12 import format_yaml

from great_docs._website import social_cards
from great_docs.config import Config

pytestmark = pytest.mark.skipif(shutil.which("quarto") is None, reason="Quarto is not installed")

IMAGE = "https://docs.example.com/pkg/card.png"
_TAG = re.compile(r'<meta (?:property|name)="((?:og|twitter):[\w:]+)" content="([^"]*)"')


def _render_site(tmp_path: Path, yaml: str, image_url: str | None) -> tuple[Path, str]:
    """
    Render a two-page site with the supplied social card settings

    Returns
    -------
    :
        The output directory and Quarto's console output.
    """
    (tmp_path / "great-docs.yml").write_text(yaml, encoding="utf-8")
    project = tmp_path / "proj"
    (project / "guide").mkdir(parents=True)
    quarto: dict = {"project": {"type": "website"}, "website": {"title": "Pkg"}}
    social_cards.register(quarto, Config(tmp_path), image_url, project)
    (project / "_quarto.yml").write_text(format_yaml(quarto), encoding="utf-8")
    (project / "index.qmd").write_text("---\ntitle: Home\n---\n\nWelcome text.\n", encoding="utf-8")
    (project / "guide" / "page.qmd").write_text(
        "---\ntitle: Page\n---\n\nPage text.\n", encoding="utf-8"
    )

    result = subprocess.run(
        ["quarto", "render"], cwd=project, check=True, capture_output=True, text=True
    )
    return project / "_site", result.stdout + result.stderr


def _tags(page: Path) -> dict[str, list[str]]:
    tags: dict[str, list[str]] = {}
    for name, content in _TAG.findall(page.read_text(encoding="utf-8")):
        tags.setdefault(name, []).append(content)
    return tags


def test_site_options_without_settings(tmp_path):
    site, _ = _render_site(tmp_path, "", None)

    tags = _tags(site / "guide" / "page.html")
    assert tags["og:site_name"] == ["Pkg"]
    assert tags["og:title"] == ["Page – Pkg"]
    assert tags["twitter:card"] == ["summary"]
    assert "og:image" not in tags


def test_site_options_with_image_and_handle(tmp_path):
    yaml = "social_cards:\n  twitter_site: myhandle\n"
    site, output = _render_site(tmp_path, yaml, IMAGE)

    tags = _tags(site / "guide" / "page.html")
    assert tags["og:image"] == [IMAGE]
    assert tags["twitter:image"] == [IMAGE]
    assert tags["twitter:card"] == ["summary_large_image"]
    assert tags["twitter:site"] == ["@myhandle"]
    assert IMAGE not in output
