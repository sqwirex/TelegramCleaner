import time

from PySide6.QtCore import QEvent, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QKeyEvent, QPainter, QPainterPath, QRegion, QTextCursor
from PySide6.QtWidgets import QApplication, QFrame, QLineEdit, QPlainTextEdit, QWidget

from tgcleaner.ui.common import TelegramScrollBar, _show_line_edit_context_menu, _show_plain_text_context_menu
from .cursor import _refresh_cursor_under_mouse


class ProtectedLineEdit(QLineEdit):
    def __init__(self, sensitive: bool = False):
        super().__init__()
        self.sensitive = sensitive
        self.hidden_mode = False
        self._history = [""]
        self._history_index = 0
        self._restoring_history = False
        self._drag_selection_before_release = None
        self.textEdited.connect(self._record_user_text)
        self._update_enabled_cursor()

    def _update_enabled_cursor(self):
        self.setCursor(Qt.IBeamCursor if self.isEnabled() else Qt.ArrowCursor)

    def setEnabled(self, enabled):
        super().setEnabled(enabled)
        self._update_enabled_cursor()
        QTimer.singleShot(0, lambda: _refresh_cursor_under_mouse(self))

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.EnabledChange:
            self._update_enabled_cursor()
            QTimer.singleShot(0, lambda: _refresh_cursor_under_mouse(self))

    def enterEvent(self, event):
        self._update_enabled_cursor()
        super().enterEvent(event)

    def setText(self, text: str):
        self._restoring_history = True
        super().setText(text)
        self._restoring_history = False
        self._history = [text]
        self._history_index = 0
        self.setCursorPosition(len(text))
        self.deselect()

    def _record_user_text(self, text: str):
        if self._restoring_history:
            return
        if self._history and self._history[self._history_index] == text:
            return
        self._history = self._history[: self._history_index + 1]
        self._history.append(text)
        self._history_index = len(self._history) - 1

    def _restore_history_text(self, index: int):
        if index < 0 or index >= len(self._history):
            return
        self._history_index = index
        value = self._history[self._history_index]
        self._restoring_history = True
        super().setText(value)
        self._restoring_history = False
        self.setCursorPosition(len(value))
        self.deselect()

    def _undo_hidden_text(self):
        if self._history_index > 0:
            self._restore_history_text(self._history_index - 1)

    def _redo_hidden_text(self):
        if self._history_index + 1 < len(self._history):
            self._restore_history_text(self._history_index + 1)

    def _move_cursor_to_text_end(self):
        self.setCursorPosition(len(self.text()))
        self.deselect()

    def set_hidden_mode(self, hidden: bool):
        cursor_position = self.cursorPosition()
        self.hidden_mode = hidden
        self.setEchoMode(QLineEdit.Password if hidden else QLineEdit.Normal)
        self.setCursorPosition(min(cursor_position, len(self.text())))
        self.deselect()

    def focusInEvent(self, event):
        super().focusInEvent(event)
        if not QApplication.mouseButtons() & Qt.LeftButton:
            self.deselect()
        QTimer.singleShot(0, lambda: self.deselect() if not QApplication.mouseButtons() & Qt.LeftButton else None)

    def _remember_drag_selection(self):
        if self.hasSelectedText():
            start = self.selectionStart()
            self._drag_selection_before_release = (start, start + len(self.selectedText()))

    def mousePressEvent(self, event):
        self._drag_selection_before_release = None
        super().mousePressEvent(event)
        if event.button() == Qt.LeftButton:
            self._remember_drag_selection()

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        if event.buttons() & Qt.LeftButton:
            self._remember_drag_selection()

    def mouseReleaseEvent(self, event):
        before = self._drag_selection_before_release
        outside = not self.rect().contains(event.position().toPoint())
        super().mouseReleaseEvent(event)
        if event.button() == Qt.LeftButton and outside and before and not self.hasSelectedText():
            start, end = before
            self.setSelection(start, end - start)
        self._drag_selection_before_release = None

    def keyPressEvent(self, event: QKeyEvent):
        if event.modifiers() & Qt.ControlModifier:
            if self.sensitive and self.hidden_mode:
                if event.key() in (Qt.Key_C, Qt.Key_X):
                    event.accept()
                    return
                if event.key() == Qt.Key_Z:
                    if event.modifiers() & Qt.ShiftModifier:
                        self._redo_hidden_text()
                    else:
                        self._undo_hidden_text()
                    event.accept()
                    return
                if event.key() == Qt.Key_Y:
                    self._redo_hidden_text()
                    event.accept()
                    return
            if event.key() in (Qt.Key_Z, Qt.Key_Y):
                super().keyPressEvent(event)
                QTimer.singleShot(0, self._move_cursor_to_text_end)
                event.accept()
                return
        if self.hasSelectedText() and event.modifiers() == Qt.NoModifier and event.key() in (Qt.Key_Left, Qt.Key_Right):
            start = self.selectionStart()
            end = start + len(self.selectedText())
            self.deselect()
            self.setCursorPosition(start if event.key() == Qt.Key_Left else end)
            event.accept()
            return
        super().keyPressEvent(event)

    def contextMenuEvent(self, event):
        _show_line_edit_context_menu(self, event)
        event.accept()


class _DisplayOverrideOverlay(QWidget):
    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.hide()

    def paintEvent(self, event):
        owner = self.owner
        text = owner.displayOverrideText().strip()
        if not text:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#17212B"))
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), max(2, owner._radius - 1), max(2, owner._radius - 1))
        hint_font = owner.font()
        hint_font.setPointSize(max(9, hint_font.pointSize() - 1))
        painter.setFont(hint_font)
        painter.setPen(QColor("#5C7282") if not owner.isEnabled() else owner._placeholder_color)
        text_rect = self.rect().adjusted(16, 12, -16, -12)
        painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap, text)
        painter.end()


class TelegramPlainTextEdit(QPlainTextEdit):
    def __init__(self, radius: int = 11, parent=None):
        super().__init__(parent)
        self._radius = radius
        self._placeholder_color = QColor("#6F8798")
        self._hint_text = ""
        self._display_override_text = ""
        self.setObjectName("TelegramPlainTextEdit")
        self.setFrameStyle(QFrame.NoFrame)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.viewport().setAttribute(Qt.WA_StyledBackground, True)
        self.viewport().setAutoFillBackground(False)
        self.viewport().setStyleSheet("background: transparent; border: 0;")
        self.viewport().installEventFilter(self)
        self.setVerticalScrollBar(TelegramScrollBar(Qt.Vertical, self))
        self.setHorizontalScrollBar(TelegramScrollBar(Qt.Horizontal, self))
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.verticalScrollBar().setSingleStep(28)
        self.horizontalScrollBar().setSingleStep(28)
        self._last_click_time = 0.0
        self._last_click_pos = None
        self._same_place_clicks = 0
        self._custom_click_selection = False
        self._drag_selection_before_release = None
        self._drag_selecting = False
        self._drag_last_valid_selection = None
        self._display_override_overlay = _DisplayOverrideOverlay(self)
        self._update_enabled_cursor()
        self.textChanged.connect(self.viewport().update)

    def _update_enabled_cursor(self):
        cursor_shape = Qt.IBeamCursor if self.isEnabled() else Qt.ArrowCursor
        self.setCursor(cursor_shape)
        self.viewport().setCursor(cursor_shape)

    def _remember_drag_selection(self):
        cursor = self.textCursor()
        self._drag_last_valid_selection = (cursor.selectionStart(), cursor.selectionEnd())

    def setPlaceholderText(self, text: str):
        self._hint_text = text or ""
        super().setPlaceholderText("")
        self.viewport().update()

    def placeholderText(self) -> str:
        return self._hint_text

    def setDisplayOverrideText(self, text: str):
        self._display_override_text = text or ""
        self._sync_display_override_overlay()
        self.viewport().update()

    def displayOverrideText(self) -> str:
        return self._display_override_text

    def _display_override_overlay_rect(self):
        return self.rect().adjusted(12, 9, -12, -9)

    def _sync_display_override_overlay(self):
        overlay = self._display_override_overlay
        active = bool(self.displayOverrideText().strip())
        overlay.setVisible(active)
        if active:
            overlay.setGeometry(self._display_override_overlay_rect())
            overlay.raise_()
            overlay.update()

    def clear_selection_and_focus(self):
        cursor = self.textCursor()
        cursor.clearSelection()
        self.setTextCursor(cursor)
        self.clearFocus()

    def setEnabled(self, enabled):
        if not enabled:
            self.clear_selection_and_focus()
        super().setEnabled(enabled)
        self._update_enabled_cursor()
        self._sync_display_override_overlay()
        QTimer.singleShot(0, lambda: _refresh_cursor_under_mouse(self))

    def _select_line_at_position(self, pos):
        vertical = self.verticalScrollBar().value()
        horizontal = self.horizontalScrollBar().value()
        cursor = self.cursorForPosition(pos)
        cursor.select(QTextCursor.LineUnderCursor)
        self.setTextCursor(cursor)
        self.verticalScrollBar().setValue(vertical)
        self.horizontalScrollBar().setValue(horizontal)

    def _select_all_without_scroll(self):
        vertical = self.verticalScrollBar().value()
        horizontal = self.horizontalScrollBar().value()
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.Start)
        cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
        self.setTextCursor(cursor)
        self.verticalScrollBar().setValue(vertical)
        self.horizontalScrollBar().setValue(horizontal)

    def _register_plain_click(self, pos):
        now = time.time()
        same_place = self._last_click_pos is not None and (pos - self._last_click_pos).manhattanLength() <= 7
        if same_place and now - self._last_click_time <= 0.55:
            self._same_place_clicks += 1
        else:
            self._same_place_clicks = 1
        self._last_click_time = now
        self._last_click_pos = pos
        return self._same_place_clicks

    def mousePressEvent(self, event):
        self._drag_selection_before_release = None
        if event.button() == Qt.LeftButton:
            self._drag_selecting = True
            self._drag_last_valid_selection = None
            self.setFocus(Qt.MouseFocusReason)
            pos = event.position().toPoint()
            clicks = self._register_plain_click(pos)
            if clicks >= 3:
                self._select_all_without_scroll()
                self._custom_click_selection = True
                event.accept()
                return
        self._custom_click_selection = False
        super().mousePressEvent(event)
        if event.button() == Qt.LeftButton:
            self.setFocus(Qt.MouseFocusReason)
            self._remember_drag_selection()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self._drag_selecting = True
            self.setFocus(Qt.MouseFocusReason)
            self.viewport().setCursor(Qt.IBeamCursor if self.isEnabled() else Qt.ArrowCursor)
            cursor = self.textCursor()
            if cursor.hasSelection():
                self._drag_selection_before_release = (cursor.selectionStart(), cursor.selectionEnd())
        super().mouseMoveEvent(event)
        if event.buttons() & Qt.LeftButton:
            self.setFocus(Qt.MouseFocusReason)
            self._remember_drag_selection()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._custom_click_selection:
            self._drag_selecting = False
            self.setFocus(Qt.MouseFocusReason)
            event.accept()
            return
        before = self._drag_selection_before_release
        outside = not self.viewport().rect().contains(event.position().toPoint())
        super().mouseReleaseEvent(event)
        if event.button() == Qt.LeftButton and outside and before:
            cursor = self.textCursor()
            if not cursor.hasSelection():
                cursor.setPosition(before[0])
                cursor.setPosition(before[1], QTextCursor.KeepAnchor)
                self.setTextCursor(cursor)
        if event.button() == Qt.LeftButton:
            self._drag_selecting = False
            self.viewport().setCursor(Qt.IBeamCursor if self.isEnabled() else Qt.ArrowCursor)
            self.setFocus(Qt.MouseFocusReason)
        self._drag_selection_before_release = None
        self._drag_last_valid_selection = None

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.position().toPoint()
            self._same_place_clicks = 2
            self._last_click_time = time.time()
            self._last_click_pos = pos
            self._select_line_at_position(pos)
            self._custom_click_selection = True
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        cursor = self.textCursor()
        if cursor.hasSelection() and event.modifiers() == Qt.NoModifier and event.key() in (Qt.Key_Left, Qt.Key_Right):
            position = cursor.selectionStart() if event.key() == Qt.Key_Left else cursor.selectionEnd()
            cursor.setPosition(position)
            self.setTextCursor(cursor)
            event.accept()
            return
        super().keyPressEvent(event)

    def _apply_viewport_mask(self):
        viewport = self.viewport()
        if viewport is None or viewport.width() <= 0 or viewport.height() <= 0:
            return
        path = QPainterPath()
        path.addRoundedRect(QRectF(viewport.rect()).adjusted(0.5, 0.5, -0.5, -0.5), max(2, self._radius - 1), max(2, self._radius - 1))
        viewport.setMask(QRegion(path.toFillPolygon().toPolygon()))

    def eventFilter(self, watched, event):
        if watched is self.viewport() and event.type() in (QEvent.Resize, QEvent.Show):
            self._apply_viewport_mask()
            self._sync_display_override_overlay()
        return super().eventFilter(watched, event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_viewport_mask()
        self._sync_display_override_overlay()

    def showEvent(self, event):
        super().showEvent(event)
        self._apply_viewport_mask()
        self._sync_display_override_overlay()

    def contextMenuEvent(self, event):
        _show_plain_text_context_menu(self, event)
        event.accept()

    def paintEvent(self, event):
        super().paintEvent(event)
        override = self.displayOverrideText().strip()
        if override:
            return
        placeholder = "" if self.toPlainText() else self.placeholderText().strip()
        if not placeholder:
            return
        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.TextAntialiasing)
        hint_font = self.font()
        hint_font.setPointSize(max(9, hint_font.pointSize() - 1))
        painter.setFont(hint_font)
        painter.setPen(QColor("#5C7282") if not self.isEnabled() else self._placeholder_color)
        text_rect = self.viewport().rect().adjusted(14, 11, -14, -10)
        painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap, placeholder)
        painter.end()