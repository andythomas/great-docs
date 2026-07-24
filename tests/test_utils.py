import pytest

from great_docs._utils import fenced_lines


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
