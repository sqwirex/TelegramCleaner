from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QCheckBox

from tgcleaner.core.i18n import T


class StyledCheckBox(QCheckBox):
    def __init__(self, text: str):
        super().__init__(text)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(32)
        self.setFocusPolicy(Qt.TabFocus)
        self.show_focus_outline = False
        self._compact_width = False
        self._update_minimum_width()

    def hitButton(self, pos):
        return self.rect().contains(pos)

    def _checkbox_width(self):
        text_width = self.fontMetrics().horizontalAdvance(self.text())
        width = int(text_width + 50)
        return width if self._compact_width else max(92, width)

    def _update_minimum_width(self):
        self.setMinimumWidth(self._checkbox_width())

    def setCompactWidth(self, compact: bool):
        self._compact_width = bool(compact)
        self._update_minimum_width()
        self.updateGeometry()
        self.update()

    def minimumSizeHint(self):
        hint = super().minimumSizeHint()
        return QSize(self.minimumWidth(), max(self.minimumHeight(), hint.height()))

    def sizeHint(self):
        hint = super().sizeHint()
        width = self.minimumWidth() if self._compact_width else max(self.minimumWidth(), hint.width())
        return QSize(width, max(self.minimumHeight(), hint.height()))

    def setText(self, text):
        super().setText(text)
        self._update_minimum_width()
        self.updateGeometry()
        self.update()

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
        super().mousePressEvent(event)
        self.update()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if event.button() == Qt.LeftButton:
            self.clearFocus()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        box_size = 18
        x = 9
        y = (self.height() - box_size) / 2
        rect = QRectF(x, y, box_size, box_size)

        enabled = self.isEnabled()
        border = QColor("#385365") if enabled else QColor("#24313A")
        fill = QColor("#2AABEE") if self.isChecked() and enabled else QColor("#17212B")
        if not enabled:
            fill = QColor("#111820")

        painter.setPen(QPen(border, 1.2))
        painter.setBrush(fill)
        painter.drawRoundedRect(rect, 5, 5)

        if self.isChecked():
            pen = QPen(QColor("#FFFFFF") if enabled else QColor("#80878C"), 2.0)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(pen)
            path = QPainterPath()
            path.moveTo(x + 4.5, y + 9.3)
            path.lineTo(x + 7.8, y + 12.4)
            path.lineTo(x + 13.8, y + 5.6)
            painter.drawPath(path)

        painter.setPen(QColor("#E8F2F8") if enabled else QColor("#6C7A86"))
        text_x = int(x + box_size + 10)
        text_width = painter.fontMetrics().horizontalAdvance(self.text())
        painter.drawText(text_x, 0, self.width() - text_x - 2, self.height(), Qt.AlignVCenter | Qt.AlignLeft, self.text())

        if self.hasFocus() and self.show_focus_outline:
            focus_pen = QPen(QColor("#5BC8FF"), 1.35)
            focus_pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(focus_pen)
            painter.setBrush(Qt.NoBrush)
            focus_width = min(self.width() - 4, text_x + text_width + 10)
            focus_x = 2.0 if self.text() == T.CHECKBOX_ONLY_GROUPS else 0.5
            painter.drawRoundedRect(QRectF(focus_x, 3.5, focus_width, self.height() - 7), 8, 8)

        painter.end()