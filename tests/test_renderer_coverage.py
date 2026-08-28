"""Tests targeting missed coverage lines in _term_player/renderer.py."""

from __future__ import annotations

from great_docs._term_player.emulator import Cell, CellStyle, ScreenState, TerminalEmulator
from great_docs._term_player.parser import Theme
from great_docs._term_player.renderer import (
    _collect_bg_spans,
    _index_to_color,
    _render_chrome,
    _resolve_bg,
    _style_classes,
    render_frame,
)


# ---------------------------------------------------------------------------
# render_frame with colored background cells
# ---------------------------------------------------------------------------


class TestRenderFrameBgSpans:
    def test_cell_with_bg_color_produces_rect(self):
        """Cells with non-default background produce <rect> elements."""
        emu = TerminalEmulator(cols=10, rows=3)

        # Set a green background on some text
        emu.feed("\x1b[42mHello\x1b[0m")
        svg = render_frame(emu.screen)

        # Should contain a rect for the background span (not the full-frame rect)
        # Count rects: one is the frame bg, additional ones are cell bgs
        assert svg.count("<rect") > 1

    def test_contiguous_bg_spans_merged(self):
        """Multiple cells with same bg produce one rect span."""
        emu = TerminalEmulator(cols=10, rows=3)
        emu.feed("\x1b[44mABC\x1b[0m")
        svg = render_frame(emu.screen, show_cursor=False)

        # Frame bg rect + one span rect for the 3-char blue background
        assert svg.count("<rect") == 2


# ---------------------------------------------------------------------------
# _render_chrome function (minimal and colorful)
# ---------------------------------------------------------------------------


class TestRenderChrome:
    def test_minimal_chrome(self):
        """Minimal chrome produces circles and rects."""
        theme = Theme()
        result = _render_chrome("minimal", 400.0, theme)

        assert "circle" in result
        assert "#585b70" in result
        assert "rect" in result

    def test_colorful_chrome(self):
        """Colorful chrome produces colored traffic light circles."""
        theme = Theme()
        result = _render_chrome("colorful", 400.0, theme)

        assert "circle" in result
        assert "#f38ba8" in result  # Close (red)
        assert "#f9e2af" in result  # Minimize (yellow)
        assert "#a6e3a1" in result  # Maximize (green)

    def test_none_chrome_returns_empty(self):
        """Style 'none' (or any other) returns empty string."""
        theme = Theme()
        result = _render_chrome("none", 400.0, theme)

        assert result == ""


# ---------------------------------------------------------------------------
# _collect_bg_spans — contiguous cells extending a span
# ---------------------------------------------------------------------------


class TestCollectBgSpansContiguous:
    def test_contiguous_same_bg_extends_span(self):
        """Multiple cells with same bg are merged into one span."""
        theme = Theme()
        style_bg = CellStyle(bg="#ff0000")
        row = [
            Cell(char="A", style=style_bg.copy()),
            Cell(char="B", style=style_bg.copy()),
            Cell(char="C", style=style_bg.copy()),
            Cell(char=" ", style=CellStyle()),
        ]
        spans = _collect_bg_spans(row, theme)

        assert len(spans) == 1
        assert spans[0] == (0, 3, "#ff0000")

    def test_different_bg_splits_spans(self):
        """Different bg colors produce separate spans."""
        theme = Theme()
        row = [
            Cell(char="A", style=CellStyle(bg="#ff0000")),
            Cell(char="B", style=CellStyle(bg="#00ff00")),
            Cell(char="C", style=CellStyle()),
        ]
        spans = _collect_bg_spans(row, theme)

        assert len(spans) == 2
        assert spans[0] == (0, 1, "#ff0000")
        assert spans[1] == (1, 1, "#00ff00")


# ---------------------------------------------------------------------------
# _resolve_bg with inverse mode
# ---------------------------------------------------------------------------


class TestResolveBgInverse:
    def test_inverse_with_explicit_fg(self):
        """Inverse mode with fg set uses fg color as background."""
        theme = Theme()
        cell = Cell(char="X", style=CellStyle(inverse=True, fg="#ff0000"))
        result = _resolve_bg(cell, theme)

        assert result == "#ff0000"

    def test_inverse_no_fg_uses_theme_fg(self):
        """Inverse mode with no fg uses theme's foreground as background."""
        theme = Theme(fg="#aabbcc", bg="#112233")
        cell = Cell(char="X", style=CellStyle(inverse=True))
        result = _resolve_bg(cell, theme)

        assert result == "#aabbcc"

    def test_inverse_fg_same_as_theme_bg_returns_none(self):
        """Inverse where resolved fg == theme bg returns None."""
        theme = Theme(fg="#aabbcc", bg="#112233")
        cell = Cell(char="X", style=CellStyle(inverse=True, fg="#112233"))
        result = _resolve_bg(cell, theme)

        assert result is None

    def test_inverse_no_fg_same_as_bg_returns_none(self):
        """Inverse where theme.fg == theme.bg returns None."""
        theme = Theme(fg="#111111", bg="#111111")
        cell = Cell(char="X", style=CellStyle(inverse=True))
        result = _resolve_bg(cell, theme)

        assert result is None


# ---------------------------------------------------------------------------
# _index_to_color — index >= palette but < 16, and fallback
# ---------------------------------------------------------------------------


class TestIndexToColorExtended:
    def test_index_beyond_palette_but_within_16(self):
        """Index >= palette length but < 16 uses ANSI_COLORS_16."""
        # Create theme with only 4 palette entries
        theme = Theme(palette=["#000", "#111", "#222", "#333"])
        result = _index_to_color("8", theme)
        from great_docs._term_player.emulator import ANSI_COLORS_16

        assert result == ANSI_COLORS_16[8]

    def test_index_beyond_16_returns_theme_fg(self):
        """Index >= 16 falls through to theme.fg."""
        theme = Theme(fg="#facade", palette=["#000"] * 4)
        result = _index_to_color("20", theme)

        assert result == "#facade"


# ---------------------------------------------------------------------------
# _style_classes — strikethrough
# ---------------------------------------------------------------------------


class TestStyleClassesStrikethrough:
    def test_strikethrough_class(self):
        """Strikethrough style produces the correct CSS class."""
        style = CellStyle(strikethrough=True)
        result = _style_classes(style)

        assert "gd-tp-strikethrough" in result

    def test_strikethrough_combined(self):
        """Strikethrough combined with other styles."""
        style = CellStyle(bold=True, strikethrough=True)
        result = _style_classes(style)

        assert "gd-tp-bold" in result
        assert "gd-tp-strikethrough" in result
