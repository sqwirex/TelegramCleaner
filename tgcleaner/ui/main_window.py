import sys
from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import QEvent, Qt, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QCheckBox, QLineEdit, QMainWindow, QPushButton

from tgcleaner.core.config import read_saved_fields, resource_path
from tgcleaner.core.models import FoundMessage
from tgcleaner.telegram.controller import TelegramController
from tgcleaner.ui.runner import AsyncRunner
from tgcleaner.ui.common import NoFocusRectStyle
from tgcleaner.ui.windows.auth import MainWindowAuthMixin
from tgcleaner.ui.windows.dialogs import MainWindowDialogsMixin
from tgcleaner.ui.windows.focus import MainWindowFocusMixin
from tgcleaner.ui.windows.layout import MainWindowLayoutMixin
from tgcleaner.ui.windows.results import MainWindowResultsMixin
from tgcleaner.ui.windows.search import MainWindowSearchMixin
from tgcleaner.ui.windows.styles import MainWindowStylesMixin
from tgcleaner.core.i18n import T, set_language


class TelegramCleanerApp(
    MainWindowLayoutMixin,
    MainWindowStylesMixin,
    MainWindowFocusMixin,
    MainWindowAuthMixin,
    MainWindowSearchMixin,
    MainWindowResultsMixin,
    MainWindowDialogsMixin,
    QMainWindow,
):
    def __init__(self):
        super().__init__()
        self._app_closing = False
        self.controller = TelegramController()
        self.runner = AsyncRunner()
        self.runner.completed.connect(self._on_async_completed)
        self.runner.progress.connect(self._on_async_progress)
        self.callbacks: dict[int, tuple[Callable, Callable]] = {}
        self.active_search_task_id: Optional[int] = None
        self.active_delete_task_id: Optional[int] = None
        self.search_stop_requested = False
        self.delete_stop_requested = False
        self.current_results_mode = "messages"
        self.pending_results_mode = "messages"
        self.found_messages: list[FoundMessage] = []
        self.all_found_messages: list[FoundMessage] = []
        self.delete_result_backup: list[FoundMessage] = []
        self.result_select_checkboxes: list[QCheckBox] = []
        self.pending_result_messages: list[FoundMessage] = []
        self.pending_result_timer = QTimer(self)
        self.pending_result_timer.setInterval(70)
        self.pending_result_timer.timeout.connect(self._flush_pending_result_messages)
        self.rendered_result_count = 0
        self.last_search_export_metadata = {}
        self.last_delete_had_error = False
        self.last_delete_was_stopped = False
        self.auth_state = "initial"
        self.saved = read_saved_fields()
        self.simple_render_enabled = str(self.saved.get("simple_render", "0")).strip() == "1"
        set_language(self.saved.get("language", "en"))
        self.current_api_id: Optional[int] = None
        self.current_api_hash: Optional[str] = None
        self.current_phone: Optional[str] = None
        self.eye_buttons: dict[QLineEdit, QPushButton] = {}
        self.setWindowTitle(T.APP_TITLE)
        self._set_window_icon()
        self.resize(980, 760)
        self.setMinimumSize(980, 760)
        self._build_ui()
        self._last_results_window_expanded_state = self._results_window_expanded_state()
        self._apply_styles()
        self._setup_autosave()
        self._setup_focus_behavior()
        self._set_initial_values()
        self._check_session_on_start()
    def _set_window_icon(self):
        icon_path = resource_path("assets/app.ico")
        if Path(icon_path).exists():
            self.setWindowIcon(QIcon(icon_path))

    def _results_window_expanded_state(self):
        state = self.windowState()
        return bool(state & Qt.WindowFullScreen) or bool(state & Qt.WindowMaximized)

    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange:
            current = self._results_window_expanded_state()
            previous = getattr(self, "_last_results_window_expanded_state", current)
            self._last_results_window_expanded_state = current
            if current != previous:
                results_list = getattr(self, "results_list", None)
                if results_list is not None:
                    if hasattr(results_list, "begin_window_state_resize_transition"):
                        results_list.begin_window_state_resize_transition()
                    elif hasattr(results_list, "begin_fullscreen_resize_transition"):
                        results_list.begin_fullscreen_resize_transition()
        super().changeEvent(event)


def main():
    app = QApplication(sys.argv)
    for effect_name in ("UI_AnimateCombo", "UI_FadeMenu", "UI_AnimateMenu"):
        effect = getattr(Qt, effect_name, None)
        if effect is not None:
            QApplication.setEffectEnabled(effect, False)
    app.setStyle(NoFocusRectStyle(app.style()))
    icon_path = resource_path("assets/app.ico")
    if Path(icon_path).exists():
        app.setWindowIcon(QIcon(icon_path))
    window = TelegramCleanerApp()
    window.show()
    sys.exit(app.exec())