from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QKeyEvent, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QApplication, QPushButton


class EyeToggleButton(QPushButton):
    def __init__(self, hidden: bool = False):
        super().__init__()
        self.hidden = hidden
        self.show_focus_outline = False
        self.setObjectName("EyeButton")
        self.setFixedSize(36, 36)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.TabFocus)
        self.setFlat(True)


    def focusInEvent(self, event):
        self.show_focus_outline = event.reason() in (Qt.TabFocusReason, Qt.BacktabFocusReason)
        super().focusInEvent(event)
        self.update()

    def focusOutEvent(self, event):
        self.show_focus_outline = False
        super().focusOutEvent(event)
        self.update()

    def mousePressEvent(self, event):
        self.show_focus_outline = False
        if event.button() == Qt.LeftButton and self.rect().contains(event.position().toPoint()):
            self.setDown(True)
            event.accept()
            self.update()
            return
        super().mousePressEvent(event)
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            inside = self.rect().contains(event.position().toPoint())
            self.setDown(False)
            if inside:
                self.click()
                self.clearFocus()
            event.accept()
            self.update()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            self.click()
            event.accept()
            self.update()
            return
        super().keyPressEvent(event)

    def set_hidden_state(self, hidden: bool):
        self.hidden = hidden
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(Qt.NoBrush)
        cx = self.width() / 2
        cy = self.height() / 2
        pen = QPen(QColor("#FFFFFF"))
        pen.setWidthF(1.8)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        eye = QPainterPath()
        eye.moveTo(cx - 10.5, cy)
        eye.cubicTo(cx - 6.0, cy - 6.0, cx + 6.0, cy - 6.0, cx + 10.5, cy)
        eye.cubicTo(cx + 6.0, cy + 6.0, cx - 6.0, cy + 6.0, cx - 10.5, cy)
        painter.drawPath(eye)
        if not self.hidden:
            painter.setBrush(QColor("#FFFFFF"))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QRectF(cx - 2.8, cy - 2.8, 5.6, 5.6))
        else:
            painter.setBrush(Qt.NoBrush)
            painter.setPen(pen)
            painter.drawLine(QPointF(cx - 10.0, cy + 8.5), QPointF(cx + 10.0, cy - 8.5))
        if self.hasFocus() and self.show_focus_outline:
            focus_pen = QPen(QColor("#5BC8FF"))
            focus_pen.setWidthF(1.4)
            focus_pen.setCapStyle(Qt.RoundCap)
            focus_pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(focus_pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(QRectF(5.5, 5.5, self.width() - 11, self.height() - 11), 8, 8)
        painter.end()


class NoMouseFocusButton(QPushButton):
    def __init__(self, text: str = ""):
        super().__init__(text)
        self._mouse_pressed = False
        self.setFocusPolicy(Qt.TabFocus)
        self._set_keyboard_focus_property(False)

    def _set_keyboard_focus_property(self, value: bool):
        current = self.property("keyboardFocus")
        text_value = "true" if value else "false"
        if current == text_value:
            return
        self.setProperty("keyboardFocus", text_value)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()
        self.repaint()

    def _clear_mouse_focus(self):
        self._set_keyboard_focus_property(False)
        if hasattr(self, "_suppress_hover"):
            self._suppress_hover = True
        if self.hasFocus():
            self.clearFocus()
        window = self.window()
        if window is not None and window is not self:
            window.setFocus(Qt.OtherFocusReason)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._mouse_pressed = self.rect().contains(event.position().toPoint())
            self._set_keyboard_focus_property(False)
            if self._mouse_pressed:
                self.setDown(True)
                event.accept()
                self.update()
                return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._mouse_pressed:
            inside = self.rect().contains(event.position().toPoint())
            self.setDown(False)
            self._mouse_pressed = False
            if inside and self.isEnabled():
                self.click()
            self._clear_mouse_focus()
            QTimer.singleShot(0, self._clear_mouse_focus)
            QTimer.singleShot(30, self._clear_mouse_focus)
            event.accept()
            self.update()
            return
        self._mouse_pressed = False
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        self._set_keyboard_focus_property(True)
        super().keyPressEvent(event)

    def focusInEvent(self, event):
        self._set_keyboard_focus_property(event.reason() in (Qt.TabFocusReason, Qt.BacktabFocusReason))
        super().focusInEvent(event)
        if event.reason() == Qt.MouseFocusReason:
            QTimer.singleShot(0, self._clear_mouse_focus)

    def focusOutEvent(self, event):
        self._mouse_pressed = False
        self._set_keyboard_focus_property(False)
        super().focusOutEvent(event)


class CollapseToggleButton(NoMouseFocusButton):
    def __init__(self):
        super().__init__("")
        self.collapsed = False
        self._suppress_hover = False
        self._mouse_pressed = False
        self.setObjectName("CollapseButton")
        self.setFixedSize(38, 20)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.TabFocus)

    def set_collapsed_state(self, collapsed: bool):
        self.collapsed = collapsed
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.isEnabled():
            self._last_trigger_by_mouse = True
            self._mouse_pressed = self.rect().contains(event.position().toPoint())
            self._suppress_hover = True
            self._set_keyboard_focus_property(False)
            self.setDown(self._mouse_pressed)
            event.accept()
            self.update()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._mouse_pressed:
            inside = self.rect().contains(event.position().toPoint())
            self.setDown(False)
            self._mouse_pressed = False
            self._suppress_hover = True
            if inside and self.isEnabled():
                self.click()
            self._clear_mouse_focus()
            event.accept()
            self.update()
            QTimer.singleShot(0, self._clear_mouse_focus)
            QTimer.singleShot(30, self._clear_mouse_focus)
            return
        self._mouse_pressed = False
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        inside = self.rect().contains(event.position().toPoint())
        if self._mouse_pressed or event.buttons() & Qt.LeftButton:
            self._suppress_hover = not inside
            self.setDown(inside)
        else:
            self._suppress_hover = False
        super().mouseMoveEvent(event)
        self.update()

    def leaveEvent(self, event):
        if self._mouse_pressed or QApplication.mouseButtons() & Qt.LeftButton:
            self._suppress_hover = True
            self.setDown(False)
        else:
            self._suppress_hover = False
        super().leaveEvent(event)
        self.update()

    def focusInEvent(self, event):
        if event.reason() in (Qt.TabFocusReason, Qt.BacktabFocusReason):
            self._last_trigger_by_mouse = False
        super().focusInEvent(event)
        if event.reason() == Qt.MouseFocusReason:
            self._last_trigger_by_mouse = True
            QTimer.singleShot(0, self._clear_mouse_focus)
            QTimer.singleShot(30, self._clear_mouse_focus)

    def focusOutEvent(self, event):
        self._mouse_pressed = False
        self._set_keyboard_focus_property(False)
        super().focusOutEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        if not self.isEnabled():
            bg = QColor("#0D151C")
            border = QColor("#1C2A36")
            arrow = QColor("#556675")
        elif self.isDown():
            bg = QColor("#0D151C")
            border = QColor("#2AABEE")
            arrow = QColor("#FFFFFF")
        elif self.hasFocus() and not getattr(self, "_last_trigger_by_mouse", False):
            bg = QColor("#111A22")
            border = QColor("#5BC8FF")
            arrow = QColor("#FFFFFF")
        elif self.underMouse() and not self._suppress_hover:
            bg = QColor("#1C2733")
            border = QColor("#3E6485")
            arrow = QColor("#FFFFFF")
        else:
            bg = QColor("#111A22")
            border = QColor("#263847")
            arrow = QColor("#AFC2D3")
        painter.setPen(QPen(border, 1.2))
        painter.setBrush(bg)
        painter.drawRoundedRect(rect, 10, 10)
        cx = rect.center().x()
        cy = rect.center().y()
        triangle = QPainterPath()
        half_width = 4.3
        half_height = 2.9
        if self.collapsed:
            triangle.moveTo(cx - half_width, cy - half_height)
            triangle.lineTo(cx + half_width, cy - half_height)
            triangle.lineTo(cx, cy + half_height)
        else:
            triangle.moveTo(cx - half_width, cy + half_height)
            triangle.lineTo(cx + half_width, cy + half_height)
            triangle.lineTo(cx, cy - half_height)
        triangle.closeSubpath()
        painter.setPen(Qt.NoPen)
        painter.setBrush(arrow)
        painter.drawPath(triangle)
        painter.end()