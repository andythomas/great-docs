import pytest

from great_docs._utils import fenced_lines, is_in_great_docs_build_dir


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
        ("great-docs-0.2", "index.qmd"),
        ("great-docs-0.2",),
    ],
)
def test_is_in_great_docs_build_dir_matches_build_output(parts: tuple[str, ...]):
    assert is_in_great_docs_build_dir(parts) is True


@pytest.mark.parametrize(
    "parts",
    [
        (),
        ("docs", "great-docs-examples", "index.qmd"),
        ("great_docs_notes", "index.qmd"),
    ],
)
def test_is_in_great_docs_build_dir_ignores_nested_or_unrelated_dirs(parts: tuple[str, ...]):
    assert is_in_great_docs_build_dir(parts) is False
