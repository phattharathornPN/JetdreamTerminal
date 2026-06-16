COLORS = {
    "bg": "#2e3440",
    "bg_light": "#3b4252",
    "bg_lighter": "#434c5e",
    "bg_lightest": "#4c566a",
    "fg": "#eceff4",
    "fg_dim": "#d8dee9",
    "fg_bright": "#ffffff",
    "accent": "#88c0d0",
    "accent2": "#81a1c1",
    "green": "#a3be8c",
    "red": "#bf616a",
    "yellow": "#ebcb8b",
    "orange": "#d08770",
    "purple": "#b48ead",
    "cyan": "#88c0d0",
    "selection_bg": "#434c5e",
    "cursor": "#eceff4",
    "tab_active": "#2e3440",
    "tab_inactive": "#3b4252",
    "tab_hover": "#434c5e",
    "sidebar_bg": "#2e3440",
    "status_bg": "#3b4252",
}

TERMINAL_THEMES = {
    "Nord": {"bg": "#1a1a2e", "fg": "#ffffff"},
    "Dracula": {"bg": "#282a36", "fg": "#ffffff"},
    "Monokai": {"bg": "#272822", "fg": "#ffffff"},
    "Solarized Dark": {"bg": "#002b36", "fg": "#eeeeec"},
    "Solarized Light": {"bg": "#fdf6e3", "fg": "#586e75"},
    "Gruvbox Dark": {"bg": "#282828", "fg": "#fbf1c7"},
    "One Dark": {"bg": "#282c34", "fg": "#c8ccd4"},
    "Catppuccin": {"bg": "#1e1e2e", "fg": "#e0e0e0"},
    "Tokyo Night": {"bg": "#1a1b26", "fg": "#c0caf5"},
    "White": {"bg": "#ffffff", "fg": "#222222"},
    "Black": {"bg": "#000000", "fg": "#00ff00"},
}

_current_terminal_theme = "Dracula"
_terminal_bg_image: str = ""
_terminal_opacity: float = 1.0


def get_terminal_bg() -> str:
    return TERMINAL_THEMES.get(_current_terminal_theme, TERMINAL_THEMES["Dracula"])["bg"]


def get_terminal_fg() -> str:
    return TERMINAL_THEMES.get(_current_terminal_theme, TERMINAL_THEMES["Dracula"])["fg"]


def set_terminal_theme(name: str):
    global _current_terminal_theme
    if name in TERMINAL_THEMES:
        _current_terminal_theme = name
        _save_setting("terminal", "theme", name)


def get_terminal_theme_name() -> str:
    return _current_terminal_theme


def set_terminal_bg_image(path: str):
    global _terminal_bg_image
    _terminal_bg_image = path
    _save_setting("terminal", "bg_image", path)


def get_terminal_bg_image() -> str:
    return _terminal_bg_image


def set_terminal_opacity(val: float):
    global _terminal_opacity
    _terminal_opacity = max(0.1, min(1.0, val))
    _save_setting("terminal", "opacity", str(_terminal_opacity))


def get_terminal_opacity() -> float:
    return _terminal_opacity


def _save_setting(section: str, key: str, value: str):
    try:
        from utils.config import load_config, save_config
        cfg = load_config()
        if not cfg.has_section(section):
            cfg.add_section(section)
        cfg.set(section, key, value)
        save_config(cfg)
    except Exception:
        pass


def load_saved_theme():
    global _current_terminal_theme, _terminal_bg_image, _terminal_opacity
    try:
        from utils.config import load_config
        cfg = load_config()
        if cfg.has_section("terminal"):
            if cfg.has_option("terminal", "theme"):
                name = cfg.get("terminal", "theme")
                if name in TERMINAL_THEMES:
                    _current_terminal_theme = name
            if cfg.has_option("terminal", "bg_image"):
                _terminal_bg_image = cfg.get("terminal", "bg_image")
            if cfg.has_option("terminal", "opacity"):
                try:
                    _terminal_opacity = float(cfg.get("terminal", "opacity"))
                except ValueError:
                    pass
    except Exception:
        pass


def get_qss() -> str:
    c = COLORS
    return f"""
        * {{
            font-family: "JetBrains Mono", "Fira Code", "Cascadia Code", monospace;
            font-size: 13px;
        }}
        QMainWindow, QWidget {{
            background-color: {c["bg"]};
            color: {c["fg"]};
        }}
        QMenuBar {{
            background-color: {c["bg_light"]};
            color: {c["fg"]};
            border-bottom: 1px solid {c["bg_lightest"]};
            padding: 2px;
        }}
        QMenuBar::item:selected {{
            background-color: {c["bg_lighter"]};
        }}
        QMenu {{
            background-color: {c["bg_light"]};
            color: {c["fg"]};
            border: 1px solid {c["bg_lightest"]};
        }}
        QMenu::item:selected {{
            background-color: {c["accent"]};
            color: {c["bg"]};
        }}
        QTabWidget::pane {{
            border: none;
        }}
        QTabBar::tab {{
            background: {c["tab_inactive"]};
            color: {c["fg_dim"]};
            padding: 6px 16px;
            border: none;
            border-bottom: 2px solid transparent;
            min-width: 100px;
        }}
        QTabBar::tab:selected {{
            background: {c["tab_active"]};
            color: {c["fg_bright"]};
            border-bottom: 2px solid {c["accent"]};
        }}
        QTabBar::tab:hover {{
            background: {c["tab_hover"]};
        }}
        QTabBar {{
            background: {c["bg_light"]};
        }}
        QTreeView {{
            background-color: {c["sidebar_bg"]};
            color: {c["fg"]};
            border: none;
            outline: none;
        }}
        QTreeView::item {{
            padding: 4px 8px;
            border: none;
        }}
        QTreeView::item:selected {{
            background-color: {c["selection_bg"]};
            color: {c["fg_bright"]};
        }}
        QTreeView::item:hover {{
            background-color: {c["bg_lighter"]};
        }}
        QLineEdit {{
            background-color: {c["bg_lighter"]};
            color: {c["fg"]};
            border: 1px solid {c["bg_lightest"]};
            border-radius: 4px;
            padding: 4px 8px;
            selection-background-color: {c["accent"]};
        }}
        QLineEdit:focus {{
            border: 1px solid {c["accent"]};
        }}
        QPushButton {{
            background-color: {c["bg_lighter"]};
            color: {c["fg"]};
            border: 1px solid {c["bg_lightest"]};
            border-radius: 4px;
            padding: 6px 16px;
        }}
        QPushButton:hover {{
            background-color: {c["bg_lightest"]};
        }}
        QPushButton:pressed {{
            background-color: {c["accent"]};
            color: {c["bg"]};
        }}
        QComboBox {{
            background-color: {c["bg_lighter"]};
            color: {c["fg"]};
            border: 1px solid {c["bg_lightest"]};
            border-radius: 4px;
            padding: 4px 8px;
            padding-right: 24px;
        }}
        QComboBox::drop-down {{
            border: none;
            width: 24px;
            subcontrol-origin: padding;
            subcontrol-position: center right;
        }}
        QComboBox::down-arrow {{
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 6px solid {c["fg_dim"]};
            width: 0;
            height: 0;
            margin-right: 6px;
        }}
        QComboBox:hover::down-arrow {{
            border-top-color: {c["accent"]};
        }}
        QComboBox QAbstractItemView {{
            background-color: {c["bg_light"]};
            color: {c["fg"]};
            border: 1px solid {c["bg_lightest"]};
            selection-background-color: {c["accent"]};
        }}
        QCheckBox {{
            color: {c["fg"]};
            spacing: 8px;
        }}
        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
            border: 1px solid {c["bg_lightest"]};
            border-radius: 3px;
            background-color: {c["bg_lighter"]};
        }}
        QCheckBox::indicator:checked {{
            background-color: {c["accent"]};
            border-color: {c["accent"]};
        }}
        QStatusBar {{
            background-color: {c["status_bg"]};
            color: {c["fg_dim"]};
            border-top: 1px solid {c["bg_lightest"]};
        }}
        QSplitter::handle {{
            background-color: {c["bg_lightest"]};
        }}
        QScrollBar:vertical {{
            background: {c["bg"]};
            width: 10px;
            border: none;
        }}
        QScrollBar::handle:vertical {{
            background: {c["bg_lightest"]};
            border-radius: 5px;
            min-height: 30px;
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QLabel {{
            color: {c["fg"]};
            background: transparent;
        }}
        QGroupBox {{
            color: {c["fg"]};
            border: 1px solid {c["bg_lightest"]};
            border-radius: 4px;
            margin-top: 8px;
            padding-top: 16px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 4px;
        }}
    """
