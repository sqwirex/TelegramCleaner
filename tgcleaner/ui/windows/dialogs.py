import asyncio
from PySide6.QtCore import Qt, QTimer

from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
)


from tgcleaner.ui.common import StyledMessageDialog
from tgcleaner.core.i18n import T, is_handled_error_text


class MainWindowDialogsMixin:
    def _is_app_closing(self) -> bool:
        return bool(getattr(self, "_app_closing", False)) or QApplication.closingDown()


    def _close_open_dropdowns(self):
        popup = QApplication.activePopupWidget()
        if popup is not None:
            popup.close()
        for combo in self.findChildren(QComboBox):
            try:
                combo.hidePopup()
            except Exception:
                pass

    def _restore_focus_after_dialog(self):
        if self._is_app_closing():
            return
        def clear_later():
            focused = QApplication.focusWidget()
            if focused is not None:
                focused.clearFocus()
            if hasattr(self, "central_root_widget"):
                self.central_root_widget.setFocus(Qt.OtherFocusReason)
            else:
                self.setFocus(Qt.OtherFocusReason)
        clear_later()
        QTimer.singleShot(0, clear_later)
        QTimer.singleShot(40, clear_later)


    def _show_warning_dialog(self, title: str, text: str):
        if self._is_app_closing():
            return
        self._close_open_dropdowns()
        StyledMessageDialog(self, title, text, "warning").exec()
        self._restore_focus_after_dialog()


    def _show_error_dialog(self, title: str, text: str, copy_text: str | None = None):
        if self._is_app_closing():
            return
        self._close_open_dropdowns()
        error_text = str(text or "")
        raw_copy_text = copy_text
        if raw_copy_text is None and error_text and not is_handled_error_text(error_text):
            raw_copy_text = error_text
        StyledMessageDialog(self, title, error_text, "error", copy_text=raw_copy_text).exec()
        self._restore_focus_after_dialog()


    def _show_info_dialog(self, title: str, text: str):
        if self._is_app_closing():
            return
        self._close_open_dropdowns()
        StyledMessageDialog(self, title, text, "info").exec()
        self._restore_focus_after_dialog()


    def _confirm_dialog(self, title: str, text: str, danger_confirm: bool = False) -> bool:
        if self._is_app_closing():
            return False
        self._close_open_dropdowns()
        dialog = StyledMessageDialog(self, title, text, "question", (T.YES, T.NO), danger_confirm=danger_confirm)
        dialog.exec()
        result = dialog.clicked_button == T.YES
        self._restore_focus_after_dialog()
        return result


    def _confirm_dialog_default_no(self, title: str, text: str) -> bool:
        if self._is_app_closing():
            return False
        self._close_open_dropdowns()
        dialog = StyledMessageDialog(self, title, text, "question", (T.YES, T.NO))
        buttons = getattr(dialog, "_dialog_buttons", [])
        if len(buttons) >= 2:
            dialog._preferred_initial_button = buttons[-1]
        dialog.exec()
        result = dialog.clicked_button == T.YES
        self._restore_focus_after_dialog()
        return result


    def closeEvent(self, event):
        self._app_closing = True
        self.callbacks.clear()
        try:
            self.pending_result_timer.stop()
        except Exception:
            pass
        self._close_open_dropdowns()
        try:
            future = asyncio.run_coroutine_threadsafe(self.controller.disconnect_current(), self.runner.loop)
            future.result(timeout=3)
        except Exception:
            pass
        self.runner.stop()
        event.accept()