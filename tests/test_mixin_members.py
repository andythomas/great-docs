"""Tests for great_docs._apiref._render.mixin_members."""

from __future__ import annotations

import types
from unittest.mock import MagicMock, patch


class TestMixinMembersExcludeStr:
    def test_attribute_exclude_as_string(self):
        """When EXCLUSIONS.attributes returns a string, it's wrapped in tuple."""
        import great_docs._apiref._render.mixin_members as mod

        cls = vars(mod)["__RenderDocMembersMixin"]
        fake_obj = MagicMock()
        fake_obj.path = "pkg.MyClass"
        mock_doc = MagicMock()
        mock_doc.members = []
        fake_self = types.SimpleNamespace(obj=fake_obj, doc=mock_doc)

        mock_exclusions = MagicMock()
        mock_exclusions.attributes = {"pkg.MyClass": "_internal"}

        with patch("great_docs._apiref._globals.EXCLUSIONS", mock_exclusions):
            result = cls.attributes.func(fake_self)

        assert result == []

    def test_function_exclude_as_string(self):
        """When EXCLUSIONS.functions returns a string, it's wrapped in tuple."""
        import great_docs._apiref._render.mixin_members as mod

        cls = vars(mod)["__RenderDocMembersMixin"]
        fake_obj = MagicMock()
        fake_obj.path = "pkg.MyClass"
        mock_doc = MagicMock()
        mock_doc.members = []
        fake_self = types.SimpleNamespace(obj=fake_obj, doc=mock_doc)

        mock_exclusions = MagicMock()
        mock_exclusions.functions = {"pkg.MyClass": "_helper"}

        with patch("great_docs._apiref._globals.EXCLUSIONS", mock_exclusions):
            result = cls.functions.func(fake_self)

        assert result == []

    def test_class_member_pages_exclude_as_string(self):
        """When EXCLUSIONS.classes returns a string (class_member_pages), it's wrapped in tuple."""
        import great_docs._apiref._render.mixin_members as mod

        cls = vars(mod)["__RenderDocMembersMixin"]
        fake_obj = MagicMock()
        fake_obj.path = "pkg.Outer"
        mock_doc = MagicMock()
        mock_doc.members = []
        fake_self = types.SimpleNamespace(obj=fake_obj, doc=mock_doc)

        mock_exclusions = MagicMock()
        mock_exclusions.classes = {"pkg.Outer": "InnerPrivate"}

        with patch("great_docs._apiref._globals.EXCLUSIONS", mock_exclusions):
            result = cls.class_member_pages.func(fake_self)

        assert result == []
