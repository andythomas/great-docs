"""Tests for great_docs._builtin.directives._callouts."""

from __future__ import annotations


class TestCollectIndentedBody:
    def test_blank_lines_before_end_of_input(self):
        """Blank lines followed by end-of-input breaks collection."""
        from great_docs._builtin.directives._callouts import collect_indented_body

        lines = [
            "    indented content",
            "",
            "",
        ]
        body, idx = collect_indented_body(lines, start=0, directive_indent=0)
        assert body == ["    indented content"]

    def test_blank_lines_before_dedented_content(self):
        """Blank lines followed by dedented content breaks."""
        from great_docs._builtin.directives._callouts import collect_indented_body

        lines = [
            "    indented content",
            "",
            "not indented anymore",
        ]
        body, idx = collect_indented_body(lines, start=0, directive_indent=0)
        assert body == ["    indented content"]
