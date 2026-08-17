import shutil
from pathlib import Path

from great_docs._utils import QUARTO_YML_HEADER
from great_docs.mcp import _sibling_build_dirs


class TestSiblingBuildDirs:
    def _make_build_dir(self, path: Path) -> None:
        path.mkdir(parents=True)
        (path / "_quarto.yml").write_text(
            QUARTO_YML_HEADER + "project:\n  type: website\n", encoding="utf-8"
        )

    def test_finds_marked_dirs_only(self, tmp_path: Path):
        self._make_build_dir(tmp_path / "great-docs-0.2")
        self._make_build_dir(tmp_path / "great-docs-0.1")
        (tmp_path / "great-docs-notes").mkdir()
        (tmp_path / "great-docs").mkdir()

        result = _sibling_build_dirs(tmp_path)

        assert [d.name for d in result] == ["great-docs-0.1", "great-docs-0.2"]

    def test_empty_when_no_versions_built(self, tmp_path: Path):
        (tmp_path / "great-docs").mkdir()
        assert _sibling_build_dirs(tmp_path) == []

    def test_skips_symlinked_dir(self, tmp_path: Path):
        real_target = tmp_path / "real-target"
        self._make_build_dir(real_target)
        (tmp_path / "great-docs-0.1").symlink_to(real_target, target_is_directory=True)

        result = _sibling_build_dirs(tmp_path)

        assert result == []


class TestCleanRemovesSiblings:
    """
    Deletion coverage for historical build directories

    A clean build must remove marked historical output while preserving the
    current build and unmarked directories.
    """

    def _make_build_dir(self, path: Path) -> None:
        path.mkdir(parents=True)
        (path / "_quarto.yml").write_text(
            QUARTO_YML_HEADER + "project:\n  type: website\n", encoding="utf-8"
        )

    def test_clean_removes_siblings_but_keeps_current_and_unmarked(self, tmp_path: Path):
        self._make_build_dir(tmp_path / "great-docs-0.1")
        (tmp_path / "great-docs").mkdir()
        (tmp_path / "great-docs" / "index.html").write_text("current build", encoding="utf-8")
        unmarked = tmp_path / "great-docs-notes"
        unmarked.mkdir()
        (unmarked / "notes.txt").write_text("keep me", encoding="utf-8")

        for d in _sibling_build_dirs(tmp_path):
            shutil.rmtree(d)

        assert not (tmp_path / "great-docs-0.1").exists()
        assert (tmp_path / "great-docs").is_dir()
        assert (tmp_path / "great-docs" / "index.html").exists()
        assert unmarked.is_dir()
        assert (unmarked / "notes.txt").read_text(encoding="utf-8") == "keep me"
