# https://github.com/executablebooks/MyST-NB/blob/6ee8d018db1bd7f070f7fdbf239cd393c2b5f1e7/myst_nb/core/lexers.py
"""Pygments lexers"""
from __future__ import annotations

import re

# this is not added as an entry point in ipython, so we add it in this package
from IPython.lib.lexers import IPythonTracebackLexer  # noqa: F401
from myst_nb.core.lexers import AnsiColorLexer  # noqa

_ansi_code_to_color = {
    0: "Black",
    1: "Red",
    2: "Green",
    3: "Yellow",
    4: "Blue",
    5: "Magenta",
    6: "Cyan",
    7: "White",
}


def process(self, match):
    """Produce the next token and bit of text.

    Interprets the ANSI code (which may be a color code or some other
    code), changing the lexer state and producing a new token. If it's not
    a color code, we just strip it out and move on.

    Some useful reference for ANSI codes:
    * http://ascii-table.com/ansi-escape-sequences.php
    """
    # "after_escape" contains everything after the start of the escape
    # sequence, up to the next escape sequence. We still need to separate
    # the content from the end of the escape sequence.
    after_escape = match.group(1)

    # TODO: this doesn't handle the case where the values are non-numeric.
    # This is rare but can happen for keyboard remapping, e.g.
    # '\x1b[0;59;"A"p'
    parsed = re.match(
        r"([0-9;=]*?)?([a-zA-Z])(.*)$",
        after_escape,
        re.DOTALL | re.MULTILINE,
    )
    if parsed is None:
        # This shouldn't ever happen if we're given valid text + ANSI, but
        # people can provide us with utter junk, and we should tolerate it.
        text = after_escape
    else:
        value, code, text = parsed.groups()
        if code == "m":  # "m" is "Set Graphics Mode"
            # Special case \x1b[m is a reset code
            if value == "":
                self.reset_state()
            else:
                try:
                    values = [int(v) for v in value.split(";")]
                except ValueError:
                    # Shouldn't ever happen, but could with invalid ANSI.
                    values = []

                while len(values) > 0:
                    value = values.pop(0)
                    fg_color = _ansi_code_to_color.get(value - 30)
                    bg_color = _ansi_code_to_color.get(value - 40)
                    if fg_color:
                        self.fg_color = fg_color
                    elif bg_color:
                        self.bg_color = bg_color
                    elif value == 1:
                        self.bold = True
                    elif value == 2:
                        self.faint = True
                    elif value == 22:
                        self.bold = False
                        self.faint = False
                    elif value == 39:
                        self.fg_color = None
                    elif value == 49:
                        self.bg_color = None
                    elif value == 92:  # Special case for bright green
                        self.fg_color = "Green"
                    elif value == 0:
                        self.reset_state()
                    elif value in (38, 48):
                        try:
                            five = values.pop(0)
                            color = values.pop(0)
                        except IndexError:
                            continue
                        else:
                            if five != 5:
                                continue
                            if not 0 <= color <= 255:
                                continue
                            if value == 38:
                                self.fg_color = f"C{color}"
                            else:
                                self.bg_color = f"C{color}"

    yield match.start(), self.current_token, text


AnsiColorLexer.process = process
