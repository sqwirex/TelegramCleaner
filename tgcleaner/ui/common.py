from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QMenu,
)
from tgcleaner.core.i18n import T


def _styled_text_menu(parent):
    menu = QMenu(parent)
    menu.setStyleSheet("""
        QMenu {
            background-color: #17212B;
            color: #E8F2F8;
            border: 1px solid #334657;
            border-radius: 10px;
            padding: 6px;
            font-family: Segoe UI;
            font-size: 13px;
        }
        QMenu::item {
            padding: 7px 34px 7px 12px;
            border-radius: 7px;
            background-color: transparent;
        }
        QMenu::item:selected {
            background-color: #2AABEE;
            color: #FFFFFF;
        }
        QMenu::item:disabled {
            color: #617180;
        }
        QMenu::separator {
            height: 1px;
            background-color: #293A4A;
            margin: 6px 4px;
        }
    """)
    return menu


def _add_menu_action(menu, text, shortcut, enabled, callback):
    title = f"{text}    {shortcut}" if shortcut else text
    action = QAction(title, menu)
    action.setEnabled(enabled)
    action.triggered.connect(callback)
    menu.addAction(action)
    return action


def _show_line_edit_context_menu(widget, event):
    selected = widget.hasSelectedText()
    readonly = widget.isReadOnly()
    clipboard_text = QApplication.clipboard().text()
    text_exists = bool(widget.text())
    protected = getattr(widget, "sensitive", False) and getattr(widget, "hidden_mode", False)
    menu = _styled_text_menu(widget)
    _add_menu_action(menu, T.MENU_UNDO, "Ctrl+Z", widget.isUndoAvailable() and not readonly, widget.undo)
    _add_menu_action(menu, T.MENU_REDO, "Ctrl+Y", widget.isRedoAvailable() and not readonly, widget.redo)
    menu.addSeparator()
    _add_menu_action(menu, T.MENU_CUT, "Ctrl+X", selected and not readonly and not protected, widget.cut)
    _add_menu_action(menu, T.MENU_COPY, "Ctrl+C", selected and not protected, widget.copy)
    _add_menu_action(menu, T.MENU_PASTE, "Ctrl+V", bool(clipboard_text) and not readonly, widget.paste)
    _add_menu_action(menu, T.MENU_DELETE, "", selected and not readonly, widget.del_)
    menu.addSeparator()
    _add_menu_action(menu, T.MENU_SELECT_ALL, "Ctrl+A", text_exists, widget.selectAll)
    menu.exec(event.globalPos())


def _show_plain_text_context_menu(widget, event):
    cursor = widget.textCursor()
    selected = cursor.hasSelection()
    readonly = widget.isReadOnly()
    clipboard_text = QApplication.clipboard().text()
    text_exists = widget.document().characterCount() > 1
    menu = _styled_text_menu(widget)
    _add_menu_action(menu, T.MENU_UNDO, "Ctrl+Z", widget.document().isUndoAvailable() and not readonly, widget.undo)
    _add_menu_action(menu, T.MENU_REDO, "Ctrl+Y", widget.document().isRedoAvailable() and not readonly, widget.redo)
    menu.addSeparator()
    _add_menu_action(menu, T.MENU_CUT, "Ctrl+X", selected and not readonly, widget.cut)
    _add_menu_action(menu, T.MENU_COPY, "Ctrl+C", selected, widget.copy)
    _add_menu_action(menu, T.MENU_PASTE, "Ctrl+V", bool(clipboard_text) and not readonly, widget.paste)
    def delete_selection():
        active_cursor = widget.textCursor()
        active_cursor.removeSelectedText()
        widget.setTextCursor(active_cursor)
    _add_menu_action(menu, T.MENU_DELETE, "", selected and not readonly, delete_selection)
    menu.addSeparator()
    if hasattr(widget, "_select_all_without_scroll"):
        select_all = widget._select_all_without_scroll
    else:
        select_all = widget.selectAll
    _add_menu_action(menu, T.MENU_SELECT_ALL, "Ctrl+A", text_exists, select_all)
    menu.exec(event.globalPos())

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QScrollBar,
)


class RoundedClipFrame(QFrame):
    def __init__(self, radius: int = 16, background_color: str = "transparent", border_color: str = "transparent", parent=None):
        super().__init__(parent)
        self._radius = radius
        self._background_color = QColor(background_color)
        self._border_color = QColor(border_color)
        self.setAttribute(Qt.WA_StyledBackground, True)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1.2, 1.2, -1.2, -1.2)
        if self._background_color.alpha() > 0:
            painter.setPen(Qt.NoPen)
            painter.setBrush(self._background_color)
            painter.drawRoundedRect(rect, self._radius, self._radius)
        if self._border_color.alpha() > 0:
            painter.setPen(QPen(self._border_color, 1.6))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(rect, self._radius, self._radius)
        painter.end()


class TelegramScrollBar(QScrollBar):
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self._pressed = False
        self._hovered = False
        self._drag_offset = 0.0
        self._handle_rect = QRectF()
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)
        if orientation == Qt.Vertical:
            self.setFixedWidth(12)
        else:
            self.setFixedHeight(12)

    def _track_rect(self) -> QRectF:
        offset = self.property("handleOffset")
        try:
            offset = int(offset)
        except Exception:
            offset = 0
        if self.orientation() == Qt.Vertical:
            return QRectF(2 + offset, 4, max(0, self.width() - 4 - offset), max(0, self.height() - 8))
        return QRectF(4, 2 + offset, max(0, self.width() - 8), max(0, self.height() - 4 - offset))

    def _calculate_handle_rect(self) -> QRectF:
        track = self._track_rect()
        span = track.height() if self.orientation() == Qt.Vertical else track.width()
        value_range = self.maximum() - self.minimum()
        if span <= 0 or value_range <= 0:
            return QRectF()
        total = value_range + max(1, self.pageStep())
        handle_len = max(40.0, span * (self.pageStep() / total))
        handle_len = min(handle_len, span)
        available = max(0.0, span - handle_len)
        ratio = (self.value() - self.minimum()) / value_range if value_range > 0 else 0.0
        offset = available * ratio
        if self.orientation() == Qt.Vertical:
            return QRectF(track.left(), track.top() + offset, track.width(), handle_len)
        return QRectF(track.left() + offset, track.top(), handle_len, track.height())

    def paintEvent(self, event):
        if bool(self.property("resizeOverlayHidden")):
            painter = QPainter(self)
            painter.fillRect(self.rect(), QColor("#07131E"))
            painter.end()
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        track_background = self.property("trackBackground")
        if isinstance(track_background, str) and track_background and track_background.lower() != "transparent":
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(track_background))
            painter.drawRect(self.rect())
        self._handle_rect = self._calculate_handle_rect()
        if self._handle_rect.isNull() or self._handle_rect.isEmpty():
            return
        color = QColor("#3D586E")
        if self._pressed:
            color = QColor("#2AABEE")
        elif self._hovered:
            color = QColor("#5D7D95")
        painter.setPen(Qt.NoPen)
        painter.setBrush(color)
        radius = 4 if self.orientation() == Qt.Vertical else 4
        painter.drawRoundedRect(self._handle_rect, radius, radius)

    def _set_value_from_handle_top(self, handle_top: float):
        track = self._track_rect()
        handle = self._calculate_handle_rect()
        if handle.isNull() or handle.isEmpty():
            return
        span = track.height() if self.orientation() == Qt.Vertical else track.width()
        handle_len = handle.height() if self.orientation() == Qt.Vertical else handle.width()
        available = max(0.0, span - handle_len)
        if available <= 0:
            self.setValue(self.minimum())
            return
        start = track.top() if self.orientation() == Qt.Vertical else track.left()
        clamped = max(0.0, min(available, handle_top - start))
        ratio = clamped / available
        value = self.minimum() + ratio * (self.maximum() - self.minimum())
        self.setValue(round(value))

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() != Qt.LeftButton:
            super().mousePressEvent(event)
            return
        self._handle_rect = self._calculate_handle_rect()
        point = event.position()
        axis = point.y() if self.orientation() == Qt.Vertical else point.x()
        handle_start = self._handle_rect.top() if self.orientation() == Qt.Vertical else self._handle_rect.left()
        handle_len = self._handle_rect.height() if self.orientation() == Qt.Vertical else self._handle_rect.width()
        if self._handle_rect.contains(point):
            self._drag_offset = axis - handle_start
        else:
            self._drag_offset = handle_len / 2
            self._set_value_from_handle_top(axis - self._drag_offset)
            self._handle_rect = self._calculate_handle_rect()
        self._pressed = True
        self.update()
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        point = event.position()
        if self._pressed:
            axis = point.y() if self.orientation() == Qt.Vertical else point.x()
            self._set_value_from_handle_top(axis - self._drag_offset)
        self._handle_rect = self._calculate_handle_rect()
        self._hovered = self._handle_rect.contains(point)
        self.update()
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._pressed = False
        self._handle_rect = self._calculate_handle_rect()
        self._hovered = self._handle_rect.contains(event.position())
        self.update()
        event.accept()

    def leaveEvent(self, event):
        self._hovered = False
        if not self._pressed:
            self.update()
        super().leaveEvent(event)


from PySide6.QtCore import QEvent, QRect, Qt, QTimer
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

class StyledMessageDialog(QDialog):
    def __init__(self, parent, title: str, text: str, kind: str = "info", buttons: tuple[str, ...] = ("OK",), danger_confirm: bool = False, copy_text: str | None = None):
        super().__init__(parent)
        self.clicked_button = None
        self._copy_text = copy_text
        self.setWindowTitle(title)
        self.setModal(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setSizeGripEnabled(False)
        self.setWindowFlag(Qt.FramelessWindowHint, True)
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, False)
        self.setWindowFlag(Qt.WindowMinMaxButtonsHint, False)
        self.setWindowFlag(Qt.MSWindowsFixedSizeDialogHint, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMinimumWidth(340)
        self.setStyleSheet("""
            QDialog {
                background-color: transparent;
                color: #E8F2F8;
                border: 0;
            }
            QFrame#DialogPanel {
                background-color: #17212B;
                border: 1px solid #3A5268;
                border-radius: 18px;
            }
            QLabel {
                background-color: transparent;
                color: #E8F2F8;
                border: 0;
            }
            QPushButton {
                background-color: #2AABEE;
                color: #FFFFFF;
                border: 1px solid transparent;
                border-radius: 10px;
                outline: none;
                padding: 6px 16px;
                min-width: 72px;
                min-height: 28px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #39B8F3;
            }
            QPushButton[keyboardFocus="true"]:focus {
                border: 1px solid #92DDFF;
            }
            QPushButton#SecondaryDialogButton {
                background-color: #1C2733;
                border: 1px solid #334657;
            }
            QPushButton#SecondaryDialogButton:hover {
                background-color: #26384A;
            }
            QPushButton#SecondaryDialogButton[keyboardFocus="true"]:focus {
                border: 1px solid #92DDFF;
            }
            QPushButton#SecondaryDialogButton[keyboardFocus="false"]:focus {
                border: 1px solid #334657;
            }
            QPushButton#DangerDialogButton {
                background-color: #E85D75;
                border: 1px solid transparent;
            }
            QPushButton#DangerDialogButton:hover {
                background-color: #F06F86;
            }
            QPushButton#DangerDialogButton[keyboardFocus="true"]:focus {
                border: 1px solid #FFB5BE;
            }
            QPushButton#DangerDialogButton[keyboardFocus="false"]:focus {
                border: 1px solid transparent;
            }
        """)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(0)
        panel = QFrame(self)
        panel.setObjectName("DialogPanel")
        shadow = QGraphicsDropShadowEffect(panel)
        shadow.setBlurRadius(36)
        shadow.setOffset(0, 10)
        shadow.setColor(QColor(0, 0, 0, 175))
        panel.setGraphicsEffect(shadow)
        outer.addWidget(panel)
        root = QVBoxLayout(panel)
        root.setContentsMargins(22, 20, 22, 18)
        root.setSpacing(16)
        row = QHBoxLayout()
        row.setSpacing(14)
        icon = QLabel()
        icon.setFixedSize(34, 34)
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("""
            QLabel {
                border-radius: 17px;
                background-color: #2AABEE;
                color: #FFFFFF;
                font-size: 18px;
                font-weight: 700;
                padding-bottom: 1px;
            }
        """)
        if kind == "warning":
            icon.setText("!")
            icon.setStyleSheet(icon.styleSheet().replace("#2AABEE", "#E9B949"))
        elif kind == "error":
            icon.setText("✕")
            icon.setStyleSheet(icon.styleSheet().replace("#2AABEE", "#E85D75"))
        elif kind == "question":
            icon.setText("?")
        else:
            icon.setText("✓")
        content = QVBoxLayout()
        content.setSpacing(5)
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 15px; font-weight: 700; color: #FFFFFF; border: 0;")
        title_label.setWordWrap(True)
        title_label.setTextInteractionFlags(Qt.NoTextInteraction)
        title_label.setFocusPolicy(Qt.NoFocus)
        message_label = QLabel(text)
        message_label.setWordWrap(True)
        message_label.setTextInteractionFlags(Qt.NoTextInteraction)
        message_label.setFocusPolicy(Qt.NoFocus)
        message_label.setCursor(Qt.ArrowCursor)
        path_like = "\\" in text or "/" in text
        label_width = 760 if path_like else (600 if len(text) > 90 else 430)
        message_label.setMinimumWidth(520 if path_like else (360 if label_width > 430 else 230))
        message_label.setMaximumWidth(label_width)
        message_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        message_label.setStyleSheet("font-size: 14px; color: #DDE9F2; background-color: transparent; border: 0;")
        text_bounds = QFontMetrics(message_label.font()).boundingRect(QRect(0, 0, label_width, 2000), Qt.TextWordWrap, text)
        message_label.setMinimumHeight(max(24, text_bounds.height() + 6))
        content.addWidget(title_label)
        content.addWidget(message_label)
        row.addWidget(icon, 0, Qt.AlignTop)
        row.addLayout(content, 1)
        root.addLayout(row)
        button_row = QHBoxLayout()
        from tgcleaner.ui.widgets.buttons import NoMouseFocusButton
        self._dialog_buttons = []
        self._preferred_initial_button = None
        if copy_text:
            copy_button = NoMouseFocusButton(T.BUTTON_COPY_ERROR)
            copy_button.setFocusPolicy(Qt.TabFocus)
            copy_button.setCursor(Qt.PointingHandCursor)
            copy_button.setAutoDefault(False)
            copy_button.setDefault(False)
            copy_button.setObjectName("SecondaryDialogButton")
            copy_button.clicked.connect(self._copy_error_text)
            button_row.addWidget(copy_button)
            self._dialog_buttons.append(copy_button)
        button_row.addStretch(1)
        for i, button_text in enumerate(buttons):
            button = NoMouseFocusButton(button_text)
            button.setFocusPolicy(Qt.TabFocus)
            button.setCursor(Qt.PointingHandCursor)
            button.setAutoDefault(False)
            button.setDefault(False)
            if danger_confirm and i == 0:
                button.setObjectName("DangerDialogButton")
            else:
                button.setObjectName("SecondaryDialogButton")
            button.clicked.connect(lambda checked=False, value=button_text: self._finish(value))
            button_row.addWidget(button)
            self._dialog_buttons.append(button)
            if not danger_confirm and self._preferred_initial_button is None:
                self._preferred_initial_button = button
            elif danger_confirm and i == len(buttons) - 1:
                self._preferred_initial_button = button
        root.addLayout(button_row)
        for widget in self.findChildren(QWidget):
            widget.installEventFilter(self)
        self.installEventFilter(self)
        self.adjustSize()
        self._dialog_fixed_size = self.sizeHint()
        self.setMinimumSize(self._dialog_fixed_size)
        self.setMaximumSize(self._dialog_fixed_size)
        self.setFixedSize(self._dialog_fixed_size)
        QTimer.singleShot(0, self._clear_dialog_focus)
        QTimer.singleShot(30, self._clear_dialog_focus)

    def _repaint_dialog_buttons(self):
        for button in self._dialog_buttons:
            if hasattr(button, "_set_keyboard_focus_property"):
                button._set_keyboard_focus_property(False)
            button.setDown(False)
            button.update()
            button.repaint()
        self.update()
        self.repaint()

    def _clear_dialog_focus(self):
        focused = QApplication.focusWidget()
        if focused is not None and focused is not self:
            focused.clearFocus()
        self._repaint_dialog_buttons()
        self.setFocus(Qt.OtherFocusReason)

    def _move_button_focus(self, reverse: bool):
        buttons = [button for button in self._dialog_buttons if button.isEnabled() and button.isVisible()]
        if not buttons:
            self._clear_dialog_focus()
            return
        focused = QApplication.focusWidget()
        if focused not in buttons:
            target = buttons[-1] if reverse else (self._preferred_initial_button or buttons[0])
        else:
            index = buttons.index(focused)
            next_index = (index - 1) % len(buttons) if reverse else (index + 1) % len(buttons)
            focused.clearFocus()
            target = buttons[next_index]
        self._repaint_dialog_buttons()
        target.setFocus(Qt.BacktabFocusReason if reverse else Qt.TabFocusReason)
        if hasattr(target, "_set_keyboard_focus_property"):
            target._set_keyboard_focus_property(True)
        target.update()
        target.repaint()

    def _handle_dialog_key(self, event):
        if event.key() in (Qt.Key_Tab, Qt.Key_Backtab):
            reverse = event.key() == Qt.Key_Backtab or bool(event.modifiers() & Qt.ShiftModifier)
            self._move_button_focus(reverse)
            event.accept()
            return True
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            focused = QApplication.focusWidget()
            if focused in self._dialog_buttons and focused.isEnabled():
                focused.click()
            event.accept()
            return True
        if event.key() == Qt.Key_Escape:
            self._clear_dialog_focus()
            event.accept()
            return True
        return False

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress and self._handle_dialog_key(event):
            return True
        if obj in self._dialog_buttons:
            if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                inside = obj.rect().contains(event.position().toPoint())
                obj._dialog_mouse_pressed = inside
                self._repaint_dialog_buttons()
                obj._set_keyboard_focus_property(False)
                if inside:
                    obj.setDown(True)
                    event.accept()
                    return True
            if event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
                inside = obj.rect().contains(event.position().toPoint())
                pressed = bool(getattr(obj, "_dialog_mouse_pressed", False))
                obj._dialog_mouse_pressed = False
                obj.setDown(False)
                obj._set_keyboard_focus_property(False)
                if pressed and inside and obj.isEnabled():
                    obj.click()
                self._repaint_dialog_buttons()
                QTimer.singleShot(0, self._clear_dialog_focus)
                event.accept()
                return True
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event):
        if self._handle_dialog_key(event):
            return
        super().keyPressEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        self.setFixedSize(self._dialog_fixed_size)
        QTimer.singleShot(0, lambda: self.setFixedSize(self._dialog_fixed_size))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "_dialog_fixed_size") and self.size() != self._dialog_fixed_size:
            QTimer.singleShot(0, lambda: self.setFixedSize(self._dialog_fixed_size))

    def _copy_error_text(self):
        if self._copy_text:
            QApplication.clipboard().setText(self._copy_text)
        self._clear_dialog_focus()

    def _finish(self, value: str):
        self.clicked_button = value
        self.accept()

from PySide6.QtWidgets import (
    QProxyStyle,
    QStyle,
)


class NoFocusRectStyle(QProxyStyle):
    def drawPrimitive(self, element, option, painter, widget=None):
        if element == QStyle.PE_FrameFocusRect:
            return
        super().drawPrimitive(element, option, painter, widget)