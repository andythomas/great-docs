# pyright: reportPrivateUsage=false

import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from great_docs._git import (
    format_date,
    get_file_contributors,
    get_file_created_date,
    get_file_modified_date,
    is_git_repository,
)


def test_format_date_default():
    """Formats with default '%B %d, %Y' pattern."""
    dt = datetime(2026, 3, 24)
    assert format_date(dt) == "March 24, 2026"


def test_format_date_custom():
    """Formats with custom pattern."""
    dt = datetime(2026, 3, 24)
    assert format_date(dt, "%Y-%m-%d") == "2026-03-24"


def test_format_date_none_returns_empty():
    """Returns empty string for None input."""
    assert format_date(None) == ""


def test_format_date_iso():
    """Formats with ISO-like pattern."""
    dt = datetime(2026, 1, 5, 14, 30, 0)
    assert format_date(dt, "%Y-%m-%dT%H:%M:%S") == "2026-01-05T14:30:00"


@patch("great_docs._git.subprocess.run")
def test_created_date_git_success(mock_run):
    """Returns datetime from Git log output."""
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout="2026-02-10T09:15:30+00:00\n2026-01-05T10:30:00+00:00\n",
    )
    result = get_file_created_date(Path("docs/guide.qmd"), Path("/project"))
    assert result is not None
    assert result.year == 2026
    assert result.month == 1
    assert result.day == 5


@patch("great_docs._git.subprocess.run")
def test_created_date_git_empty_output(mock_run):
    """Falls back to mtime when Git returns empty output."""
    mock_run.return_value = MagicMock(returncode=0, stdout="")

    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "test.txt"
        f.write_text("hello")
        result = get_file_created_date(f, Path(tmp))
        assert result is not None
        assert isinstance(result, datetime)


@patch("great_docs._git.subprocess.run")
def test_created_date_git_failure_fallback(mock_run):
    """Falls back to mtime on non-zero returncode."""
    mock_run.return_value = MagicMock(returncode=128, stdout="")

    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "test.txt"
        f.write_text("content")
        result = get_file_created_date(f, Path(tmp))
        assert result is not None


@patch("great_docs._git.subprocess.run")
def test_created_date_timeout_fallback(mock_run):
    """Falls back to mtime on subprocess timeout."""
    mock_run.side_effect = subprocess.TimeoutExpired(cmd="git", timeout=10)

    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "test.txt"
        f.write_text("data")
        result = get_file_created_date(f, Path(tmp))
        assert result is not None


@patch("great_docs._git.subprocess.run")
def test_created_date_no_fallback_returns_none(mock_run):
    """Returns None when Git fails and fallback disabled."""
    mock_run.return_value = MagicMock(returncode=128, stdout="")
    result = get_file_created_date(Path("nonexistent.txt"), Path("/tmp"), fallback_to_mtime=False)
    assert result is None


@patch("great_docs._git.subprocess.run")
def test_created_date_absolute_path(mock_run):
    """Handles absolute filepath by making it relative."""
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout="2026-03-01T12:00:00+00:00\n",
    )
    result = get_file_created_date(Path("/project/docs/guide.qmd"), Path("/project"))
    assert result is not None
    call_args = mock_run.call_args[0][0]
    assert "docs/guide.qmd" in " ".join(call_args)


@patch("great_docs._git.subprocess.run")
def test_created_date_path_not_under_root(mock_run):
    """Handles filepath not under project_root gracefully."""
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout="2026-03-01T12:00:00+00:00\n",
    )
    result = get_file_created_date(Path("/other/file.txt"), Path("/project"))
    assert result is not None


@patch("great_docs._git.subprocess.run")
def test_created_date_file_not_found_fallback(mock_run):
    """FileNotFoundError (git not installed) triggers fallback."""
    mock_run.side_effect = FileNotFoundError("git not found")

    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "test.txt"
        f.write_text("data")
        result = get_file_created_date(f, Path(tmp))
        assert result is not None


@patch("great_docs._git.subprocess.run")
def test_modified_date_git_success(mock_run):
    """Returns datetime from most recent Git commit."""
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout="2026-03-24T14:45:00+00:00\n",
    )
    result = get_file_modified_date(Path("docs/guide.qmd"), Path("/project"))
    assert result is not None
    assert result.year == 2026
    assert result.month == 3
    assert result.day == 24


@patch("great_docs._git.subprocess.run")
def test_modified_date_git_empty_output(mock_run):
    """Falls back to mtime when Git returns empty output."""
    mock_run.return_value = MagicMock(returncode=0, stdout="")

    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "test.txt"
        f.write_text("hello")
        result = get_file_modified_date(f, Path(tmp))
        assert result is not None


@patch("great_docs._git.subprocess.run")
def test_modified_date_git_failure_fallback(mock_run):
    """Falls back to mtime on Git failure."""
    mock_run.return_value = MagicMock(returncode=128, stdout="")

    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "test.txt"
        f.write_text("content")
        result = get_file_modified_date(f, Path(tmp))
        assert result is not None


@patch("great_docs._git.subprocess.run")
def test_modified_date_no_fallback(mock_run):
    """Returns None when Git fails and fallback disabled."""
    mock_run.return_value = MagicMock(returncode=128, stdout="")
    result = get_file_modified_date(Path("nonexistent.txt"), Path("/tmp"), fallback_to_mtime=False)
    assert result is None


@patch("great_docs._git.subprocess.run")
def test_modified_date_timeout(mock_run):
    """Falls back on timeout."""
    mock_run.side_effect = subprocess.TimeoutExpired(cmd="git", timeout=10)

    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "test.txt"
        f.write_text("data")
        result = get_file_modified_date(f, Path(tmp))
        assert result is not None


@patch("great_docs._git.subprocess.run")
def test_modified_date_absolute_path(mock_run):
    """Handles absolute filepath."""
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout="2026-03-01T12:00:00+00:00\n",
    )
    result = get_file_modified_date(Path("/project/file.txt"), Path("/project"))
    assert result is not None


@patch("great_docs._git.subprocess.run")
def test_modified_date_path_not_under_root(mock_run):
    """Handles filepath outside project_root."""
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout="2026-03-01T12:00:00+00:00\n",
    )
    result = get_file_modified_date(Path("/other/file.txt"), Path("/project"))
    assert result is not None


@patch("great_docs._git.subprocess.run")
def test_contributors_multiple(mock_run):
    """Returns deduplicated list in order."""
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout="Alice Smith\nBob Jones\nAlice Smith\nCharlie Brown\n",
    )
    result = get_file_contributors(Path("file.py"), Path("/project"))
    assert result == ["Alice Smith", "Bob Jones", "Charlie Brown"]


@patch("great_docs._git.subprocess.run")
def test_contributors_single(mock_run):
    """Returns single contributor."""
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout="Alice Smith\nAlice Smith\n",
    )
    result = get_file_contributors(Path("file.py"), Path("/project"))
    assert result == ["Alice Smith"]


@patch("great_docs._git.subprocess.run")
def test_contributors_git_failure(mock_run):
    """Returns empty list on Git failure."""
    mock_run.return_value = MagicMock(returncode=128, stdout="")
    result = get_file_contributors(Path("file.py"), Path("/project"))
    assert result == []


@patch("great_docs._git.subprocess.run")
def test_contributors_timeout(mock_run):
    """Returns empty list on timeout."""
    mock_run.side_effect = subprocess.TimeoutExpired(cmd="git", timeout=10)
    result = get_file_contributors(Path("file.py"), Path("/project"))
    assert result == []


@patch("great_docs._git.subprocess.run")
def test_contributors_empty_output(mock_run):
    """Returns empty list for empty Git output."""
    mock_run.return_value = MagicMock(returncode=0, stdout="")
    result = get_file_contributors(Path("file.py"), Path("/project"))
    assert result == []


@patch("great_docs._git.subprocess.run")
def test_contributors_absolute_path(mock_run):
    """Handles absolute filepath."""
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout="Dev One\n",
    )
    result = get_file_contributors(Path("/project/src/mod.py"), Path("/project"))
    assert result == ["Dev One"]


@patch("great_docs._git.subprocess.run")
def test_contributors_file_not_found(mock_run):
    """FileNotFoundError (git not installed) returns empty list."""
    mock_run.side_effect = FileNotFoundError("git not found")
    result = get_file_contributors(Path("file.py"), Path("/project"))
    assert result == []


@patch("great_docs._git.subprocess.run")
def test_is_git_repo_true(mock_run):
    """Returns True when git rev-parse succeeds."""
    mock_run.return_value = MagicMock(returncode=0)
    assert is_git_repository(Path("/project")) is True


@patch("great_docs._git.subprocess.run")
def test_is_git_repo_false(mock_run):
    """Returns False when git rev-parse fails."""
    mock_run.return_value = MagicMock(returncode=128)
    assert is_git_repository(Path("/not-a-repo")) is False


@patch("great_docs._git.subprocess.run")
def test_is_git_repo_timeout(mock_run):
    """Returns False on timeout."""
    mock_run.side_effect = subprocess.TimeoutExpired(cmd="git", timeout=5)
    assert is_git_repository(Path("/project")) is False


@patch("great_docs._git.subprocess.run")
def test_is_git_repo_not_installed(mock_run):
    """Returns False when git is not installed."""
    mock_run.side_effect = FileNotFoundError("git not found")
    assert is_git_repository(Path("/project")) is False


@patch("great_docs._git.subprocess.run")
def test_is_git_repo_os_error(mock_run):
    """Returns False on OSError."""
    mock_run.side_effect = OSError("permission denied")
    assert is_git_repository(Path("/project")) is False


def test_get_file_created_date_git_exception_returns_mtime_fallback(tmp_path: Path):
    """get_file_created_date falls back to mtime when git subprocess raises."""
    f = tmp_path / "doc.md"
    f.write_text("hello")

    with patch("subprocess.run", side_effect=FileNotFoundError("git not found")):
        result = get_file_created_date(f, project_root=tmp_path, fallback_to_mtime=True)

    assert result is not None


def test_get_file_created_date_fallback_file_not_found_returns_none(tmp_path: Path):
    """get_file_created_date returns None when file is missing and git fails."""
    missing = tmp_path / "ghost.md"

    with patch("subprocess.run", side_effect=FileNotFoundError("no git")):
        result = get_file_created_date(missing, project_root=tmp_path, fallback_to_mtime=True)

    assert result is None


def test_get_file_modified_date_fallback_file_not_found_returns_none(tmp_path: Path):
    """get_file_modified_date returns None when file is missing and git fails."""
    missing = tmp_path / "ghost.md"

    with patch("subprocess.run", side_effect=FileNotFoundError("no git")):
        result = get_file_modified_date(missing, project_root=tmp_path, fallback_to_mtime=True)

    assert result is None


def test_get_file_contributors_filepath_outside_project_root(tmp_path: Path):
    """get_file_contributors handles a filepath that is not relative to project_root."""
    other_root = tmp_path / "other"
    other_root.mkdir()
    f = tmp_path / "outside.md"
    f.write_text("hi")

    # project_root is other_root; filepath is not under it -> ValueError -> uses absolute path
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = ""
    with patch("subprocess.run", return_value=mock_result):
        result = get_file_contributors(f, project_root=other_root)

    assert isinstance(result, list)


def test_get_file_created_date_empty_iso_date_falls_through_to_mtime(tmp_path: Path):
    """get_file_created_date returns mtime when git returns empty date string."""
    f = tmp_path / "doc.md"
    f.write_text("hello")

    # Simulate git returning empty stdout for the date
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "   "  # whitespace only =? iso_date strips to "" -> falsy

    with patch("subprocess.run", return_value=mock_result):
        result = get_file_created_date(f, project_root=tmp_path, fallback_to_mtime=True)

    # Should have fallen through to mtime fallback
    assert result is not None
