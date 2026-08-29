"""Tests for great_docs._apiref.introspect."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import griffe as gf
import pytest

import great_docs._apiref.introspect as introspect_mod
from great_docs._apiref.introspect import (
    _promote_callable_attribute,
    resolve_alias,
)


class TestStaticObjectParentAlias:
    def test_parent_alias_wraps_function(self):
        """When parent is an Alias and obj is a Function, wraps obj in Alias."""
        from great_docs._apiref.introspect import _static_object

        func = gf.Function(name="do_thing", lineno=1)
        parent_alias = MagicMock(spec=gf.Alias)

        mock_loader = MagicMock()
        collection = {
            "pkg.cls.do_thing": func,
            "pkg.cls": parent_alias,
        }
        mock_loader.modules_collection.__getitem__ = lambda self, key: collection[key]

        result = _static_object("pkg", "cls.do_thing", mock_loader)

        assert isinstance(result, gf.Alias)
        assert result.name == "do_thing"


class TestResolveAlias:
    def test_infinite_recursion_raises(self):
        """Raises ValueError after >100 hops."""
        mock_alias = MagicMock(spec=gf.Alias)
        mock_alias.target = mock_alias

        with pytest.raises(ValueError, match="infinitely recursing"):
            resolve_alias(mock_alias)

    def test_resolution_error_without_get_object_reraises(self):
        """AliasResolutionError re-raises when no get_object provided."""
        mock_alias = MagicMock(spec=gf.Alias)
        err = gf.AliasResolutionError(MagicMock())
        type(mock_alias).target = property(lambda self: (_ for _ in ()).throw(err))

        with pytest.raises(gf.AliasResolutionError):
            resolve_alias(mock_alias, get_object=None)

    def test_resolution_error_with_get_object_retries(self):
        """AliasResolutionError with get_object retries via get_object."""
        mock_alias = MagicMock(spec=gf.Alias)
        mock_target_alias = MagicMock()
        mock_target_alias.target_path = "some.target"

        err = gf.AliasResolutionError(mock_target_alias)
        type(mock_alias).target = property(lambda self: (_ for _ in ()).throw(err))

        resolved = gf.Function(name="resolved_func", lineno=1)

        result = resolve_alias(mock_alias, get_object=lambda path: resolved)
        assert result is resolved


class TestLocateRuntimeObject:
    def test_parent_chain_attribute_error(self):
        """When parent class chain can't be traversed, returns None."""
        from great_docs._apiref.introspect import _locate_runtime_object

        obj = MagicMock(spec=gf.Function)
        obj.name = "my_method"

        parent_cls = MagicMock(spec=gf.Class)
        parent_cls.name = "MyClass"
        parent_cls.parent = MagicMock(spec=gf.Module)

        obj.parent = parent_cls

        mock_module = MagicMock(spec=["__name__"])
        mock_module.__name__ = "test_mod"
        del mock_module.MyClass

        obj.module = MagicMock()
        obj.module.canonical_path = "test_mod"

        with patch.object(introspect_mod, "importlib") as mock_il:
            mock_il.import_module.return_value = mock_module
            result = _locate_runtime_object(obj)

        assert result is None

    def test_final_getattr_attribute_error(self):
        """When parent class found but method not on it, returns None."""
        from great_docs._apiref.introspect import _locate_runtime_object

        obj = MagicMock(spec=gf.Function)
        obj.name = "missing_method"

        parent_cls = MagicMock(spec=gf.Class)
        parent_cls.name = "MyClass"
        parent_cls.parent = MagicMock(spec=gf.Module)

        obj.parent = parent_cls

        mock_cls = MagicMock(spec=["__name__"])
        mock_cls.__name__ = "MyClass"

        mock_module = MagicMock()
        mock_module.MyClass = mock_cls

        obj.module = MagicMock()
        obj.module.canonical_path = "test_mod"

        with patch.object(introspect_mod, "importlib") as mock_il:
            mock_il.import_module.return_value = mock_module
            result = _locate_runtime_object(obj)

        assert result is None


class TestPromoteCallableAttribute:
    def test_signature_extraction_fails(self):
        """ValueError/TypeError from inspect.signature is caught."""
        parent = gf.Module(name="mymod", filepath=None)
        attr = gf.Attribute(name="my_func", lineno=1, parent=parent)
        parent.set_member("my_func", attr)

        class BadCallable:
            pass

        bad = BadCallable()

        with patch("inspect.signature", side_effect=ValueError("no sig")):
            _promote_callable_attribute(attr, bad, "A docstring")

        assert isinstance(parent.members["my_func"], gf.Function)
        assert len(parent.members["my_func"].parameters) == 0


class TestDynamicAliasDeclarationOnly:
    def test_declaration_only_path(self):
        """When _locate_runtime_attr returns _DeclarationOnly, its obj is returned."""
        from great_docs._apiref.introspect import _DeclarationOnly, dynamic_alias

        mock_obj = MagicMock(spec=gf.Attribute)
        decl = _DeclarationOnly(obj=mock_obj)

        mock_module = MagicMock()
        with (
            patch.object(introspect_mod, "importlib") as mock_il,
            patch.object(introspect_mod, "_locate_runtime_attr", return_value=decl),
        ):
            mock_il.import_module.return_value = mock_module
            result = dynamic_alias("mod:attr", loader=MagicMock())

        assert result is mock_obj


class TestLocateDeclaration:
    def test_has_no_value_returns_declaration(self):
        """When static obj has no value, returns _DeclarationOnly."""
        from great_docs._apiref.introspect import _DeclarationOnly, _locate_declaration

        mock_obj = MagicMock(spec=gf.Attribute)

        with (
            patch("great_docs._apiref.introspect.get_object", return_value=mock_obj),
            patch("great_docs._apiref.introspect._has_no_value", return_value=True),
        ):
            result = _locate_declaration("mod.name", "name", "mod:name", MagicMock())

        assert isinstance(result, _DeclarationOnly)
        assert result.obj is mock_obj

    def test_has_value_raises_attribute_error(self):
        """When static obj has a value, raises AttributeError."""
        from great_docs._apiref.introspect import _locate_declaration

        mock_obj = MagicMock(spec=gf.Attribute)

        with (
            patch("great_docs._apiref.introspect.get_object", return_value=mock_obj),
            patch("great_docs._apiref.introspect._has_no_value", return_value=False),
        ):
            with pytest.raises(AttributeError, match="No attribute named"):
                _locate_declaration("mod.name", "name", "mod:name", MagicMock())


class TestCanonicalHome:
    def test_canonical_path_none_returns_none(self):
        """Returns None when located has no canonical_path."""
        from great_docs._apiref.introspect import _canonical_home

        located = MagicMock()
        located.canonical_path = None
        result = _canonical_home(located, MagicMock())
        assert result is None

    def test_get_object_raises_key_error(self):
        """Returns None when get_object raises KeyError."""
        from great_docs._apiref.introspect import _canonical_home

        located = MagicMock()
        located.canonical_path = "some.path"

        with patch("great_docs._apiref.introspect.get_object", side_effect=KeyError("nope")):
            result = _canonical_home(located, MagicMock())

        assert result is None

    def test_get_object_raises_import_error(self):
        """Returns None on ImportError."""
        from great_docs._apiref.introspect import _canonical_home

        located = MagicMock()
        located.canonical_path = "some.path"

        with patch("great_docs._apiref.introspect.get_object", side_effect=ImportError("nope")):
            result = _canonical_home(located, MagicMock())

        assert result is None


class TestAuthoredDocstring:
    def test_get_object_raises_key_error(self):
        """Returns None when get_object raises KeyError."""
        from great_docs._apiref.introspect import _authored_docstring

        with patch("great_docs._apiref.introspect.get_object", side_effect=KeyError("nope")):
            result = _authored_docstring("some.path", MagicMock())

        assert result is None

    def test_get_object_raises_import_error(self):
        """Returns None on ImportError."""
        from great_docs._apiref.introspect import _authored_docstring

        with patch("great_docs._apiref.introspect.get_object", side_effect=ImportError("nope")):
            result = _authored_docstring("some.path", MagicMock())

        assert result is None


class TestAliasIntoParent:
    def test_parent_is_module_creates_parented_alias(self):
        """When parent is a Module, creates alias with parent."""
        from great_docs._apiref.introspect import _alias_into_parent

        located = MagicMock()
        located.name = "my_attr"
        located.access_path = "pkg:my_attr"

        mock_parent = MagicMock(spec=gf.Module)
        mock_obj = MagicMock(spec=gf.Function)

        with patch("great_docs._apiref.introspect._access_parent", return_value=mock_parent):
            result = _alias_into_parent(located, mock_obj, MagicMock())

        assert isinstance(result, gf.Alias)
        assert result.name == "my_attr"

    def test_parent_not_module_class_creates_unparented_alias(self):
        """When parent is neither Module/Class/Alias, creates unparented alias."""
        from great_docs._apiref.introspect import _alias_into_parent

        located = MagicMock()
        located.name = "my_attr"
        located.access_path = "pkg:my_attr"

        mock_parent = MagicMock(spec=gf.Function)
        mock_obj = MagicMock(spec=gf.Function)

        with patch("great_docs._apiref.introspect._access_parent", return_value=mock_parent):
            result = _alias_into_parent(located, mock_obj, MagicMock())

        assert isinstance(result, gf.Alias)
        assert result.name == "my_attr"


class TestAccessParent:
    def test_object_path_none(self):
        """When object_path is None, uses module parent path."""
        from great_docs._apiref.introspect import _access_parent

        located = MagicMock()
        located.access_path = "pkg.sub"

        mock_obj = MagicMock(spec=gf.Module)

        with (
            patch(
                "great_docs._apiref.introspect._split_path",
                return_value=("pkg.sub", None),
            ),
            patch("great_docs._apiref.introspect.get_object", return_value=mock_obj) as mock_get,
        ):
            result = _access_parent(located, MagicMock())

        assert result is mock_obj
        mock_get.assert_called_once()
        assert mock_get.call_args[0][0] == "pkg"
        assert mock_get.call_args[1]["dynamic"] is True

    def test_object_path_with_dot(self):
        """When object_path has a dot, uses module:parent_class path."""
        from great_docs._apiref.introspect import _access_parent

        located = MagicMock()
        located.access_path = "pkg:MyClass.method"

        mock_obj = MagicMock(spec=gf.Class)

        with (
            patch(
                "great_docs._apiref.introspect._split_path",
                return_value=("pkg", "MyClass.method"),
            ),
            patch("great_docs._apiref.introspect.get_object", return_value=mock_obj) as mock_get,
        ):
            result = _access_parent(located, MagicMock())

        assert result is mock_obj
        mock_get.assert_called_once()
        assert mock_get.call_args[0][0] == "pkg:MyClass"
        assert mock_get.call_args[1]["dynamic"] is True
