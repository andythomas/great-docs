"""Tests for great_docs._apiref.spec."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest


class TestSpecOptionsDefaultFactory:
    def test_default_factory_field_initialized(self):
        """Fields with default_factory are initialized when not passed."""
        from great_docs._apiref.spec import SpecOptions

        @dataclass(init=False)
        class TestSpec(SpecOptions):
            items: list = field(default_factory=list)

        obj = TestSpec()
        assert obj.items == []
        assert isinstance(obj.items, list)


class TestSpecSectionValidation:
    def test_empty_section_raises(self):
        """Section without title, subtitle, or contents raises."""
        from great_docs._apiref.spec import SpecSection

        with pytest.raises(ValueError, match="must specify a title"):
            SpecSection()

    def test_both_title_and_subtitle_raises(self):
        """Section with both title and subtitle raises."""
        from great_docs._apiref.spec import SpecSection

        with pytest.raises(ValueError, match="cannot specify both"):
            SpecSection(title="Functions", subtitle="Utilities")
