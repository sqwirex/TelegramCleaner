from PySide6.QtCore import QEvent, Qt, QTimer
from PySide6.QtGui import QKeyEvent

from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QLineEdit,
    QPushButton,
    QPlainTextEdit,
    QWidget,
    QComboBox,
    QTabBar,
)

from tgcleaner.ui.widgets.results import ResultsListWidget


class MainWindowFocusMixin:
    def keyPressEvent(self, event: QKeyEvent):
        if self._handle_global_navigation_keys(event):
            event.accept()
            return
        super().keyPressEvent(event)


    def _handle_results_keyboard_shortcuts(self, event: QKeyEvent) -> bool:
        focused = QApplication.focusWidget()
        if QApplication.activePopupWidget() is not None:
            return False
        if isinstance(focused, (QLineEdit, QPlainTextEdit)):
            return False
        if not hasattr(self, "results_list") or not self.results_list._message_rows():
            return False
        key = event.key()
        modifiers = event.modifiers()
        if key in (Qt.Key_Up, Qt.Key_Down):
            step = 1 if key == Qt.Key_Down else -1
            self.results_list.setFocus(Qt.OtherFocusReason)
            self.results_list.move_current_message(step, False)
            return True
        if key == Qt.Key_A and modifiers & Qt.ControlModifier:
            self.results_list._set_all_messages_selected(True)
            self.results_list.clearFocus()
            self.results_list.clearSelection()
            return True
        if key == Qt.Key_D and modifiers & Qt.ControlModifier:
            self.results_list._set_all_messages_selected(False)
            self.results_list.clearFocus()
            self.results_list.clearSelection()
            return True
        if key == Qt.Key_Escape:
            return False
        if key == Qt.Key_Delete:
            self.results_list.setFocus(Qt.OtherFocusReason)
            self.on_delete()
            return True
        if self.results_list.hasFocus() and key in (Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter):
            self.results_list.keyPressEvent(event)
            return True
        return False


    def _handle_global_navigation_keys(self, event: QKeyEvent) -> bool:
        focused = QApplication.focusWidget()
        if QApplication.activePopupWidget() is not None:
            return False
        if isinstance(focused, (QLineEdit, QPlainTextEdit)):
            return False

        if self._handle_results_keyboard_shortcuts(event):
            return True

        if event.key() in (Qt.Key_Left, Qt.Key_Right):
            if self._is_search_loading():
                return True
            if event.key() == Qt.Key_Left:
                self.tabs.setCurrentIndex(0)
                return True
            if self.tabs.isTabEnabled(1):
                self.tabs.setCurrentIndex(1)
                return True

        return False


    def _setup_focus_behavior(self):
        self._mouse_press_text_widget = None
        self._text_mouse_drag_active = False
        QApplication.instance().installEventFilter(self)
        self.installEventFilter(self)
        for widget in self.findChildren(QWidget):
            widget.installEventFilter(self)
        for entry in self._auth_line_edits():
            entry.returnPressed.connect(self._trigger_active_auth_button)


    def _text_input_target(self, widget):
        while widget is not None:
            if isinstance(widget, (QLineEdit, QPlainTextEdit)):
                return widget
            widget = widget.parentWidget()
        return None


    def _is_focus_interactive_target(self, widget):
        tab_bar = self.tabs.tabBar()
        while widget is not None:
            if isinstance(widget, (QLineEdit, QPlainTextEdit, QPushButton, QCheckBox, QComboBox)):
                return True
            if isinstance(widget, ResultsListWidget):
                return False
            if widget is tab_bar:
                return True
            widget = widget.parentWidget()
        return False


    def _clear_current_focus(self):
        for widget in self.findChildren(QLineEdit):
            widget.deselect()
        for widget in self.findChildren(QPlainTextEdit):
            if hasattr(widget, "clear_selection_and_focus"):
                widget.clear_selection_and_focus()
            else:
                cursor = widget.textCursor()
                cursor.clearSelection()
                widget.setTextCursor(cursor)
        focused = QApplication.focusWidget()
        if focused is not None:
            focused.clearFocus()
        if hasattr(self, "central_root_widget"):
            self.central_root_widget.setFocus(Qt.OtherFocusReason)
        else:
            self.setFocus(Qt.OtherFocusReason)


    def eventFilter(self, obj, event):
        active_modal = QApplication.activeModalWidget()
        if active_modal is not None and active_modal is not self:
            return False
        if event.type() == QEvent.KeyPress and QApplication.activePopupWidget() is not None:
            return False
        if event.type() == QEvent.KeyPress and self._handle_global_navigation_keys(event):
            return True
        if event.type() == QEvent.MouseButtonPress:
            try:
                pressed = QApplication.widgetAt(event.globalPosition().toPoint())
            except Exception:
                pressed = obj if isinstance(obj, QWidget) else None
            self._mouse_press_text_widget = self._text_input_target(pressed)
            if event.button() == Qt.LeftButton:
                self._text_mouse_drag_active = self._mouse_press_text_widget is not None
        if event.type() == QEvent.MouseButtonRelease:
            try:
                clicked = QApplication.widgetAt(event.globalPosition().toPoint())
            except Exception:
                clicked = obj if isinstance(obj, QWidget) else None
            text_press_widget = getattr(self, "_mouse_press_text_widget", None)
            text_drag_active = bool(getattr(self, "_text_mouse_drag_active", False))
            self._mouse_press_text_widget = None
            if text_drag_active:
                QTimer.singleShot(0, lambda: setattr(self, "_text_mouse_drag_active", False))
            button = clicked
            while button is not None and not isinstance(button, QPushButton):
                button = button.parentWidget()
            tab_bar = clicked
            while tab_bar is not None and not isinstance(tab_bar, QTabBar):
                tab_bar = tab_bar.parentWidget()
            if text_press_widget is not None or text_drag_active:
                target = text_press_widget if text_press_widget is not None else QApplication.focusWidget()
                if isinstance(target, (QLineEdit, QPlainTextEdit)):
                    QTimer.singleShot(0, lambda widget=target: widget.setFocus(Qt.MouseFocusReason))
            elif button is not None:
                QTimer.singleShot(0, button.clearFocus)
                QTimer.singleShot(30, button.clearFocus)
                if hasattr(self, "central_root_widget"):
                    QTimer.singleShot(0, lambda: self.central_root_widget.setFocus(Qt.OtherFocusReason))
                else:
                    QTimer.singleShot(0, lambda: self.setFocus(Qt.OtherFocusReason))
            elif tab_bar is not None:
                QTimer.singleShot(0, tab_bar.clearFocus)
                QTimer.singleShot(30, tab_bar.clearFocus)
                if hasattr(self, "central_root_widget"):
                    QTimer.singleShot(0, lambda: self.central_root_widget.setFocus(Qt.OtherFocusReason))
                else:
                    QTimer.singleShot(0, lambda: self.setFocus(Qt.OtherFocusReason))
            elif not self._is_focus_interactive_target(clicked):
                self._clear_current_focus()

        if event.type() == QEvent.FocusIn and isinstance(obj, QLineEdit):
            if not QApplication.mouseButtons() & Qt.LeftButton:
                obj.deselect()
            QTimer.singleShot(0, lambda widget=obj: widget.deselect() if not QApplication.mouseButtons() & Qt.LeftButton else None)

        if event.type() == QEvent.KeyPress:
            if isinstance(obj, (QLineEdit, QPlainTextEdit)) and event.modifiers() & Qt.ControlModifier and event.key() in (Qt.Key_Z, Qt.Key_Y):
                QTimer.singleShot(0, lambda widget=obj: self._clear_text_selection_only(widget))
                QTimer.singleShot(20, lambda widget=obj: self._clear_text_selection_only(widget))

            if event.key() == Qt.Key_Escape:
                if self._handle_results_keyboard_shortcuts(event):
                    return True
                self._clear_current_focus()
                return True

            if event.key() in (Qt.Key_Left, Qt.Key_Right):
                focused = QApplication.focusWidget()
                if not isinstance(focused, (QLineEdit, QPlainTextEdit)):
                    if self._is_search_loading():
                        return True
                    if event.key() == Qt.Key_Left:
                        self.tabs.setCurrentIndex(0)
                    elif self.tabs.isTabEnabled(1):
                        self.tabs.setCurrentIndex(1)
                    return True

            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                focused = QApplication.focusWidget()
                if isinstance(focused, QPushButton):
                    if focused.isEnabled():
                        focused.click()
                    return True
                if isinstance(focused, QCheckBox):
                    if focused.isEnabled():
                        focused.toggle()
                    return True

            if event.key() in (Qt.Key_Tab, Qt.Key_Backtab):
                reverse = event.key() == Qt.Key_Backtab or event.modifiers() & Qt.ShiftModifier
                focused_before = QApplication.focusWidget()
                if focused_before is None or focused_before in (self, getattr(self, "central_root_widget", None)) or not self._is_focus_interactive_target(focused_before):
                    self.language_combo.setFocus(Qt.TabFocusReason)
                elif reverse:
                    self.focusPreviousChild()
                else:
                    self.focusNextChild()
                focused = QApplication.focusWidget()
                attempts = 0
                while focused is not None and not self._is_focus_interactive_target(focused) and attempts < 12:
                    if reverse:
                        self.focusPreviousChild()
                    else:
                        self.focusNextChild()
                    focused = QApplication.focusWidget()
                    attempts += 1
                if focused is None or not self._is_focus_interactive_target(focused):
                    self.language_combo.setFocus(Qt.TabFocusReason)
                    focused = self.language_combo
                if isinstance(focused, QLineEdit):
                    focused.deselect()
                    QTimer.singleShot(0, focused.deselect)
                    QTimer.singleShot(20, focused.deselect)
                return True
        return super().eventFilter(obj, event)