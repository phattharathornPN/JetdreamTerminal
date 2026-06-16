import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QTreeView, QMenu, QMenuBar, QStatusBar,
    QLabel, QPushButton, QSplitter, QMessageBox,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction, QKeySequence, QShortcut, QStandardItemModel, QStandardItem

from models.session import Session, SessionType
from core.session_manager import load_all, delete, update_last_used
from ui.session_dialog import SessionDialog
from ui.ssh_tab import SSHTab
from ui.telnet_tab import TelnetTab
from ui.rdp_tab import RdpTab
from ui.serial_tab import SerialTab
from ui.shell_tab import ShellTab
from ui.sftp_tab import SftpTab
from ui.host_key_dialog import HostKeyDialog, ChangedKeyDialog
from ui.keygen_dialog import KeygenDialog
from ui.settings_dialog import SettingsDialog
from ui.theme import get_qss, COLORS
from utils.logger import log


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("JetdreamTerminal")
        self.setMinimumSize(1000, 650)
        self.resize(1200, 750)
        self.sessions: list[Session] = []
        self._setup_ui()
        self._setup_shortcuts()
        self._load_sessions()

    def _setup_ui(self):
        self.setStyleSheet(get_qss())

        self._menu = self.menuBar()
        self._setup_menus()

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        sidebar = QWidget()
        sidebar.setMaximumWidth(250)
        sidebar.setStyleSheet(f"background: {COLORS['sidebar_bg']};")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)

        search_layout = QHBoxLayout()
        self._search = QLabel("🔍 Sessions")
        self._search.setStyleSheet("padding: 8px; font-weight: bold; color: #d8dee9;")
        search_layout.addWidget(self._search)
        sidebar_layout.addLayout(search_layout)

        self._session_tree = QTreeView()
        self._session_tree.setHeaderHidden(True)
        self._session_tree.setAnimated(True)
        self._session_tree.doubleClicked.connect(self._on_tree_double_click)
        self._session_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._session_tree.customContextMenuRequested.connect(self._on_tree_context)
        sidebar_layout.addWidget(self._session_tree)

        btn_layout = QHBoxLayout()
        self._new_btn = QPushButton("+ New Session")
        self._new_btn.clicked.connect(self._new_session)
        btn_layout.addWidget(self._new_btn)
        self._shell_btn = QPushButton("⬛ Shell")
        self._shell_btn.clicked.connect(self._open_shell)
        btn_layout.addWidget(self._shell_btn)
        sidebar_layout.addLayout(btn_layout)

        keygen_layout = QHBoxLayout()
        self._keygen_btn = QPushButton("🔑 Key Generator")
        self._keygen_btn.clicked.connect(self._open_keygen)
        keygen_layout.addWidget(self._keygen_btn)
        sidebar_layout.addLayout(keygen_layout)

        splitter.addWidget(sidebar)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self._tabs = QTabWidget()
        self._tabs.setTabsClosable(True)
        self._tabs.tabCloseRequested.connect(self._close_tab)
        right_layout.addWidget(self._tabs)

        self._statusbar = QStatusBar()
        self.setStatusBar(self._statusbar)
        self._statusbar.showMessage("Ready")

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

    def _setup_menus(self):
        file_menu = self._menu.addMenu("&File")

        new_action = QAction("&New Session", self)
        new_action.setShortcut(QKeySequence("Ctrl+N"))
        new_action.triggered.connect(self._new_session)
        file_menu.addAction(new_action)

        file_menu.addSeparator()

        quit_action = QAction("&Quit", self)
        quit_action.setShortcut(QKeySequence("Ctrl+Q"))
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        session_menu = self._menu.addMenu("&Sessions")

        connect_action = QAction("&Connect", self)
        connect_action.setShortcut(QKeySequence("Ctrl+Enter"))
        connect_action.triggered.connect(self._connect_selected)
        session_menu.addAction(connect_action)

        tools_menu = self._menu.addMenu("&Tools")

        settings_action = QAction("&Settings", self)
        settings_action.setShortcut(QKeySequence("Ctrl+,"))
        settings_action.triggered.connect(self._open_settings)
        tools_menu.addAction(settings_action)

        tools_menu.addSeparator()

        keygen_action = QAction("SSH Key &Generator", self)
        keygen_action.setShortcut(QKeySequence("Ctrl+K"))
        keygen_action.triggered.connect(self._open_keygen)
        tools_menu.addAction(keygen_action)

    def _setup_shortcuts(self):
        pass

    def _load_sessions(self):
        self.sessions = load_all()
        self._refresh_tree()

    def _refresh_tree(self):
        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(["Sessions"])

        fav_group = QStandardItem("⭐ Favorites")
        fav_group.setEditable(False)
        has_favs = False

        groups: dict[str, QStandardItem] = {}
        icon_map = {
            SessionType.SSH: "🔐",
            SessionType.TELNET: "📡",
            SessionType.RDP: "🖥️",
            SessionType.SFTP: "📁",
            SessionType.SERIAL: "🔌",
            SessionType.SHELL: "⬛",
            SessionType.VPN: "🔒",
            SessionType.VNC: "🖥️",
        }
        for s in self.sessions:
            icon = icon_map.get(s.session_type, "📄")
            item = QStandardItem(f"{icon} {s.name}")
            item.setEditable(False)
            item.setData(s.id, Qt.ItemDataRole.UserRole)

            if s.favorite:
                star = QStandardItem(f"⭐ {icon} {s.name}")
                star.setEditable(False)
                star.setData(s.id, Qt.ItemDataRole.UserRole)
                fav_group.appendRow(star)
                has_favs = True
            else:
                grp = s.group or "Default"
                if grp not in groups:
                    group_item = QStandardItem(grp)
                    group_item.setEditable(False)
                    groups[grp] = group_item
                    model.appendRow(group_item)
                groups[grp].appendRow(item)

        if has_favs:
            model.insertRow(0, fav_group)

        self._session_tree.setModel(model)
        self._session_tree.expandAll()

    def _on_tree_double_click(self, index):
        model = self._session_tree.model()
        item = model.itemFromIndex(index)
        if item and not item.hasChildren():
            session_id = item.data(Qt.ItemDataRole.UserRole)
            if session_id:
                self._open_session_by_id(session_id)

    def _on_tree_context(self, pos):
        index = self._session_tree.indexAt(pos)
        if not index.isValid():
            return
        model = self._session_tree.model()
        item = model.itemFromIndex(index)
        if item and not item.hasChildren():
            session_id = item.data(Qt.ItemDataRole.UserRole)
            if session_id:
                menu = QMenu(self)
                connect_action = menu.addAction("Connect")
                fav_action = menu.addAction("Toggle Favorite ⭐")
                edit_action = menu.addAction("Edit")
                delete_action = menu.addAction("Delete")
                action = menu.exec(self._session_tree.viewport().mapToGlobal(pos))

                if action == connect_action:
                    self._open_session_by_id(session_id)
                elif action == fav_action:
                    self._toggle_favorite(session_id)
                elif action == edit_action:
                    self._edit_session(session_id)
                elif action == delete_action:
                    self._delete_session(session_id)

    def _open_session_by_id(self, session_id: int):
        from core.session_manager import get_by_id
        session = get_by_id(session_id)
        if session:
            self._open_session(session)

    def _open_session(self, session: Session):
        update_last_used(session.id)
        tab_map = {
            SessionType.SSH: SSHTab,
            SessionType.TELNET: TelnetTab,
            SessionType.RDP: RdpTab,
            SessionType.SERIAL: SerialTab,
            SessionType.SHELL: ShellTab,
            SessionType.SFTP: SftpTab,
        }
        tab_cls = tab_map.get(session.session_type, SSHTab)
        if session.session_type == SessionType.VPN:
            from ui.vpn_tab import VpnTab
            tab = VpnTab(session, self)
        elif session.session_type == SessionType.VNC:
            from ui.vnc_tab import VncTab
            tab = VncTab(session, self)
        else:
            tab = tab_cls(session, self)
        icon_map = {
            SessionType.SSH: "🔐",
            SessionType.TELNET: "📡",
            SessionType.RDP: "🖥️",
            SessionType.SFTP: "📁",
            SessionType.SERIAL: "🔌",
        }
        icon = icon_map.get(session.session_type, "📄")
        idx = self._tabs.addTab(tab, f"{icon} {session.name}")
        self._tabs.setCurrentIndex(idx)
        if session.session_type == SessionType.SERIAL:
            self._statusbar.showMessage(f"Connected: {session.name} ({session.serial_port})")
        elif session.session_type == SessionType.SHELL:
            self._statusbar.showMessage(f"Shell: {session.name}")
        else:
            self._statusbar.showMessage(f"Connected: {session.name} ({session.host})")

    def _close_tab(self, index):
        tab = self._tabs.widget(index)
        if tab:
            if hasattr(tab, "close_terminal"):
                tab.close_terminal()
            if hasattr(tab, "close_rdp"):
                tab.close_rdp()
            if hasattr(tab, "disconnect"):
                tab.disconnect()
            if hasattr(tab, "_force_disconnect"):
                tab._force_disconnect()
            self._tabs.removeTab(index)
            tab.deleteLater()

    def _new_session(self):
        dlg = SessionDialog(parent=self)
        dlg.session_saved.connect(lambda s: (self._load_sessions(), self._open_session(s)))
        dlg.exec()

    def _open_shell(self):
        session = Session(
            name="Shell",
            session_type=SessionType.SHELL,
        )
        self._open_session(session)

    def _edit_session(self, session_id: int):
        from core.session_manager import get_by_id
        session = get_by_id(session_id)
        if session:
            dlg = SessionDialog(session, parent=self)
            dlg.session_saved.connect(lambda: self._load_sessions())
            dlg.exec()

    def _toggle_favorite(self, session_id: int):
        from core.session_manager import get_by_id, save
        session = get_by_id(session_id)
        if session:
            session.favorite = not session.favorite
            save(session)
            self._load_sessions()

    def _delete_session(self, session_id: int):
        reply = QMessageBox.question(
            self, "Delete Session",
            "Are you sure you want to delete this session?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            delete(session_id)
            self._load_sessions()

    def _connect_selected(self):
        indexes = self._session_tree.selectedIndexes()
        if indexes:
            self._on_tree_double_click(indexes[0])

    def _open_keygen(self):
        dlg = KeygenDialog(self)
        dlg.exec()

    def _open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec():
            for i in range(self._tabs.count()):
                tab = self._tabs.widget(i)
                if hasattr(tab, '_term') and hasattr(tab._term, '_load_bg_image'):
                    tab._term._load_bg_image()
                    tab._term.update()

    def closeEvent(self, event):
        for i in range(self._tabs.count()):
            tab = self._tabs.widget(i)
            if tab:
                if hasattr(tab, "close_terminal"):
                    tab.close_terminal()
                if hasattr(tab, "close_rdp"):
                    tab.close_rdp()
                if hasattr(tab, "disconnect"):
                    tab.disconnect()
        event.accept()
