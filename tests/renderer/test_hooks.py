import griffe as gf
import pytest

from great_docs import hooks
from great_docs.hooks import _docstring_parsed, _object_resolved


@pytest.fixture
def clean_hooks():
    """Preserve the registered pipeline handlers across an isolated test"""
    registries = (_object_resolved.REGISTRY, _docstring_parsed.REGISTRY)
    saved = [(list(reg._entries), reg._sequence) for reg in registries]
    for reg in registries:
        reg.clear()
    yield
    for reg, (entries, sequence) in zip(registries, saved):
        reg._entries[:] = entries
        reg._sequence = sequence
        reg._ordered = None


def test_only_registration_decorators_are_exported():
    assert hooks.__all__ == ["on_docstring_parsed", "on_object_resolved"]


def test_emit_object_resolved_threads_object_through_handlers(clean_hooks):
    seen: list[str] = []

    @hooks.on_object_resolved
    def annotate(obj):
        seen.append(obj)
        return f"{obj}!"

    assert _object_resolved.emit_object_resolved("X") == "X!"
    assert seen == ["X"]


def test_emit_object_resolved_none_skips_and_short_circuits(clean_hooks):
    calls: list[str] = []

    @hooks.on_object_resolved
    def drop(obj):
        calls.append("drop")
        return None

    @hooks.on_object_resolved
    def never(obj):
        calls.append("never")
        return obj

    assert _object_resolved.emit_object_resolved("X") is None
    assert calls == ["drop"]


def test_on_object_resolved_returns_the_handler(clean_hooks):
    def h(obj):
        return obj

    assert hooks.on_object_resolved(h) is h


def test_emit_object_resolved_with_no_handlers_is_identity(clean_hooks):
    sentinel = object()
    assert _object_resolved.emit_object_resolved(sentinel) is sentinel


def test_bare_decorator_registers_the_hook(clean_hooks):
    @hooks.on_object_resolved
    def h(obj):
        return obj

    assert h in _object_resolved.REGISTRY
    assert list(_object_resolved.REGISTRY) == [h]


def test_priority_orders_emit_low_to_high(clean_hooks):
    order: list[str] = []

    @hooks.on_object_resolved(priority=100)
    def late(obj):
        order.append("late")
        return obj

    @hooks.on_object_resolved(priority=-100)
    def early(obj):
        order.append("early")
        return obj

    @hooks.on_object_resolved
    def mid(obj):
        order.append("mid")
        return obj

    _object_resolved.emit_object_resolved("X")
    assert order == ["early", "mid", "late"]


def test_low_priority_none_short_circuits_before_high(clean_hooks):
    calls: list[str] = []

    @hooks.on_object_resolved(priority=100)
    def never(obj):
        calls.append("never")
        return obj

    @hooks.on_object_resolved(priority=-100)
    def drop(obj):
        calls.append("drop")
        return None

    assert _object_resolved.emit_object_resolved("X") is None
    assert calls == ["drop"]


def test_object_resolved_invalidates_final_docstring_parse(clean_hooks):
    obj = gf.Function("f")
    obj.docstring = gf.Docstring("Before.", parent=obj, parser="numpy")
    obj.docstring.__dict__["parsed"] = [gf.DocstringSectionText("stale")]

    @hooks.on_object_resolved
    def revise(value):
        value.docstring.value = "After."
        return value

    result = _object_resolved.emit_object_resolved(obj)

    assert result is obj
    assert "parsed" not in obj.docstring.__dict__


def test_object_resolved_invalidates_cache_read_by_handler(clean_hooks):
    obj = gf.Function("f")
    obj.docstring = gf.Docstring("Summary.", parent=obj, parser="numpy")

    @hooks.on_object_resolved
    def inspect(value):
        assert value.docstring.parsed
        return value

    _object_resolved.emit_object_resolved(obj)

    assert "parsed" not in obj.docstring.__dict__


def test_emit_docstring_parsed_threads_and_caches_sections(clean_hooks):
    obj = gf.Function("f")
    obj.docstring = gf.Docstring("Summary.", parent=obj, parser="numpy")

    @hooks.on_docstring_parsed
    def append_section(value, sections):
        assert value is obj
        return [*sections, gf.DocstringSectionText("More.")]

    result = _docstring_parsed.emit_docstring_parsed(obj)

    assert [section.value for section in result] == ["Summary.", "More."]
    assert obj.docstring.__dict__["parsed"] is result


def test_docstring_parsed_rejects_none(clean_hooks):
    obj = gf.Function("f")
    obj.docstring = gf.Docstring("Summary.", parent=obj, parser="numpy")

    @hooks.on_docstring_parsed
    def invalid(value, sections):
        return None

    with pytest.raises(TypeError, match="returned None"):
        _docstring_parsed.emit_docstring_parsed(obj)


def test_docstring_parsed_rejects_object_without_docstring(clean_hooks):
    with pytest.raises(ValueError, match="without a docstring"):
        _docstring_parsed.emit_docstring_parsed(gf.Function("f"))


def test_docstring_parsed_keeps_empty_section_list(clean_hooks):
    obj = gf.Function("f")
    obj.docstring = gf.Docstring("Summary.", parent=obj, parser="numpy")

    @hooks.on_docstring_parsed
    def remove_body(value, sections):
        return []

    assert _docstring_parsed.emit_docstring_parsed(obj) == []
    assert obj.docstring.__dict__["parsed"] == []


def test_docstring_parsed_orders_handlers_by_priority(clean_hooks):
    obj = gf.Function("f")
    obj.docstring = gf.Docstring("Summary.", parent=obj, parser="numpy")
    calls: list[str] = []

    @hooks.on_docstring_parsed(priority=100)
    def late(value, sections):
        calls.append("late")
        return sections

    @hooks.on_docstring_parsed(priority=-100)
    def early(value, sections):
        calls.append("early")
        return sections

    _docstring_parsed.emit_docstring_parsed(obj)

    assert calls == ["early", "late"]
