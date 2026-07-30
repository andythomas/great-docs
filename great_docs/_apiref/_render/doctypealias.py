from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from great_docs.pandoc.blocks import Blocks, Div
from great_docs.pandoc.components import Attr
from great_docs.pandoc.inlines import Code, Inlines0, Span

from ._type_parameters import render_type_parameters
from .doc import RenderDoc

if TYPE_CHECKING:
    import griffe as gf

    from great_docs.pandoc.blocks import BlockContent
    from great_docs.pandoc.inlines import InlineContentItem

    from .. import content

# `obj.kind.value` is "type alias", with a space; used bare it would split into
# two CSS classes, the second colliding with the `alias` kind.
_KIND_SLUG = "type-alias"


@dataclass
class __RenderDocTypeAlias(RenderDoc):
    """
    Render documentation for a PEP 695 type alias (`content.DocTypeAlias`)
    """

    def __post_init__(self):
        super().__post_init__()
        # We narrow the type with a TypeAlias since we do not expect
        # any subclasses to have narrower types
        self.doc: content.DocTypeAlias = self.doc
        self.obj: gf.TypeAlias = self.obj

        self.subject_above_signature = self.subject_above_signature is None and not self.contained

    def render_signature(self) -> BlockContent:
        """
        Render the alias in its source form, e.g. `type Pair[T] = tuple[T, T]`
        """
        name = self.signature_name if self.show_signature_name else ""
        declared = f"{name}{render_type_parameters(self.obj.type_parameters)}"

        items: list[InlineContentItem] = [
            Span("type", Attr(classes=[f"doc-{_KIND_SLUG}-keyword", "kw"])),
            " ",
            Span(declared, Attr(classes=["doc-parameter-name"])),
            " ",
            Span("=", Attr(classes=["doc-parameter-default-sep", "op"])),
            " ",
            Span(str(self.obj.value), Attr(classes=["doc-parameter-default"])),
        ]

        return Div(
            Code(str(Inlines0(items))).html,
            Attr(classes=["doc-signature", f"doc-{_KIND_SLUG}"]),
        )

    def render_description(self) -> BlockContent:
        """
        Render description for type aliases: subject above signature, no Usage label
        """
        return Blocks(
            [
                self.render_docstring_subject(),
                self.render_signature() if self.show_signature else None,
            ]
        )


class RenderDocTypeAlias(__RenderDocTypeAlias):
    """
    Extension point for the rendering of a `content.DocTypeAlias` object
    """
