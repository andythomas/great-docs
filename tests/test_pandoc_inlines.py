"""Tests for great_docs.pandoc.inlines."""

from __future__ import annotations

import pytest


class TestInlinesEmpty:
    def test_inlines_empty_returns_empty(self):
        """Inlines with no elements returns ''."""
        from great_docs.pandoc.inlines import Inlines

        assert str(Inlines(elements=None)) == ""
        assert str(Inlines(elements=[])) == ""

    def test_inlines0_empty_returns_empty(self):
        """Inlines0 with no elements returns ''."""
        from great_docs.pandoc.inlines import Inlines0

        assert str(Inlines0(elements=None)) == ""
        assert str(Inlines0(elements=[])) == ""


class TestInlineContentToStrError:
    def test_unsupported_type_raises(self):
        """Unsupported type raises TypeError."""
        from great_docs.pandoc.inlines import inlinecontent_to_str

        with pytest.raises(TypeError, match="Could not process type"):
            inlinecontent_to_str(12345)
