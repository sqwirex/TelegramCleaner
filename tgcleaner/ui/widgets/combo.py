from PySide6.QtCore import QEvent, QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QCursor, QKeyEvent, QMouseEvent, QPainter
from PySide6.QtWidgets import QApplication, QComboBox, QLabel, QStyle, QStyledItemDelegate


class ComboPopupItemDelegate(QStyledItemDelegate):
    def __init__(self, parent=None, gap: int = 3):
        super().__init__(parent)
        self.gap = gap
        self.horizontal_padding = 12
        self.vertical_padding = 14
        self.minimum_item_height = 34
        self.left_margin = 0
        self.right_margin = 9

    def _popup_width(self, option) -> int:
        view = self.parent()
        width = option.rect.width()
        if view is not None and hasattr(view, "viewport"):
            viewport_width = view.viewport().width()
            if viewport_width > 0:
                width = viewport_width
        return max(40, width)

    def _text_width_limit(self, option) -> int:
        width = option.rect.width()
        if width <= 0:
            width = self._popup_width(option)
        return max(24, width - self.left_margin - self.right_margin - self.horizontal_padding * 2)

    def _break_word(self, word: str, max_width: int, font_metrics) -> list[str]:
        parts = []
        current = ""
        for char in str(word):
            candidate = current + char
            if current and font_metrics.horizontalAdvance(candidate) > max_width:
                parts.append(current)
                current = char
            else:
                current = candidate
        if current:
            parts.append(current)
        return parts or [""]

    def _wrapped_lines(self, text: str, max_width: int, font_metrics) -> list[str]:
        lines = []
        current = ""
        for word in str(text or "").split():
            parts = [word] if font_metrics.horizontalAdvance(word) <= max_width else self._break_word(word, max_width, font_metrics)
            for part in parts:
                if not current:
                    current = part
                    continue
                candidate = f"{current} {part}"
                if font_metrics.horizontalAdvance(candidate) <= max_width:
                    current = candidate
                else:
                    lines.append(current)
                    current = part
        if current:
            lines.append(current)
        return lines or [""]

    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        text = index.data(Qt.DisplayRole) or ""
        max_width = self._text_width_limit(option)
        lines = self._wrapped_lines(text, max_width, option.fontMetrics)
        height = max(self.minimum_item_height, len(lines) * option.fontMetrics.lineSpacing() + self.vertical_padding + 4)
        model = index.model()
        if model is not None and index.row() < model.rowCount(index.parent()) - 1:
            height += self.gap
        size.setWidth(self._popup_width(option))
        size.setHeight(height)
        return size

    def paint(self, painter, option, index):
        option_rect = QRectF(option.rect)
        painter.setClipRect(option_rect.adjusted(0, 0, -1, 0))
        rect = option_rect.adjusted(self.left_margin, 0, -self.right_margin, 0)
        model = index.model()
        if model is not None and index.row() < model.rowCount(index.parent()) - 1:
            rect = rect.adjusted(0, 0, 0, -self.gap)
        selected = bool(option.state & QStyle.State_Selected)
        hovered = bool(option.state & QStyle.State_MouseOver)
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        if selected:
            painter.setBrush(QColor("#3E6380"))
        elif hovered:
            painter.setBrush(QColor("#223140"))
        else:
            painter.setBrush(QColor("#17212B"))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(rect, 6, 6)
        text = str(index.data(Qt.DisplayRole) or "")
        text_rect = rect.adjusted(self.horizontal_padding, 5, -self.horizontal_padding, -5)
        max_width = max(24, int(text_rect.width()))
        lines = self._wrapped_lines(text, max_width, option.fontMetrics)
        line_height = option.fontMetrics.lineSpacing()
        total_height = len(lines) * line_height
        y = text_rect.y() + max(0, (text_rect.height() - total_height) // 2) + option.fontMetrics.ascent()
        painter.setPen(QColor("#FFFFFF") if selected else QColor("#E8F2F8"))
        for line in lines:
            painter.drawText(text_rect.x(), y, line)
            y += line_height
        painter.restore()


class ResponsiveStatusLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.setWordWrap(False)
        self.setContentsMargins(0, 0, 14, 0)
        self.setToolTip(text)

    def setText(self, text):
        super().setText(text)
        self.setToolTip(text)
        self.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.setWordWrap(False)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.TextAntialiasing)
        painter.setPen(self.palette().color(self.foregroundRole()))
        rect = self.contentsRect()
        text = self.fontMetrics().elidedText(self.text(), Qt.ElideRight, max(0, rect.width()))
        painter.drawText(rect, Qt.AlignLeft | Qt.AlignVCenter | Qt.TextSingleLine, text)
        painter.end()


class KeyboardComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._popup_open = False
        self._popup_opened_by_mouse = False
        self._keyboard_focus = False
        self.view().installEventFilter(self)
        self.view().viewport().installEventFilter(self)
        self.view().setSpacing(0)
        self.view().setContentsMargins(0, 0, 0, 0)
        self.view().viewport().setContentsMargins(0, 0, 0, 0)
        self.view().setTextElideMode(Qt.ElideNone)
        self.view().setWordWrap(True)
        self.view().setUniformItemSizes(False)
        self.view().setItemDelegate(ComboPopupItemDelegate(self.view(), 3))
        try:
            self.view().setResizeMode(self.view().ResizeMode.Adjust)
        except Exception:
            pass
        self.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.setMinimumContentsLength(12)
        self.setFocusPolicy(Qt.StrongFocus)
        self.view().setMouseTracking(True)
        self.view().viewport().setMouseTracking(True)
        try:
            from tgcleaner.ui.common import TelegramScrollBar
            scrollbar = TelegramScrollBar(Qt.Vertical, self.view())
            scrollbar.setAutoFillBackground(False)
            scrollbar.setAttribute(Qt.WA_NoSystemBackground, True)
            scrollbar.setAttribute(Qt.WA_TranslucentBackground, True)
            scrollbar.setStyleSheet("background: #17212B; background-color: #17212B; border: 0;")
            scrollbar.setProperty("trackBackground", "#17212B")
            scrollbar.setProperty("handleOffset", 2)
            self.view().setVerticalScrollBar(scrollbar)
            scrollbar.valueChanged.connect(self._refresh_popup_hover_under_cursor)
        except Exception:
            pass

    def _refresh_popup_hover_under_cursor(self):
        if not self._popup_open:
            return
        view = self.view()
        viewport = view.viewport()
        pos = viewport.mapFromGlobal(QCursor.pos())
        if viewport.rect().contains(pos):
            event = QMouseEvent(QEvent.MouseMove, QPointF(pos), viewport.mapToGlobal(pos), Qt.NoButton, Qt.NoButton, Qt.NoModifier)
            QApplication.sendEvent(viewport, event)
        viewport.update()

    def focusInEvent(self, event):
        self._keyboard_focus = event.reason() in (Qt.TabFocusReason, Qt.BacktabFocusReason)
        self.setProperty("keyboardFocus", self._keyboard_focus)
        self.style().unpolish(self)
        self.style().polish(self)
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        self._keyboard_focus = False
        self.setProperty("keyboardFocus", False)
        self.style().unpolish(self)
        self.style().polish(self)
        super().focusOutEvent(event)

    def mousePressEvent(self, event):
        self._popup_opened_by_mouse = True
        self._keyboard_focus = False
        self.setProperty("keyboardFocus", False)
        self.style().unpolish(self)
        self.style().polish(self)
        super().mousePressEvent(event)
        QTimer.singleShot(0, self.clearFocus)

    def showPopup(self):
        view = self.view()
        view.setFixedWidth(self.width())
        view.viewport().setFixedWidth(max(1, self.width() - (view.verticalScrollBar().width() if view.verticalScrollBar().isVisible() else 0)))
        view.setUniformItemSizes(False)
        view.window().setWindowOpacity(1.0)
        view.setAttribute(Qt.WA_TranslucentBackground, False)
        view.viewport().setAttribute(Qt.WA_TranslucentBackground, False)
        view.setUpdatesEnabled(False)
        view.viewport().setUpdatesEnabled(False)
        self._popup_open = True
        super().showPopup()
        view.setFixedWidth(self.width())
        view.viewport().setFixedWidth(max(1, self.width() - (view.verticalScrollBar().width() if view.verticalScrollBar().isVisible() else 0)))
        view.setUniformItemSizes(False)
        view.updateGeometries()
        view.doItemsLayout()
        current = self.model().index(self.currentIndex(), 0)
        if current.isValid():
            view.setCurrentIndex(current)
        view.setUpdatesEnabled(True)
        view.viewport().setUpdatesEnabled(True)
        view.update()
        view.viewport().update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.view().setFixedWidth(self.width())


    def hidePopup(self):
        super().hidePopup()
        self._popup_open = False
        if self._popup_opened_by_mouse:
            QTimer.singleShot(0, self.clearFocus)
        self._popup_opened_by_mouse = False

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        if key in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            if not self._popup_open:
                self._popup_opened_by_mouse = False
                self.showPopup()
                event.accept()
                return
        if key == Qt.Key_Escape:
            if self._popup_open:
                self.hidePopup()
            self.clearFocus()
            event.accept()
            return
        super().keyPressEvent(event)

    def eventFilter(self, watched, event):
        if watched is self.view().viewport() and event.type() == QEvent.MouseButtonPress:
            if event.button() == Qt.LeftButton:
                index = self.view().indexAt(event.position().toPoint())
                if index.isValid():
                    self.view().setCurrentIndex(index)
                    self.setCurrentIndex(index.row())
                    self.hidePopup()
                    self.clearFocus()
                event.accept()
                return True
        if watched is self.view().viewport() and event.type() == QEvent.MouseButtonRelease:
            if event.button() == Qt.LeftButton:
                event.accept()
                return True
        if watched is self.view().viewport() and event.type() in (QEvent.MouseMove, QEvent.Leave, QEvent.Enter):
            self.view().viewport().update()
            return False
        if watched is self.view().viewport() and event.type() == QEvent.Wheel:
            QTimer.singleShot(0, self._refresh_popup_hover_under_cursor)
            return False
        if watched is self.view() and event.type() in (QEvent.MouseMove, QEvent.Leave, QEvent.Enter):
            self.view().viewport().update()
            return False
        if watched is self.view() and event.type() == QEvent.Wheel:
            QTimer.singleShot(0, self._refresh_popup_hover_under_cursor)
            return False
        if watched is self.view() and event.type() == QEvent.KeyPress:
            key = event.key()
            if key == Qt.Key_Escape:
                self.hidePopup()
                self.clearFocus()
                event.accept()
                return True
            if key in (Qt.Key_Return, Qt.Key_Enter):
                index = self.view().currentIndex()
                if index.isValid():
                    self.setCurrentIndex(index.row())
                self.hidePopup()
                self.clearFocus()
                event.accept()
                return True
            if key in (Qt.Key_Up, Qt.Key_Down):
                if self.count() > 0:
                    row = self.view().currentIndex().row()
                    if row < 0:
                        row = self.currentIndex()
                    row += -1 if key == Qt.Key_Up else 1
                    row = max(0, min(self.count() - 1, row))
                    self.view().setCurrentIndex(self.model().index(row, 0))
                event.accept()
                return True
        return super().eventFilter(watched, event)