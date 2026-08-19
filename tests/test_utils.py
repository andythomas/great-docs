import pytest

from great_docs._utils import QUARTO_YML_HEADER, fenced_lines, is_in_great_docs_build_dir


def test_fenced_lines_without_markers_returns_lines_and_clear_mask():
    assert fenced_lines("first\nsecond") == (
        ["first", "second"],
        [False, False],
    )


@pytest.mark.parametrize("fence", ["```", "~~~"])
def test_fenced_lines_marks_opening_content_and_closing_lines(fence: str):
    assert fenced_lines(f"before\n{fence}python\ninside\n{fence}\nafter") == (
        ["before", f"{fence}python", "inside", fence, "after"],
        [False, True, True, True, False],
    )


def test_fenced_lines_requires_a_matching_long_enough_closer():
    assert fenced_lines("````text\ninside\n```\nstill inside\n````\nafter")[1] == [
        True,
        True,
        True,
        True,
        True,
        False,
    ]


@pytest.mark.parametrize("text", ["a `code` span", "value ~ default"])
def test_fenced_lines_ignores_non_fence_characters(text: str):
    assert fenced_lines(text) == ([text], [False])


@pytest.mark.parametrize(
    "parts",
    [
        ("great-docs", "index.qmd"),
    ],
)
def test_is_in_great_docs_build_dir_recognises_current_build(parts: tuple[str, ...], tmp_path):
    assert is_in_great_docs_build_dir(parts, tmp_path) is True


def test_is_in_great_docs_build_dir_recognises_historical_build(tmp_path):
    build_dir = tmp_path / "great-docs-0.2"
    build_dir.mkdir()
    (build_dir / "_quarto.yml").write_text(QUARTO_YML_HEADER, encoding="utf-8")

    assert is_in_great_docs_build_dir((build_dir.name, "index.qmd"), tmp_path) is True


@pytest.mark.parametrize(
    "parts",
    [
        (),
        ("docs", "great-docs-examples", "index.qmd"),
        ("great_docs_notes", "index.qmd"),
        ("great-docs-notes", "index.qmd"),
    ],
)
def test_is_in_great_docs_build_dir_rejects_non_build_paths(parts: tuple[str, ...], tmp_path):
    if parts:
        (tmp_path / parts[0]).mkdir(exist_ok=True)

    assert is_in_great_docs_build_dir(parts, tmp_path) is False
