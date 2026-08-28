"""Tests targeting _term_player/emulator.py."""

from __future__ import annotations

from great_docs._term_player.emulator import Cell, CellStyle, TerminalEmulator


def _screen_text(emu: TerminalEmulator, row: int) -> str:
    state = emu.screen
    return "".join(cell.char for cell in state.cells[row]).rstrip()


# ---------------------------------------------------------------------------
# OSC sequences
# ---------------------------------------------------------------------------


class TestOSCSequences:
    def test_osc_complete_sequence_skipped(self):
        """Complete OSC sequence (e.g., set title) is silently consumed."""
        emu = TerminalEmulator(cols=80, rows=24)

        # OSC sequence terminated by ST (\x1b\\)
        emu.feed("\x1b]0;Window Title\x1b\\Hello")

        assert _screen_text(emu, 0) == "Hello"

    def test_osc_bel_terminated(self):
        """OSC terminated by BEL (\x07)."""
        emu = TerminalEmulator(cols=80, rows=24)
        emu.feed("\x1b]2;Title\x07World")

        assert _screen_text(emu, 0) == "World"

    def test_osc_incomplete_skips_to_end(self):
        """Incomplete OSC (no terminator) skips rest of data."""
        emu = TerminalEmulator(cols=80, rows=24)

        # OSC with no terminator (should skip to end of data)
        emu.feed("\x1b]9999")

        assert _screen_text(emu, 0) == ""


# ---------------------------------------------------------------------------
# Unknown escape sequences
# ---------------------------------------------------------------------------


class TestUnknownEscape:
    def test_unknown_escape_skips_two_chars(self):
        """Unknown escape sequence skips ESC + next character."""
        emu = TerminalEmulator(cols=80, rows=24)

        # ESC followed by an unrecognized character (e.g., 'Z')
        emu.feed("\x1bZHello")

        assert _screen_text(emu, 0) == "Hello"

    def test_unknown_escape_mid_text(self):
        """Unknown escape in the middle of text."""
        emu = TerminalEmulator(cols=80, rows=24)
        emu.feed("AB\x1b#CD")

        assert _screen_text(emu, 0) == "ABCD"


# ---------------------------------------------------------------------------
# Bell character
# ---------------------------------------------------------------------------


class TestBellCharacter:
    def test_bell_ignored(self):
        """Bell character (\\x07) is silently ignored."""
        emu = TerminalEmulator(cols=80, rows=24)
        emu.feed("A\x07B")

        assert _screen_text(emu, 0) == "AB"


# ---------------------------------------------------------------------------
# Other control characters
# ---------------------------------------------------------------------------


class TestOtherControlChars:
    def test_control_chars_skipped(self):
        """Control characters (< 0x20) other than CR/LF/BS/Tab/Bell/ESC are skipped."""
        emu = TerminalEmulator(cols=80, rows=24)

        # \x01 (SOH), \x02 (STX), \x0e (SO), \x0f (SI) — all should be skipped
        emu.feed("A\x01\x02\x0e\x0fB")

        assert _screen_text(emu, 0) == "AB"

    def test_vertical_tab_skipped(self):
        """Vertical tab (\\x0b) and form feed (\\x0c) are control chars."""
        emu = TerminalEmulator(cols=80, rows=24)
        emu.feed("X\x0b\x0cY")

        assert _screen_text(emu, 0) == "XY"


# ---------------------------------------------------------------------------
# ESC M (Reverse Index) and ESC D (Index)
# ---------------------------------------------------------------------------


class TestEscSimpleSequences:
    def test_reverse_index_at_top_scrolls_down(self):
        """ESC M at scroll top inserts a blank line (scroll down)."""
        emu = TerminalEmulator(cols=80, rows=5)
        emu.feed("line1\r\nline2\r\nline3")

        # Move cursor to row 0
        emu.feed("\x1b[1;1H")

        # ESC M (reverse index) at top should scroll down
        emu.feed("\x1bM")

        # Row 0 should now be blank, line1 moved to row 1
        assert _screen_text(emu, 0) == ""
        assert _screen_text(emu, 1) == "line1"

    def test_reverse_index_not_at_top_moves_up(self):
        """ESC M when cursor is not at scroll top just moves cursor up."""
        emu = TerminalEmulator(cols=80, rows=5)
        emu.feed("line1\r\nline2")

        # Cursor is at row 1 after typing line2
        state = emu.screen

        assert state.cursor_row == 1

        # ESC M should move cursor up
        emu.feed("\x1bM")
        state = emu.screen

        assert state.cursor_row == 0

    def test_esc_d_index_linefeed(self):
        """ESC D performs a linefeed (index)."""
        emu = TerminalEmulator(cols=80, rows=5)
        emu.feed("Hello")
        emu.feed("\x1bD")
        state = emu.screen

        assert state.cursor_row == 1


# ---------------------------------------------------------------------------
# Alt screen mode 47/1047
# ---------------------------------------------------------------------------


class TestAltScreen47:
    def test_alt_screen_47_enter(self):
        """Mode 47 enters alt screen buffer."""
        emu = TerminalEmulator(cols=80, rows=5)
        emu.feed("Main content")

        # Enter alt screen via mode 47
        emu.feed("\x1b[?47h")

        # Alt screen should be blank
        assert _screen_text(emu, 0) == ""

    def test_alt_screen_47_exit(self):
        """Mode 47 exit restores main screen."""
        emu = TerminalEmulator(cols=80, rows=5)
        emu.feed("Main")

        # Enter alt screen
        emu.feed("\x1b[?47h")
        emu.feed("Alt text")

        # Exit alt screen
        emu.feed("\x1b[?47l")

        assert _screen_text(emu, 0) == "Main"

    def test_alt_screen_1047_enter_exit(self):
        """Mode 1047 also controls alt screen."""
        emu = TerminalEmulator(cols=80, rows=5)
        emu.feed("Original")
        emu.feed("\x1b[?1047h")

        assert _screen_text(emu, 0) == ""

        emu.feed("\x1b[?1047l")

        assert _screen_text(emu, 0) == "Original"


# ---------------------------------------------------------------------------
# SGR attributes — missed branches
# ---------------------------------------------------------------------------


class TestSGRMissedBranches:
    def test_sgr_empty_params_resets(self):
        """SGR with no params (ESC[m) resets attributes."""
        emu = TerminalEmulator(cols=80, rows=24)
        emu.feed("\x1b[1mBold\x1b[mNormal")
        state = emu.screen

        # Cell at "N" (index 4) should not be bold
        assert state.cells[0][4].style.bold is False

    def test_sgr_dim(self):
        """SGR 2 sets dim."""
        emu = TerminalEmulator(cols=80, rows=24)
        emu.feed("\x1b[2mD")
        state = emu.screen

        assert state.cells[0][0].style.dim is True

    def test_sgr_strikethrough(self):
        """SGR 9 sets strikethrough."""
        emu = TerminalEmulator(cols=80, rows=24)
        emu.feed("\x1b[9mX")
        state = emu.screen

        assert state.cells[0][0].style.strikethrough is True

    def test_sgr_reset_bold_dim(self):
        """SGR 22 resets bold and dim."""
        emu = TerminalEmulator(cols=80, rows=24)
        emu.feed("\x1b[1;2mA\x1b[22mB")
        state = emu.screen

        assert state.cells[0][0].style.bold is True
        assert state.cells[0][0].style.dim is True
        assert state.cells[0][1].style.bold is False
        assert state.cells[0][1].style.dim is False

    def test_sgr_reset_italic(self):
        """SGR 23 resets italic."""
        emu = TerminalEmulator(cols=80, rows=24)
        emu.feed("\x1b[3mI\x1b[23mN")
        state = emu.screen

        assert state.cells[0][0].style.italic is True
        assert state.cells[0][1].style.italic is False

    def test_sgr_reset_underline(self):
        """SGR 24 resets underline."""
        emu = TerminalEmulator(cols=80, rows=24)
        emu.feed("\x1b[4mU\x1b[24mN")
        state = emu.screen

        assert state.cells[0][0].style.underline is True
        assert state.cells[0][1].style.underline is False

    def test_sgr_reset_inverse(self):
        """SGR 27 resets inverse."""
        emu = TerminalEmulator(cols=80, rows=24)
        emu.feed("\x1b[7mI\x1b[27mN")
        state = emu.screen

        assert state.cells[0][0].style.inverse is True
        assert state.cells[0][1].style.inverse is False

    def test_sgr_reset_strikethrough(self):
        """SGR 29 resets strikethrough."""
        emu = TerminalEmulator(cols=80, rows=24)
        emu.feed("\x1b[9mS\x1b[29mN")
        state = emu.screen

        assert state.cells[0][0].style.strikethrough is True
        assert state.cells[0][1].style.strikethrough is False

    def test_sgr_bright_background(self):
        """SGR 100-107 sets bright background colors."""
        emu = TerminalEmulator(cols=80, rows=24)

        # SGR 100 = bright black background
        emu.feed("\x1b[100mA")
        state = emu.screen

        assert state.cells[0][0].style.bg == "8"

    def test_sgr_bright_background_white(self):
        """SGR 107 = bright white background."""
        emu = TerminalEmulator(cols=80, rows=24)
        emu.feed("\x1b[107mZ")
        state = emu.screen

        assert state.cells[0][0].style.bg == "15"


# ---------------------------------------------------------------------------
# Extended color edge cases
# ---------------------------------------------------------------------------


class TestExtendedColorEdgeCases:
    def test_extended_fg_empty_params(self):
        """SGR 38 with no following params returns None."""
        emu = TerminalEmulator(cols=80, rows=24)

        # ESC[38m with nothing after — the extended color parser gets empty list
        emu.feed("\x1b[38mA")
        state = emu.screen

        # fg should remain None (no color set)
        assert state.cells[0][0].style.fg is None

    def test_extended_color_invalid_subcommand(self):
        """SGR 38;9;... with invalid sub-command returns None."""
        emu = TerminalEmulator(cols=80, rows=24)
        # Sub-command 9 is invalid (only 2 and 5 are valid)
        emu.feed("\x1b[38;9;100mB")
        state = emu.screen

        assert state.cells[0][0].style.fg is None

    def test_extended_bg_empty_params(self):
        """SGR 48 with no following params returns None."""
        emu = TerminalEmulator(cols=80, rows=24)
        emu.feed("\x1b[48mA")
        state = emu.screen

        assert state.cells[0][0].style.bg is None


# ---------------------------------------------------------------------------
# Erase display mode 1 — erase above
# ---------------------------------------------------------------------------


class TestEraseDisplayAbove:
    def test_erase_above_clears_rows_and_current_position(self):
        """ED mode 1 erases all rows above and current line up to cursor."""
        emu = TerminalEmulator(cols=80, rows=5)
        emu.feed("AAAA\r\nBBBB\r\nCCCC")

        # Cursor is at row 2, col 4
        # Move cursor to row 1, col 2

        emu.feed("\x1b[2;3H")

        # Erase above (mode 1)
        emu.feed("\x1b[1J")

        # Row 0 should be blank (erased above)
        assert _screen_text(emu, 0) == ""

        # Row 1 up to and including col 2 should be blank
        state = emu.screen

        assert state.cells[1][0].char == " "
        assert state.cells[1][1].char == " "
        assert state.cells[1][2].char == " "

        # Row 2 should be untouched
        assert _screen_text(emu, 2) == "CCCC"
