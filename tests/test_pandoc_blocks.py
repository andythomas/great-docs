"""Tests for great_docs.pandoc.blocks."""

from __future__ import annotations

from unittest.mock import MagicMock


class TestBlockcontentToStrItemsEmpty:
    def test_block_with_empty_as_list_item(self):
        """fmt('', pfx) returns '' inside sequence iteration."""
        from great_docs.pandoc.blocks import Block, blockcontent_to_str_items

        mock_block = MagicMock(spec=Block)
        mock_block.as_list_item = ""
        result = blockcontent_to_str_items([mock_block], "bullet")
        assert result == ""
