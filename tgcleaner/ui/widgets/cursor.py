from PySide6.QtCore import QEvent, QObject, QPointF, Qt, QTimer
from PySide6.QtGui import QCursor, QMouseEvent
from PySide6.QtWidgets import QApplication


class _InputCursorOverride(QObject):
    def __init__(self):
        super().__init__()
        self._active = False
        self._widget = None

    def activate(self, widget, shape):
        app = QApplication.instance()
        if app is None:
            return
        self._widget = widget
        cursor = QCursor(shape)
        if self._active:
            QApplication.changeOverrideCursor(cursor)
        else:
            QApplication.setOverrideCursor(cursor)
            app.installEventFilter(self)
            self._active = True

    def restore(self):
        if not self._active:
            return
        app = QApplication.instance()
        if app is not None:
            app.removeEventFilter(self)
        QApplication.restoreOverrideCursor()
        self._active = False
        self._widget = None

    def _inside_widget(self):
        widget = self._widget
        if widget is None or not widget.isVisible():
            return False
        global_pos = QCursor.pos()
        targets = [widget]
        if hasattr(widget, "viewport"):
            viewport = widget.viewport()
            if viewport is not None:
                targets.append(viewport)
        for target in targets:
            if target is not None and target.isVisible() and target.rect().contains(target.mapFromGlobal(global_pos)):
                return True
        return False

    def _sync(self):
        if not self._inside_widget():
            self.restore()
            return
        widget = self._widget
        shape = Qt.IBeamCursor if widget.isEnabled() and widget.isEnabledTo(widget.window()) else Qt.ArrowCursor
        QApplication.changeOverrideCursor(QCursor(shape))

    def eventFilter(self, obj, event):
        if self._active and event.type() in (
            QEvent.MouseMove,
            QEvent.Enter,
            QEvent.Leave,
            QEvent.Wheel,
            QEvent.MouseButtonPress,
            QEvent.WindowDeactivate,
        ):
            QTimer.singleShot(0, self._sync)
        return False


_input_cursor_override = _InputCursorOverride()


def _cursor_refresh_deferred(widget):
    try:
        return bool(widget.property("_defer_enabled_cursor_refresh")) and widget.isEnabled()
    except Exception:
        return False


def _force_cursor_override_under_mouse(widget):
    if widget is None or not widget.isVisible():
        return
    if _cursor_refresh_deferred(widget):
        return
    global_pos = QCursor.pos()
    targets = [widget]
    if hasattr(widget, "viewport"):
        viewport = widget.viewport()
        if viewport is not None:
            targets.append(viewport)
    inside = False
    for target in targets:
        if target is not None and target.isVisible() and target.rect().contains(target.mapFromGlobal(global_pos)):
            inside = True
            break
    if not inside:
        return
    shape = Qt.IBeamCursor if widget.isEnabled() and widget.isEnabledTo(widget.window()) else Qt.ArrowCursor
    _input_cursor_override.activate(widget, shape)


def _refresh_cursor_under_mouse(widget):
    if widget is None or not widget.isVisible():
        return
    if _cursor_refresh_deferred(widget):
        return
    _force_cursor_override_under_mouse(widget)
    global_pos = QCursor.pos()
    target = QApplication.widgetAt(global_pos)
    if target is None:
        return
    current = target
    inside = False
    while current is not None:
        if current is widget:
            inside = True
            break
        current = current.parentWidget()
    if not inside:
        return
    local_pos = target.mapFromGlobal(global_pos)
    event = QMouseEvent(
        QEvent.MouseMove,
        QPointF(local_pos),
        QPointF(global_pos),
        Qt.NoButton,
        Qt.NoButton,
        QApplication.keyboardModifiers(),
    )
    QApplication.sendEvent(target, event)
    _force_cursor_override_under_mouse(widget)


def refresh_input_cursors_under_mouse(widgets):
    global_pos = QCursor.pos()
    for widget in widgets:
        if widget is None or not widget.isVisible():
            continue
        if _cursor_refresh_deferred(widget):
            continue
        target = widget.viewport() if hasattr(widget, "viewport") else widget
        if target is None or not target.isVisible():
            continue
        local_pos = target.mapFromGlobal(global_pos)
        if not target.rect().contains(local_pos):
            continue
        enabled = widget.isEnabled() and widget.isEnabledTo(widget.window())
        cursor_shape = Qt.IBeamCursor if enabled else Qt.ArrowCursor
        widget.setCursor(cursor_shape)
        target.setCursor(cursor_shape)
        event = QMouseEvent(
            QEvent.MouseMove,
            QPointF(local_pos),
            QPointF(global_pos),
            Qt.NoButton,
            Qt.NoButton,
            QApplication.keyboardModifiers(),
        )
        QApplication.sendEvent(target, event)
        _force_cursor_override_under_mouse(widget)
        break