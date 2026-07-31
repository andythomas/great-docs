"""
Griffe object access

The located `Object` / `Alias` nodes that model a package's public API — the
source of truth for every documented object's signature and docstring, loaded
and normalized from griffe's static analysis (with an optional dynamic-import
mode).
"""

from __future__ import annotations

import enum
import importlib
import inspect
import warnings
from dataclasses import dataclass
from types import ModuleType
from typing import TYPE_CHECKING, Callable, cast

import griffe as gf

if TYPE_CHECKING:
    from griffe import DocstringOptions

# Parser defaults ==============================================================

DEFAULT_OPTIONS: dict[str, dict[str, object]] = {}


def get_parser_defaults(name: str) -> dict[str, object]:
    """
    Get the default parser options registered for the named docstring style

    Parameters
    ----------
    name :
        Name of a docstring style, e.g. `numpy` or `google`.

    Returns
    -------
    :
        The registered options, or an empty dict when the style has none.
    """
    return DEFAULT_OPTIONS.get(name, {})


def make_loader(parser: str = "numpy") -> gf.GriffeLoader:
    """
    Configure a griffe loader with the defaults for a docstring parser

    Parameters
    ----------
    parser :
        Name of the docstring style the loader parses with.

    Returns
    -------
    :
        A loader with its own module and line collections, so it shares no
        cached state with any other loader.
    """
    raw_defaults = get_parser_defaults(parser)
    docstring_options = cast("DocstringOptions", raw_defaults) if raw_defaults else None
    return gf.GriffeLoader(
        docstring_parser=gf.Parser(parser),
        docstring_options=docstring_options,
        modules_collection=gf.ModulesCollection(),
        lines_collection=gf.LinesCollection(),
    )


# Docstring loading / parsing =================================================


def get_object(
    path: str,
    parser: str | None = None,
    dynamic: bool = False,
    loader: gf.GriffeLoader | None = None,
) -> gf.Object | gf.Alias:
    """
    Get the griffe object at the given import path

    Parameters
    ----------
    path :
        An import path to the object. This should have the form `path.to.module:object`.
        For example, `my_package:get_object` or `my_package:MyClass.render`.
    parser :
        A docstring parser to configure a new loader with. Ignored, with a warning,
        when `loader` is given, since the loader already carries a parser.
    dynamic :
        Whether to dynamically import the object. Useful when the docstring is not
        hard-coded, but was set on the object by running python code.
    loader :
        An existing griffe loader to reuse. A fresh loader is created when omitted.

    Returns
    -------
    :
        The node griffe models at `path` — an object, or an alias when the path
        reaches it through a re-export.
    """
    _validate_dynamic(dynamic)

    if loader is None:
        loader = make_loader(parser or "numpy")
    elif parser is not None:
        warnings.warn(
            f"Ignoring parser {parser!r} because `loader` was given; "
            "the loader already carries a docstring parser.",
            UserWarning,
            stacklevel=2,
        )

    module_path, object_path = _split_path(path)

    root_mod = module_path.split(".", 1)[0]
    if root_mod not in loader.modules_collection:
        _ = loader.load(module_path)

    if dynamic:
        return dynamic_alias(path, loader=loader)

    return _static_object(module_path, object_path, loader)


def _split_path(path: str) -> tuple[str, str | None]:
    """
    Split a `module:object` path into its module part and its object part

    Parameters
    ----------
    path :
        A path of the form `path.to.module:object`, or `path.to.module` alone.

    Returns
    -------
    :
        The module part, and the object part or `None` when the path names a
        module only.
    """
    module_path, _, object_path = path.partition(":")
    return module_path, object_path or None


def _static_object(
    module_path: str,
    object_path: str | None,
    loader: gf.GriffeLoader,
) -> gf.Object | gf.Alias:
    """
    The griffe object at a path, as griffe's static analysis models it

    An alias imported from elsewhere brings its target's module along, so the
    target can be resolved.

    Parameters
    ----------
    module_path :
        Dotted path of the module to read from.
    object_path :
        Dotted path of the object within that module, or `None` for the module
        itself.
    loader :
        Loader whose collection the module has already been loaded into.

    Returns
    -------
    :
        The node at the path. An imported name comes back as an alias, and a
        function or attribute reached through an aliased parent keeps that
        parent.

    Raises
    ------
    KeyError
        When the static model holds nothing at the path. The key names the
        object that was asked for, which callers turn into a user-facing error.
    """
    # griffe uses only periods for the path
    griffe_path = f"{module_path}.{object_path}" if object_path else module_path
    obj = loader.modules_collection[griffe_path]
    parent = loader.modules_collection[griffe_path.rsplit(".", 1)[0]]

    if isinstance(parent, gf.Alias) and isinstance(obj, (gf.Function, gf.Attribute)):
        obj = gf.Alias(obj.name, obj, parent=parent)

    if isinstance(obj, gf.Alias):
        target_mod = obj.target_path.split(".")[0]
        if target_mod != module_path:
            _ = loader.load(target_mod)

    return obj


def resolve_alias(
    obj: gf.Alias | gf.Object,
    get_object: Callable[..., gf.Object | gf.Alias] | None = None,
) -> gf.Object:
    """Resolve the alias chain to the concrete `Object` at its end

    Follows `Alias.target` links until a non-alias node is reached. An
    unresolved link is re-loaded through `get_object` when one is provided;
    otherwise the `AliasResolutionError` propagates.

    Parameters
    ----------
    obj :
        The node to resolve. One that is not an alias is returned unchanged.
    get_object :
        Callable used to re-load a link whose target is absent from the
        collection. When omitted, such a link raises instead.

    Returns
    -------
    :
        The concrete object at the end of the chain.

    Raises
    ------
    ValueError
        When the chain appears to be infinitely recursive (> 100 hops).
    """
    count = 0
    while isinstance(obj, gf.Alias):
        count += 1
        if count > 100:
            raise ValueError("Attempted to resolve target, but may be infinitely recursing?")

        try:
            obj = obj.target
        except gf.AliasResolutionError as e:
            if get_object is None:
                raise
            obj = get_object(e.alias.target_path)

    return obj


def replace_docstring(obj: gf.Object | gf.Alias, runtime_obj: object = None) -> None:
    """
    Replace the griffe object's docstring in place with the imported runtime docstring

    Callable attributes (the `method = some_function` pattern) are also
    promoted to functions so they render with a signature.

    Parameters
    ----------
    obj :
        Object whose docstring is replaced.
    runtime_obj :
        The python object whose docstring to use in the replacement. If not
        specified, then attempt to import obj and use its docstring.
    """
    if isinstance(obj, gf.Alias):
        obj = resolve_alias(obj)

    if isinstance(obj, gf.Class):
        for child_obj in obj.members.values():
            replace_docstring(child_obj)

    if runtime_obj is None:
        runtime_obj = _locate_runtime_object(obj)
        if runtime_obj is None:
            return

    if getattr(runtime_obj, "__doc__", None) is None:
        return

    doc: str = runtime_obj.__doc__  # type: ignore[assignment]

    # Enum members inherit __doc__ from the enum class. Skip the
    # replacement so griffe's statically-parsed per-member docstring
    # (if any) is preserved; when there is none the member correctly
    # shows no docstring rather than the class-level one.
    if isinstance(runtime_obj, enum.Enum):
        parent_cls = type(runtime_obj)
        if doc == parent_cls.__doc__:
            return

    # Reclassify callable attributes as functions.
    # When a class uses `method = some_function` pattern, griffe sees it as
    # Kind.ATTRIBUTE. If the runtime value is actually a function, promote it
    # to a Function object so it gets proper function-style rendering.
    if (
        isinstance(obj, gf.Attribute)
        and callable(runtime_obj)
        and hasattr(runtime_obj, "__code__")
        and obj.parent is not None
    ):
        _promote_callable_attribute(obj, runtime_obj, doc)
        return

    old = obj.docstring
    obj.docstring = _clone_docstring(old, doc, getattr(old, "parent", None))


def _locate_runtime_object(obj: gf.Object) -> object | None:
    """
    Locate the imported runtime object that `obj` documents, or return None if unreachable

    A member of a (possibly nested) class is reached by walking the class
    chain, e.g. `Node.add_child` inside `Tree` resolves to
    `mod.Tree.Node.add_child`.

    Parameters
    ----------
    obj :
        The documented node whose runtime counterpart is wanted.

    Returns
    -------
    :
        The imported object, or `None` when the class chain or the attribute
        itself cannot be reached at runtime.
    """
    mod = importlib.import_module(obj.module.canonical_path)

    if not isinstance(obj.parent, gf.Class):
        return getattr(mod, obj.name)

    parent_chain: list[str] = []
    p: gf.Object | gf.Alias | None = obj.parent
    while isinstance(p, gf.Class):
        parent_chain.append(p.name)
        p = p.parent
    parent_chain.reverse()

    try:
        parent_obj: object = mod
        for attr_name in parent_chain:
            parent_obj = getattr(parent_obj, attr_name)
    except AttributeError:
        return None

    try:
        return getattr(parent_obj, obj.name)
    except AttributeError:
        return None


def _promote_callable_attribute(obj: gf.Attribute, f: object, doc: str) -> None:
    """
    Re-register the attribute on its parent as a `gf.Function`

    The function carries the runtime signature when it is recoverable, so
    the member renders function-style instead of attribute-style.

    Parameters
    ----------
    obj :
        The attribute to replace on its parent.
    f :
        The runtime callable the attribute holds. Its signature is copied when
        `inspect` can read it, and omitted when it cannot.
    doc :
        Docstring for the replacement function.
    """
    assert obj.parent is not None

    func_obj = gf.Function(
        name=obj.name,
        lineno=obj.lineno,
        endlineno=obj.endlineno,
        parent=obj.parent,
    )
    # Extract parameters from runtime signature
    try:
        sig = inspect.signature(cast("type", f))
        params: list[gf.Parameter] = []
        _kind_map = {
            inspect.Parameter.POSITIONAL_ONLY: gf.ParameterKind.positional_only,
            inspect.Parameter.POSITIONAL_OR_KEYWORD: gf.ParameterKind.positional_or_keyword,
            inspect.Parameter.VAR_POSITIONAL: gf.ParameterKind.var_positional,
            inspect.Parameter.KEYWORD_ONLY: gf.ParameterKind.keyword_only,
            inspect.Parameter.VAR_KEYWORD: gf.ParameterKind.var_keyword,
        }
        for pname, param in sig.parameters.items():
            kind = _kind_map.get(param.kind, gf.ParameterKind.positional_or_keyword)
            default = str(param.default) if param.default is not inspect.Parameter.empty else None
            params.append(gf.Parameter(name=pname, kind=kind, default=default))
        func_obj.parameters = gf.Parameters(*params)
    except (ValueError, TypeError):
        pass

    func_obj.docstring = _clone_docstring(obj.docstring, doc, func_obj)
    obj.parent.set_member(obj.name, func_obj)


def _clone_docstring(
    old: gf.Docstring | None, value: str, parent: gf.Object | None
) -> gf.Docstring:
    """
    Clone a docstring with a new value, keeping the old one's position and parser

    Parameters
    ----------
    old :
        Docstring to copy the position and parser settings from. `None` yields
        a docstring with no position.
    value :
        Text of the new docstring.
    parent :
        Node the new docstring belongs to.

    Returns
    -------
    :
        A docstring carrying `value`.
    """
    return gf.Docstring(
        value=value,
        lineno=getattr(old, "lineno", None),
        endlineno=getattr(old, "endlineno", None),
        parent=parent,
        parser=getattr(old, "parser", None),
        parser_options=getattr(old, "parser_options", None),
    )


@dataclass(frozen=True)
class _LocatedAttr:
    """
    A runtime attribute reached by walking an access path

    `canonical_path` is `None` when the attribute does not report where it
    lives, leaving `access_path` the only path known for it.
    """

    value: object
    name: str
    access_path: str
    canonical_path: str | None


@dataclass(frozen=True)
class _DeclarationOnly:
    """A path that names a declaration carrying no runtime value, e.g. an instance attribute"""

    obj: gf.Object | gf.Alias


@dataclass(frozen=True)
class _Documented:
    """The griffe object documenting an attribute, and the path it was loaded from"""

    obj: gf.Object | gf.Alias
    path: str


def _same_path(one: str, other: str) -> bool:
    """
    Whether two paths name the same object, ignoring the `:` / `.` separator

    Parameters
    ----------
    one, other :
        Paths to compare, each in either `module:object` or dotted form.

    Returns
    -------
    :
        True when both name the same object.
    """
    return one.replace(":", ".") == other.replace(":", ".")


def dynamic_alias(
    path: str,
    loader: gf.GriffeLoader | None = None,
) -> gf.Object | gf.Alias:
    """
    Resolve a griffe object for `path` via a dynamic import

    Parameters
    ----------
    path :
        Full path to the object. E.g. `my_package.get_object`.
    loader :
        An existing griffe loader to reuse. A fresh loader is created when omitted.

    Returns
    -------
    :
        The node griffe models at `path`, carrying the runtime docstring. It
        comes back as an alias member of the thing it was accessed through only
        when it lives somewhere else.
    """
    module_path, object_path = _split_path(path)
    module = importlib.import_module(module_path)

    located = _locate_runtime_attr(module, module_path, object_path, path, loader)
    if isinstance(located, _DeclarationOnly):
        return located.obj

    documented = _load_documenting_object(located, loader)
    replace_docstring(documented.obj, located.value)

    if _same_path(documented.path, located.access_path):
        return documented.obj
    return _alias_into_parent(located, documented.obj, loader)


def _locate_runtime_attr(
    module: ModuleType,
    module_path: str,
    object_path: str | None,
    path: str,
    loader: gf.GriffeLoader | None,
) -> _LocatedAttr | _DeclarationOnly:
    """
    Walk `object_path` from `module` to the runtime attribute it names

    Parameters
    ----------
    module :
        The already-imported module the walk starts from.
    module_path :
        Dotted path `module` was imported by.
    object_path :
        Dotted path of the attribute within the module, or `None` for the
        module itself.
    path :
        The full path as written, used in error messages.
    loader :
        Loader to read the static model through when the walk finds no runtime
        value.

    Returns
    -------
    :
        The attribute together with the paths it is known by, or the static node
        when the path names a declaration that holds no runtime value.

    Raises
    ------
    KeyError
        When the path names neither a runtime attribute nor a declaration,
        from the static lookup that `_locate_declaration` falls back to.
    ImportError
        When that static lookup needs a module that cannot be loaded.
    AttributeError
        The narrower case of a missing runtime attribute: raised only when
        the static model DOES carry a value for it, so the absence is a
        genuine error rather than a declaration to fall back to.
    """
    if object_path is None:
        return _LocatedAttr(module, module_path.rsplit(".", 1)[-1], module_path, module.__name__)

    names = object_path.split(".")
    value: object = module
    canonical_path: str | None = None

    for index, name in enumerate(names):
        home = _canonical_path(value, ".".join(names[index:]))
        if home is not None:
            canonical_path = home

        try:
            value = getattr(value, name)
        except AttributeError:
            return _locate_declaration(canonical_path or path, name, path, loader)

    home = _canonical_path(value, "")
    if home is not None:
        canonical_path = home

    return _LocatedAttr(value, names[-1], path, canonical_path)


def _locate_declaration(
    static_path: str,
    name: str,
    path: str,
    loader: gf.GriffeLoader | None,
) -> _DeclarationOnly:
    """
    Fall back to griffe's static model for an attribute with no runtime value

    Parameters
    ----------
    static_path :
        Path to read the static model at.
    name :
        Name of the attribute that was missing at runtime, for the error
        message.
    path :
        The full path as written, for the error message.
    loader :
        Loader to read the static model through.

    Returns
    -------
    :
        The static node, when it is a declaration that carries no value of its
        own.

    Raises
    ------
    AttributeError
        When the static model does carry a value, so the missing runtime
        attribute is a genuine absence rather than a declaration.
    """
    obj = get_object(static_path, loader=loader)
    if _has_no_value(obj):
        return _DeclarationOnly(obj)
    raise AttributeError(f"No attribute named `{name}` in the path `{path}`.")


def _load_documenting_object(
    located: _LocatedAttr,
    loader: gf.GriffeLoader | None,
) -> _Documented:
    """
    Load the griffe object that documents `located`

    Prefers the attribute's canonical home, falling back to the path it was
    accessed by. The fallback covers both an attribute that cannot report a
    home and one whose `__module__` names a module that cannot be imported,
    typical of PyO3 classes whose Rust `#[pyclass]` lacks `module = "..."` so
    `__module__` defaults to `"builtins"`.

    Parameters
    ----------
    located :
        The attribute whose documentation is wanted.
    loader :
        Loader to read the static model through.

    Returns
    -------
    :
        The node that documents the attribute, and the path it was read from.
        Callers compare that path against the access path to decide whether the
        attribute still needs re-exposing.
    """
    if located.canonical_path is not None:
        try:
            obj = get_object(located.canonical_path, loader=loader)
        except (KeyError, ModuleNotFoundError, ImportError):
            pass
        else:
            return _Documented(obj, located.canonical_path)

    return _Documented(get_object(located.access_path, loader=loader), located.access_path)


def _alias_into_parent(
    located: _LocatedAttr,
    obj: gf.Object | gf.Alias,
    loader: gf.GriffeLoader | None,
) -> gf.Alias:
    """
    Re-expose `obj` as an alias member of the object it was accessed through

    Only called when the object lives somewhere other than where it was
    accessed, so the alias can never target its own path.

    Parameters
    ----------
    located :
        The attribute as it was reached. Its access path names the parent, and
        its name becomes the alias's name.
    obj :
        The node to re-expose.
    loader :
        Loader to read the parent through.

    Returns
    -------
    :
        An alias named after the accessed attribute, parented to the module or
        class it was reached through. It is left unparented when the access path
        names something that cannot hold members.
    """
    module_path, object_path = _split_path(located.access_path)

    if object_path is None:
        parent_path = module_path.rsplit(".", 1)[0]
    elif "." in object_path:
        parent_path = f"{module_path}:{object_path.rsplit('.', 1)[0]}"
    else:
        parent_path = module_path

    parent = get_object(parent_path, loader=loader, dynamic=True)
    if isinstance(parent, (gf.Module, gf.Class, gf.Alias)):
        return gf.Alias(located.name, obj, parent=parent)
    return gf.Alias(located.name, obj)


def _canonical_path(current_part: object, qualname: str) -> str | None:
    """
    The path at which `current_part` reports it lives, extended by `qualname`

    `None` when the object reports no home. A module knows its own `__name__`
    but not where its members were defined, so it reports a home only for
    itself. Plain instances carry no `__qualname__` of their own.

    Parameters
    ----------
    current_part :
        The runtime object to ask.
    qualname :
        Dotted names to append to the reported home, empty for the object
        itself.

    Returns
    -------
    :
        The reported path in `module:qualname` form, or `None` when the object
        reports no home.
    """
    if isinstance(current_part, ModuleType):
        return None if qualname else current_part.__name__

    module = getattr(current_part, "__module__", None)
    qualified = getattr(current_part, "__qualname__", None)

    # `callable` rather than `inspect.isfunction` so that PyO3 / C-extension
    # callables (`builtin_function_or_method`, `method-wrapper`) report their
    # canonical home too.
    if not (module and qualified and callable(current_part)):
        return None

    qual_parts = qualname.split(".") if qualname else []
    return module + ":" + ".".join([qualified, *qual_parts])


def _has_no_value(obj: gf.Object | gf.Alias) -> bool:
    """
    Whether `obj` is an attribute that carries no runtime value

    True for class/module attributes with no assigned value, and for
    all instance attributes (which are declaration-only in griffe's static
    model).

    Parameters
    ----------
    obj :
        The node to test. Anything that is not an attribute is False.

    Returns
    -------
    :
        True when the attribute carries no value of its own.
    """
    if isinstance(obj, gf.Attribute):
        if obj.labels & {"class-attribute", "module-attribute"} and obj.value is None:
            return True
        elif "instance-attribute" in obj.labels:
            return True

    return False


def _validate_dynamic(value: object, *, allow_none: bool = False) -> None:
    if isinstance(value, bool) or (allow_none and value is None):
        return
    raise ValueError(
        f"`dynamic` accepts true or false, got {value!r}. "
        "It selects how an object is inspected, not what it points to."
    )
