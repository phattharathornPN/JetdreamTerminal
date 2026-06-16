import re
from dataclasses import dataclass
from PyQt6.QtGui import QColor


@dataclass
class HighlightRule:
    pattern: re.Pattern
    fg: QColor
    bg: QColor | None = None
    bold: bool = False
    underline: bool = False


_HIGHLIGHT_RULES: list[HighlightRule] = []


def _build_rules():
    global _HIGHLIGHT_RULES
    if _HIGHLIGHT_RULES:
        return

    _HIGHLIGHT_RULES = [
        # URLs
        HighlightRule(
            re.compile(r'https?://[^\s<>"\')\]]+'),
            fg=QColor("#88c0d0"),
            underline=True,
        ),
        # IPv4 addresses
        HighlightRule(
            re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'),
            fg=QColor("#ebcb8b"),
            bold=True,
        ),
        # Email addresses
        HighlightRule(
            re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'),
            fg=QColor("#b48ead"),
        ),
        # File paths (absolute)
        HighlightRule(
            re.compile(r'(?:/[\w.@-]+){2,}'),
            fg=QColor("#a3be8c"),
            bold=True,
        ),
        # Quoted strings (double or single)
        HighlightRule(
            re.compile(r'"[^"]*"'),
            fg=QColor("#d8dee9"),
            bg=QColor("#3b4252"),
        ),
        HighlightRule(
            re.compile(r"'[^']*'"),
            fg=QColor("#d8dee9"),
            bg=QColor("#3b4252"),
        ),
        # Success patterns
        HighlightRule(
            re.compile(r'\b(ok|OK|success|SUCCESS|done|DONE|complete|COMPLETE|connected|CONNECTED|authorized|passed|PASS)\b'),
            fg=QColor("#a3be8c"),
            bold=True,
        ),
        # Error / failure patterns
        HighlightRule(
            re.compile(r'\b(error|ERROR|fail|FAIL|failed|FAILED|denied|DENIED|refused|REFUSED|timeout|TIMEOUT|reject|REJECT)\b'),
            fg=QColor("#bf616a"),
            bold=True,
        ),
        # Warning patterns
        HighlightRule(
            re.compile(r'\b(warning|WARN|caution|WARNING)\b'),
            fg=QColor("#ebcb8b"),
            bold=True,
        ),
        # Numbers (standalone integers/floats, not inside words)
        HighlightRule(
            re.compile(r'(?<![A-Za-z_])\d+(?:\.\d+)?(?![A-Za-z_])'),
            fg=QColor("#d08770"),
        ),
        # Keywords: common command keywords
        HighlightRule(
            re.compile(r'\b(sudo|chmod|chown|mkdir|rm|cp|mv|ssh|scp|rsync|tar|grep|sed|awk|curl|wget|apt|yum|dnf|pip|docker|systemctl|journalctl)\b'),
            fg=QColor("#81a1c1"),
            bold=True,
        ),
        # Flags / options (-x, --long-option)
        HighlightRule(
            re.compile(r'(?:^|\s)(-{1,2}[\w-]+)'),
            fg=QColor("#88c0d0"),
        ),
    ]


def get_highlight_rules() -> list[HighlightRule]:
    _build_rules()
    return _HIGHLIGHT_RULES
