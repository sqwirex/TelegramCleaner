from PySide6.QtCore import QAbstractListModel, QEvent, QModelIndex, QPoint, QRect, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QRegion
from PySide6.QtWidgets import QAbstractItemView, QFrame, QListView, QStyleOptionViewItem

from tgcleaner.core.i18n import T
from tgcleaner.ui.common import TelegramScrollBar
from .messages import MessageListDelegate


class ResultsListItem:
    def __init__(self):
        self._data = {}
        self._flags = Qt.ItemIsEnabled
        self._size_hint = QSize()
        self._size_hint_width = -1

    def data(self, role):
        if role == Qt.UserRole:
            return self._data
        if role == Qt.SizeHintRole and self._size_hint.isValid():
            return self._size_hint
        if role == Qt.CheckStateRole:
            message = self._data.get("message") if isinstance(self._data, dict) else None
            selected = bool(getattr(message, "selected", self._data.get("selected", True) if isinstance(self._data, dict) else True))
            return Qt.Checked if selected else Qt.Unchecked
        return None

    def setData(self, role, value):
        if role == Qt.UserRole:
            self._data = value
            return
        if role == Qt.CheckStateRole:
            selected = value == Qt.Checked
            if isinstance(self._data, dict):
                self._data["selected"] = selected
                message = self._data.get("message")
                if message is not None:
                    message.selected = selected

    def flags(self):
        return self._flags

    def setFlags(self, flags):
        self._flags = flags

    def sizeHint(self):
        return self._size_hint

    def setSizeHint(self, size, width: int = -1):
        self._size_hint = size
        self._size_hint_width = int(width) if width is not None else -1

    def clearSizeHint(self):
        self._size_hint = QSize()
        self._size_hint_width = -1

    def checkState(self):
        return self.data(Qt.CheckStateRole)


class ResultsListModel(QAbstractListModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.items = []

    def rowCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return len(self.items)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = index.row()
        if row < 0 or row >= len(self.items):
            return None
        item = self.items[row]
        if role == Qt.SizeHintRole:
            parent = self.parent()
            width = -1
            if parent is not None and hasattr(parent, "viewport") and parent.viewport() is not None:
                width = parent.viewport().width()
            if item._size_hint.isValid():
                if item._size_hint_width < 0 or item._size_hint_width == width or bool(getattr(parent, "_keep_stale_size_hints", False)):
                    return item._size_hint
            return None
        if role in (Qt.UserRole, Qt.CheckStateRole):
            return item.data(role)
        return None

    def setData(self, index, value, role=Qt.EditRole):
        if not index.isValid():
            return False
        row = index.row()
        if row < 0 or row >= len(self.items):
            return False
        self.items[row].setData(role, value)
        self.dataChanged.emit(index, index, [role])
        return True

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags
        row = index.row()
        if row < 0 or row >= len(self.items):
            return Qt.NoItemFlags
        return self.items[row].flags()

    def clear(self):
        if not self.items:
            return
        self.beginResetModel()
        self.items.clear()
        self.endResetModel()

    def add_item(self, item):
        self.add_items([item])

    def add_items(self, items):
        if not items:
            return
        first = len(self.items)
        last = first + len(items) - 1
        self.beginInsertRows(QModelIndex(), first, last)
        self.items.extend(items)
        self.endInsertRows()

    def add_payloads(self, payloads):
        if not payloads:
            return
        items = []
        for payload in payloads:
            item = ResultsListItem()
            item.setData(Qt.UserRole, payload)
            flags = Qt.ItemIsEnabled
            if isinstance(payload, dict) and payload.get("kind") == "message":
                flags |= Qt.ItemIsSelectable
                message = payload.get("message")
                if message is not None:
                    payload["selected"] = bool(getattr(message, "selected", True))
            item.setFlags(flags)
            items.append(item)
        self.add_items(items)

    def insert_item(self, row, item):
        row = max(0, min(row, len(self.items)))
        self.beginInsertRows(QModelIndex(), row, row)
        self.items.insert(row, item)
        self.endInsertRows()

    def take_item(self, row):
        if row < 0 or row >= len(self.items):
            return None
        self.beginRemoveRows(QModelIndex(), row, row)
        item = self.items.pop(row)
        self.endRemoveRows()
        return item

    def item(self, row):
        if row < 0 or row >= len(self.items):
            return None
        return self.items[row]

    def row_of(self, item):
        try:
            return self.items.index(item)
        except ValueError:
            return -1


class ResultsListWidget(QListView):
    itemChanged = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._radius = 13
        self._scroll_locked = False
        self._keyboard_anchor_row = None
        self._layout_refresh_scheduled = False
        self._last_layout_width = -1
        self._last_mask_size = QSize()
        self._visible_layout_refresh_timer = QTimer(self)
        self._visible_layout_refresh_timer.setSingleShot(True)
        self._visible_layout_refresh_timer.timeout.connect(self._run_visible_width_layout_refresh)
        self._resize_layout_refresh_timer = QTimer(self)
        self._resize_layout_refresh_timer.setSingleShot(True)
        self._resize_layout_refresh_timer.timeout.connect(self._run_width_layout_refresh)
        self._fullscreen_resize_overlay_timer = QTimer(self)
        self._fullscreen_resize_overlay_timer.setSingleShot(True)
        self._fullscreen_resize_overlay_timer.timeout.connect(self._show_delayed_fullscreen_resize_overlay)
        self._fullscreen_resize_transition_timer = QTimer(self)
        self._fullscreen_resize_transition_timer.setSingleShot(True)
        self._fullscreen_resize_transition_timer.timeout.connect(self._finish_fullscreen_resize_transition)
        self._fullscreen_resize_overlay_suppression_timer = QTimer(self)
        self._fullscreen_resize_overlay_suppression_timer.setSingleShot(True)
        self._fullscreen_resize_overlay_suppression_timer.timeout.connect(self._finish_fullscreen_resize_overlay_suppression)
        self._controls_resize_overlay_timer = QTimer(self)
        self._controls_resize_overlay_timer.setSingleShot(True)
        self._controls_resize_overlay_timer.timeout.connect(self.finish_controls_resize_transition)
        self._controls_resize_restore_timer = QTimer(self)
        self._controls_resize_restore_timer.setSingleShot(True)
        self._controls_resize_restore_timer.timeout.connect(self._finish_controls_resize_restore)
        self._resize_overlay_safety_timer = QTimer(self)
        self._resize_overlay_safety_timer.setSingleShot(True)
        self._resize_overlay_safety_timer.timeout.connect(self._finish_resize_overlay_safety)
        self._resize_scrollbar_restore_timer = QTimer(self)
        self._resize_scrollbar_restore_timer.setSingleShot(True)
        self._resize_scrollbar_restore_timer.timeout.connect(self._finish_resize_overlay_scrollbar_restore)
        self._mask_refresh_timer = QTimer(self)
        self._mask_refresh_timer.setSingleShot(True)
        self._mask_refresh_timer.timeout.connect(self._apply_viewport_mask)
        self._last_visible_layout_refresh_width = -1
        self._last_visible_layout_refresh_rows = (-1, -1)
        self._keep_stale_size_hints = False
        self._resize_updates_locked = False
        self._resize_overlay_active = False
        self._resize_overlay_forced = False
        self._fullscreen_resize_overlay_pending = False
        self._fullscreen_resize_transition_active = False
        self._fullscreen_resize_overlay_suppressed = False
        self._controls_resize_overlay_active = False
        self._controls_resize_restore_pending = False
        self._last_window_fullscreen = False
        self._last_resize_window_size = QSize()
        self._last_resize_viewport_size = QSize()
        self._message_item_count_cache = -1
        self._lightweight_resize_refresh = False
        self._results_model = ResultsListModel(self)
        self.setModel(self._results_model)
        self.setFrameShape(QFrame.NoFrame)
        self.setFocusPolicy(Qt.NoFocus)
        self.viewport().setFocusPolicy(Qt.NoFocus)
        self.setSpacing(2)
        self.setUniformItemSizes(False)
        self.setLayoutMode(QListView.Batched)
        self.setBatchSize(24)
        self.setResizeMode(QListView.Fixed)
        self.setAlternatingRowColors(False)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBar(TelegramScrollBar(Qt.Vertical, self))
        self.setHorizontalScrollBar(TelegramScrollBar(Qt.Horizontal, self))
        self.verticalScrollBar().setSingleStep(28)
        self.setItemDelegate(MessageListDelegate(self))
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setViewportMargins(0, 0, 0, 0)
        self.viewport().setAttribute(Qt.WA_StyledBackground, True)
        self.viewport().setAutoFillBackground(False)
        self.viewport().setStyleSheet("background: transparent; border: 0;")
        self.viewport().installEventFilter(self)
        self.setStyleSheet("background: transparent; border: 0;")

    def count(self):
        return self._results_model.rowCount()

    def item(self, row):
        return self._results_model.item(row)

    def addItem(self, item):
        self._invalidate_message_item_count_cache()
        self._results_model.add_item(item)

    def addPayloads(self, payloads):
        self._invalidate_message_item_count_cache()
        self._results_model.add_payloads(payloads)

    def insertItem(self, row, item):
        self._invalidate_message_item_count_cache()
        self._results_model.insert_item(row, item)

    def takeItem(self, row):
        self._invalidate_message_item_count_cache()
        return self._results_model.take_item(row)

    def clear(self):
        self._keep_stale_size_hints = False
        self._resize_updates_locked = False
        self._cancel_fullscreen_resize_overlay_delay()
        self._set_resize_overlay_active(False)
        if self.viewport() is not None and not self.viewport().updatesEnabled():
            self.viewport().setUpdatesEnabled(True)
        self._invalidate_message_item_count_cache()
        self._results_model.clear()
        self._keyboard_anchor_row = None
        self.setCurrentIndex(QModelIndex())

    def itemAt(self, position):
        index = self.indexAt(position)
        if not index.isValid():
            return None
        return self.item(index.row())

    def visualItemRect(self, item):
        row = self._results_model.row_of(item)
        if row < 0:
            return QRect()
        return self.visualRect(self._results_model.index(row, 0))

    def scrollToItem(self, item, hint=QAbstractItemView.EnsureVisible):
        row = self._results_model.row_of(item)
        if row < 0:
            return
        self.scrollTo(self._results_model.index(row, 0), hint)

    def currentRow(self):
        index = self.currentIndex()
        return index.row() if index.isValid() else -1

    def setCurrentRow(self, row):
        if row < 0 or row >= self.count():
            self.setCurrentIndex(QModelIndex())
            return
        self.setCurrentIndex(self._results_model.index(row, 0))

    def schedule_deferred_layout_refresh(self):
        if getattr(self, "_layout_refresh_scheduled", False):
            return
        self._layout_refresh_scheduled = True
        QTimer.singleShot(0, self._run_deferred_layout_refresh)
        QTimer.singleShot(16, self._run_deferred_layout_refresh)

    def _run_deferred_layout_refresh(self):
        if not getattr(self, "_layout_refresh_scheduled", False):
            return
        self._layout_refresh_scheduled = False
        self._invalidate_message_layout_cache(False, False)

    def _update_focus_policy(self):
        self.setFocusPolicy(Qt.TabFocus if self._message_rows() else Qt.NoFocus)

    def _message_rows(self):
        rows = []
        for row in range(self.count()):
            item = self.item(row)
            if item is None:
                continue
            payload = item.data(Qt.UserRole) or {}
            if payload.get("kind") == "message":
                rows.append(row)
        return rows

    def _message_row_position(self, row: int, rows: list[int] | None = None):
        rows = self._message_rows() if rows is None else rows
        if not rows:
            return -1
        if row in rows:
            return rows.index(row)
        return 0

    def _first_message_row(self):
        rows = self._message_rows()
        return rows[0] if rows else -1

    def _current_message_row(self):
        rows = self._message_rows()
        if not rows:
            return -1
        current = self.currentRow()
        return current if current in rows else rows[0]

    def _set_current_message_row(self, row: int):
        item = self.item(row)
        if item is None:
            return
        self.setCurrentRow(row)
        self.scrollToItem(item, QAbstractItemView.EnsureVisible)
        self.viewport().update()

    def move_current_message(self, step: int, extend: bool = False):
        rows = self._message_rows()
        if not rows:
            return False
        current_row = self._current_message_row()
        current_index = self._message_row_position(current_row, rows)
        target_index = max(0, min(len(rows) - 1, current_index + step))
        target_row = rows[target_index]
        self._keyboard_anchor_row = target_row
        self._set_current_message_row(target_row)
        return True

    def _set_message_selected(self, row: int, selected: bool):
        item = self.item(row)
        if item is None:
            return
        payload = item.data(Qt.UserRole) or {}
        if payload.get("kind") != "message":
            return
        message = payload.get("message")
        payload["selected"] = selected
        if message is not None:
            message.selected = selected
        self.viewport().update(self.visualItemRect(item).adjusted(-52, -28, 52, 28))

    def _set_all_messages_selected(self, selected: bool):
        for row in self._message_rows():
            self._set_message_selected(row, selected)
        self.viewport().update()
        self._refresh_delete_button()

    def _refresh_delete_button(self):
        window = self.window()
        if hasattr(window, "delete_button") and hasattr(window, "found_messages"):
            loading = window._is_search_loading() if hasattr(window, "_is_search_loading") else False
            deleting = window._is_delete_loading() if hasattr(window, "_is_delete_loading") else False
            window.delete_button.setVisible(True)
            window.delete_button.setEnabled(bool(window.found_messages) and not loading and not deleting)

    def set_scroll_locked(self, locked: bool):
        self._scroll_locked = locked
        if locked:
            self.verticalScrollBar().setValue(0)

    def wheelEvent(self, event):
        if self._scroll_locked or self.verticalScrollBar().maximum() <= 0:
            event.accept()
            return
        super().wheelEvent(event)

    def _message_checkbox_at(self, position):
        item = self.itemAt(position.toPoint())
        if item is None:
            return None, None, None
        payload = item.data(Qt.UserRole) or {}
        if payload.get("kind") != "message":
            return None, None, None
        delegate = self.itemDelegate()
        message = payload.get("message")
        if not isinstance(delegate, MessageListDelegate) or message is None:
            return None, None, None
        option = QStyleOptionViewItem()
        option.initFrom(self)
        option.rect = self.visualItemRect(item)
        if delegate._message_simple_render_enabled(payload, option):
            row_rect, header_rect, body_rect, check_rect = delegate._simple_message_rects(option, message)
            if check_rect.adjusted(-10, -10, 10, 10).contains(position):
                return item, payload, message
            return None, None, None
        header_rect, bubble_rect, check_rect = delegate._message_rects(option, message)
        message_hit_rect = header_rect.united(bubble_rect).adjusted(-18, -14, 18, 14)
        check_hit_rect = check_rect.adjusted(-24, -26, 24, 26)
        if message.is_outgoing:
            check_hit_rect = check_hit_rect.adjusted(-6, 0, 18, 0)
        else:
            check_hit_rect = check_hit_rect.adjusted(-18, 0, 6, 0)
        if check_hit_rect.contains(position) or message_hit_rect.contains(position):
            return item, payload, message
        return None, None, None

    def _toggle_message_checkbox(self, item, payload, message):
        export_button = None
        window = self.window()
        if hasattr(window, "export_results_button"):
            export_button = window.export_results_button
        export_enabled = export_button.isEnabled() if export_button is not None else None
        current_state = bool(getattr(message, "selected", payload.get("selected", True)))
        new_state = not current_state
        payload["selected"] = new_state
        message.selected = new_state
        if export_button is not None and export_enabled is not None:
            export_button.setEnabled(export_enabled)
        self._refresh_delete_button()
        self.viewport().update(self.visualItemRect(item).adjusted(-52, -28, 52, 28))

    def _drop_mouse_focus(self):
        changed = self.hasFocus() or self.currentIndex().isValid()
        if self.hasFocus():
            self.clearFocus()
        if self.currentIndex().isValid():
            self.setCurrentIndex(QModelIndex())
        if changed:
            window = self.window()
            if hasattr(window, "central_root_widget"):
                window.central_root_widget.setFocus(Qt.OtherFocusReason)
            else:
                window.setFocus(Qt.OtherFocusReason)
            self.viewport().update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            window = self.window()
            if getattr(window, "final_results_rendering", False):
                event.accept()
                return
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            window = self.window()
            if getattr(window, "final_results_rendering", False):
                event.accept()
                return
            item, payload, message = self._message_checkbox_at(event.position())
            if item is not None:
                self._toggle_message_checkbox(item, payload, message)
            self._drop_mouse_focus()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def focusInEvent(self, event):
        if not self._message_rows():
            self.clearFocus()
            event.ignore()
            return
        super().focusInEvent(event)
        if self.currentRow() < 0:
            first_row = self._first_message_row()
            if first_row >= 0:
                self._set_current_message_row(first_row)
                self._keyboard_anchor_row = first_row

    def keyPressEvent(self, event):
        rows = self._message_rows()
        if not rows:
            super().keyPressEvent(event)
            return
        key = event.key()
        modifiers = event.modifiers()
        current_row = self._current_message_row()
        if key in (Qt.Key_Down, Qt.Key_Up):
            step = 1 if key == Qt.Key_Down else -1
            self.move_current_message(step, False)
            event.accept()
            return
        if key in (Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter):
            item = self.item(current_row)
            if item is not None:
                payload = item.data(Qt.UserRole) or {}
                message = payload.get("message")
                if payload.get("kind") == "message" and message is not None:
                    self._toggle_message_checkbox(item, payload, message)
                    self._keyboard_anchor_row = current_row
                    event.accept()
                    return
        if key == Qt.Key_A and modifiers & Qt.ControlModifier:
            self._set_all_messages_selected(True)
            self._drop_mouse_focus()
            event.accept()
            return
        if key == Qt.Key_D and modifiers & Qt.ControlModifier:
            self._set_all_messages_selected(False)
            self._drop_mouse_focus()
            event.accept()
            return
        if key == Qt.Key_Escape:
            self.clearFocus()
            event.accept()
            return
        if key == Qt.Key_Delete:
            window = self.window()
            if hasattr(window, "on_delete"):
                window.on_delete()
                event.accept()
                return
        super().keyPressEvent(event)

    def paintEvent(self, event):
        if self._resize_overlay_active and self._can_show_resize_overlay(self._resize_overlay_forced):
            painter = QPainter(self.viewport())
            painter.fillRect(self.viewport().rect(), QColor("#07131E"))
            painter.setRenderHint(QPainter.TextAntialiasing)
            font = QFont(self.font())
            font.setBold(False)
            painter.setFont(font)
            painter.setPen(QColor("#AFC2D3"))
            painter.drawText(self.viewport().rect().adjusted(24, 0, -24, 0), Qt.AlignCenter | Qt.TextWordWrap, T.RESIZING_RESULTS)
            painter.end()
            return
        super().paintEvent(event)

    def _results_rendering_in_progress(self):
        window = self.window()
        if window is None:
            return False
        if bool(getattr(window, "final_results_rendering", False)):
            return True
        if bool(getattr(window, "render_controls_locked", False)):
            return True
        return False

    def _window_expanded_state(self):
        window = self.window()
        if window is None:
            return False
        state = window.windowState()
        return bool(state & Qt.WindowFullScreen) or bool(state & Qt.WindowMaximized)

    def _can_show_resize_overlay(self, force: bool = False):
        if self._results_rendering_in_progress():
            return False
        count = self._message_item_count()
        if count <= 0:
            return False
        if force:
            return True
        if self._fullscreen_resize_overlay_suppressed:
            return False
        if self._fullscreen_resize_transition_active:
            return count > 180
        return True

    def _set_resize_overlay_scrollbar_hidden(self, hidden: bool):
        bar = self.verticalScrollBar()
        if bar is None:
            return
        hidden = bool(hidden)
        if bool(bar.property("resizeOverlayHidden")) == hidden:
            return
        bar.setProperty("resizeOverlayHidden", hidden)
        bar.update()
        if bar.isVisible():
            bar.repaint()

    def _set_resize_overlay_active(self, active: bool, force: bool = False):
        force = bool(force)
        active = bool(active and self._can_show_resize_overlay(force))
        old_active = self._resize_overlay_active
        old_force = self._resize_overlay_forced
        self._resize_overlay_active = active
        self._resize_overlay_forced = force if active else False
        if active:
            self._resize_scrollbar_restore_timer.stop()
            self._set_resize_overlay_scrollbar_hidden(True)
            self._resize_overlay_safety_timer.start(1800)
        else:
            self._resize_overlay_safety_timer.stop()
            if old_active:
                self._resize_scrollbar_restore_timer.start(32)
            elif not self._resize_scrollbar_restore_timer.isActive():
                self._set_resize_overlay_scrollbar_hidden(False)
        if old_active == self._resize_overlay_active and old_force == self._resize_overlay_forced:
            return
        viewport = self.viewport()
        if viewport is not None:
            viewport.update()

    def _finish_resize_overlay_scrollbar_restore(self):
        if self._resize_overlay_active:
            return
        self._set_resize_overlay_scrollbar_hidden(False)
        viewport = self.viewport()
        if viewport is not None:
            viewport.update()

    def _restore_results_after_resize_overlay(self, refresh: bool = True):
        self._keep_stale_size_hints = False
        self._resize_updates_locked = False
        self._set_resize_overlay_active(False)
        self._last_visible_layout_refresh_width = -1
        self._last_visible_layout_refresh_rows = (-1, -1)
        if refresh and self._has_message_items():
            self._resize_layout_refresh_timer.stop()
            self._run_width_layout_refresh()
        else:
            viewport = self.viewport()
            if viewport is not None:
                viewport.update()

    def _finish_resize_overlay_safety(self):
        self._controls_resize_overlay_active = False
        self._controls_resize_restore_pending = False
        self._controls_resize_restore_timer.stop()
        self._fullscreen_resize_transition_active = False
        self._cancel_fullscreen_resize_overlay_delay()
        self._restore_results_after_resize_overlay()

    def _cancel_fullscreen_resize_overlay_delay(self):
        self._fullscreen_resize_overlay_pending = False
        self._fullscreen_resize_overlay_timer.stop()

    def _schedule_fullscreen_resize_overlay_delay(self):
        if not self._can_show_resize_overlay():
            self._cancel_fullscreen_resize_overlay_delay()
            return
        self._fullscreen_resize_overlay_pending = True
        if not self._resize_overlay_active and not self._fullscreen_resize_overlay_timer.isActive():
            self._fullscreen_resize_overlay_timer.start(220)

    def _show_delayed_fullscreen_resize_overlay(self):
        if not self._fullscreen_resize_overlay_pending:
            return
        if not self._resize_layout_refresh_timer.isActive():
            self._fullscreen_resize_overlay_pending = False
            return
        if not self._fullscreen_resize_transition_active:
            self._fullscreen_resize_overlay_pending = False
            return
        if not self._can_show_resize_overlay():
            self._fullscreen_resize_overlay_pending = False
            return
        self._set_resize_overlay_active(True)
        viewport = self.viewport()
        if viewport is not None:
            viewport.update()

    def _finish_fullscreen_resize_transition(self):
        self._fullscreen_resize_transition_active = False
        self._cancel_fullscreen_resize_overlay_delay()
        if not self._controls_resize_overlay_active:
            self._restore_results_after_resize_overlay()

    def _finish_fullscreen_resize_overlay_suppression(self):
        self._fullscreen_resize_overlay_suppressed = False
        self._restore_results_after_resize_overlay(False)

    def begin_window_state_resize_transition(self):
        self._last_window_fullscreen = self._window_expanded_state()
        self._fullscreen_resize_transition_active = True
        self._fullscreen_resize_overlay_suppressed = self._message_item_count() <= 180
        self._fullscreen_resize_transition_timer.start(650)
        self._fullscreen_resize_overlay_suppression_timer.start(1300 if self._fullscreen_resize_overlay_suppressed else 700)
        self._cancel_fullscreen_resize_overlay_delay()
        if self._fullscreen_resize_overlay_suppressed:
            self._keep_stale_size_hints = False
            self._set_resize_overlay_active(False)

    def begin_fullscreen_resize_transition(self):
        self.begin_window_state_resize_transition()

    def begin_controls_resize_transition(self, duration_ms: int = 320):
        if not self._has_message_items():
            return
        self._controls_resize_overlay_active = True
        self._controls_resize_restore_pending = False
        self._controls_resize_restore_timer.stop()
        self._cancel_fullscreen_resize_overlay_delay()
        self._set_resize_overlay_active(True, True)
        self._keep_stale_size_hints = True
        self._last_visible_layout_refresh_width = -1
        self._last_visible_layout_refresh_rows = (-1, -1)
        self._controls_resize_overlay_timer.start(max(120, int(duration_ms)))
        viewport = self.viewport()
        if viewport is not None:
            viewport.update()

    def finish_controls_resize_transition(self):
        self._controls_resize_overlay_timer.stop()
        if not self._controls_resize_overlay_active:
            return
        self._controls_resize_restore_pending = True
        self._controls_resize_restore_timer.start(120)

    def _finish_controls_resize_restore(self):
        self._controls_resize_restore_pending = False
        self._controls_resize_overlay_active = False
        self._restore_results_after_resize_overlay()

    def _update_fullscreen_resize_transition(self):
        current = self._window_expanded_state()
        if self._last_window_fullscreen is None:
            self._last_window_fullscreen = current
            return False
        if current != self._last_window_fullscreen:
            self._last_window_fullscreen = current
            self.begin_fullscreen_resize_transition()
            return True
        return self._fullscreen_resize_transition_active

    def _window_size_changed(self):
        window = self.window()
        if window is None:
            return False
        size = QSize(window.size())
        if size.width() <= 0 or size.height() <= 0:
            return False
        if self._last_resize_window_size.width() <= 0 or self._last_resize_window_size.height() <= 0:
            self._last_resize_window_size = QSize(size)
            return False
        if size == self._last_resize_window_size:
            return False
        self._last_resize_window_size = QSize(size)
        return True

    def _viewport_resize_state(self):
        viewport = self.viewport()
        if viewport is None:
            return False, False
        size = QSize(viewport.size())
        if size.width() <= 0 or size.height() <= 0:
            return False, False
        if self._last_resize_viewport_size.width() <= 0 or self._last_resize_viewport_size.height() <= 0:
            self._last_resize_viewport_size = QSize(size)
            return False, False
        width_changed = size.width() != self._last_resize_viewport_size.width()
        height_changed = size.height() != self._last_resize_viewport_size.height()
        self._last_resize_viewport_size = QSize(size)
        return width_changed, height_changed

    def _should_show_resize_overlay_for_view_change(self, fullscreen_transition: bool = False):
        window_changed = self._window_size_changed()
        viewport_width_changed, viewport_height_changed = self._viewport_resize_state()
        view_changed = window_changed or viewport_width_changed or viewport_height_changed
        if not view_changed:
            return False, False
        if not self._has_message_items() or self._results_rendering_in_progress():
            return False, False
        if self._controls_resize_overlay_active:
            return True, True
        if fullscreen_transition or self._fullscreen_resize_transition_active or self._fullscreen_resize_overlay_suppressed:
            return self._can_show_resize_overlay(False), False
        return True, False

    def _invalidate_message_item_count_cache(self):
        self._message_item_count_cache = -1

    def _message_item_count(self):
        if self._message_item_count_cache >= 0:
            return self._message_item_count_cache
        total = 0
        for row in range(self.count()):
            item = self.item(row)
            if item is None:
                continue
            payload = item.data(Qt.UserRole) or {}
            if payload.get("kind") == "message":
                total += 1
        self._message_item_count_cache = total
        return total

    def _large_resize_result_set(self):
        return self._message_item_count() > 1000

    def _resize_refresh_delay(self, show_overlay: bool):
        if not show_overlay:
            return 1
        if self._message_item_count() > 5000:
            return 320
        return 180

    def _has_message_items(self):
        return self._message_item_count() > 0

    def _apply_viewport_mask(self):
        viewport = self.viewport()
        if viewport.width() <= 0 or viewport.height() <= 0:
            return
        size = viewport.size()
        if size == self._last_mask_size:
            return
        self._last_mask_size = QSize(size)
        path = QPainterPath()
        path.addRoundedRect(QRectF(viewport.rect()).adjusted(1.0, 1.0, -1.0, -1.0), self._radius, self._radius)
        viewport.setMask(QRegion(path.toFillPolygon().toPolygon()))

    def _visible_row_range(self, margin: int = 4):
        count = self.count()
        viewport = self.viewport()
        if count <= 0 or viewport is None or viewport.height() <= 0:
            return None
        height = viewport.height()
        probe_x = min(max(4, viewport.width() // 2), max(4, viewport.width() - 4))
        first = -1
        last = -1
        step = max(1, min(32, max(1, height // 24)))
        for y in range(0, height + 1, step):
            index = self.indexAt(QPoint(probe_x, y))
            if index.isValid():
                first = index.row()
                break
        for y in range(height - 1, -1, -step):
            index = self.indexAt(QPoint(probe_x, y))
            if index.isValid():
                last = index.row()
                break
        if first < 0 or last < 0:
            index = self.indexAt(QPoint(probe_x, max(0, height // 2)))
            if index.isValid():
                first = last = index.row()
        if first < 0 or last < 0:
            top_value = self.verticalScrollBar().value() if self.verticalScrollBar() is not None else 0
            estimate = max(0, min(count - 1, top_value // 76))
            first = estimate
            last = min(count - 1, estimate + 40)
        first = max(0, first - margin)
        last = min(count - 1, last + margin)
        if first > last:
            return None
        return first, last

    def _clear_message_layout_cache_rows(self, first: int, last: int):
        for row in range(max(0, first), min(self.count() - 1, last) + 1):
            item = self.item(row)
            if item is None:
                continue
            item.clearSizeHint()
            payload = item.data(Qt.UserRole) or {}
            if payload.get("kind") != "message":
                continue
            message = payload.get("message")
            if message is None:
                continue
            for attr in ("_ui_bubble_width_cache", "_ui_message_rects_cache", "_ui_size_hint_cache", "_ui_simple_size_hint_cache"):
                if hasattr(message, attr):
                    try:
                        delattr(message, attr)
                    except Exception:
                        pass

    def _emit_size_hint_changed(self, first: int, last: int):
        if self.count() <= 0:
            return
        first = max(0, first)
        last = min(self.count() - 1, last)
        if first > last:
            return
        top = self._results_model.index(first, 0)
        bottom = self._results_model.index(last, 0)
        self._results_model.dataChanged.emit(top, bottom, [Qt.SizeHintRole])

    def _make_delegate_option(self, row: int, width: int):
        option = QStyleOptionViewItem()
        option.initFrom(self)
        rect = self.visualRect(self._results_model.index(row, 0))
        height = rect.height() if rect.isValid() and rect.height() > 0 else 80
        option.rect = QRect(0, 0, max(260, width), height)
        return option

    def _update_size_hints_for_rows(self, first: int, last: int, width: int):
        delegate = self.itemDelegate()
        if not isinstance(delegate, MessageListDelegate) or width <= 0:
            return False
        changed = False
        first = max(0, first)
        last = min(self.count() - 1, last)
        for row in range(first, last + 1):
            item = self.item(row)
            if item is None:
                continue
            payload = item.data(Qt.UserRole) or {}
            if payload.get("kind") != "message":
                continue
            message = payload.get("message")
            if message is None:
                continue
            option = self._make_delegate_option(row, width)
            size = delegate.sizeHint(option, self._results_model.index(row, 0))
            if item._size_hint_width != width or item._size_hint != size:
                item.setSizeHint(size, width)
                changed = True
        return changed

    def _refresh_visible_message_layout(self, force: bool = False, margin: int = 4):
        row_range = self._visible_row_range(margin)
        if row_range is None:
            return
        first, last = row_range
        width = self.viewport().width() if self.viewport() is not None else -1
        if not force and width == self._last_visible_layout_refresh_width and (first, last) == self._last_visible_layout_refresh_rows:
            return
        self._last_visible_layout_refresh_width = width
        self._last_visible_layout_refresh_rows = (first, last)
        changed = self._update_size_hints_for_rows(first, last, width)
        if changed:
            self._emit_size_hint_changed(first, last)
            if not self._keep_stale_size_hints and not self._lightweight_resize_refresh:
                self.doItemsLayout()
                self.updateGeometries()
        self.viewport().update()

    def _schedule_width_layout_refresh(self, show_overlay: bool = True, delay_overlay: bool = False, force_overlay: bool = False):
        if not self._has_message_items():
            self._cancel_fullscreen_resize_overlay_delay()
            self._set_resize_overlay_active(False)
            self._keep_stale_size_hints = False
            if self.count() <= 1:
                self._invalidate_message_layout_cache(False, False)
            return
        show_overlay = bool(show_overlay and self._can_show_resize_overlay(force_overlay))
        delay_overlay = False
        self._resize_updates_locked = show_overlay
        self._keep_stale_size_hints = show_overlay
        if show_overlay:
            if delay_overlay:
                self._schedule_fullscreen_resize_overlay_delay()
            else:
                self._cancel_fullscreen_resize_overlay_delay()
                self._set_resize_overlay_active(True, force_overlay)
        else:
            self._cancel_fullscreen_resize_overlay_delay()
            self._set_resize_overlay_active(False)
        self._last_visible_layout_refresh_width = -1
        self._last_visible_layout_refresh_rows = (-1, -1)
        self._visible_layout_refresh_timer.stop()
        viewport = self.viewport()
        if viewport is not None and (not delay_overlay or self._resize_overlay_active):
            viewport.update()
        self._resize_layout_refresh_timer.start(self._resize_refresh_delay(show_overlay))

    def _run_visible_width_layout_refresh(self):
        self._refresh_visible_message_layout(True, 3)

    def _run_width_layout_refresh(self):
        if self._resize_overlay_active and (self._controls_resize_overlay_active or self._fullscreen_resize_transition_active):
            self._resize_layout_refresh_timer.start(120)
            return
        viewport = self.viewport()
        large_refresh = self._large_resize_result_set()
        self._lightweight_resize_refresh = large_refresh
        try:
            self._cancel_fullscreen_resize_overlay_delay()
            if not self._controls_resize_overlay_active:
                self._keep_stale_size_hints = large_refresh
            self._last_visible_layout_refresh_width = -1
            self._last_visible_layout_refresh_rows = (-1, -1)
            row_range = self._visible_row_range(8)
            if row_range is not None:
                self._clear_message_layout_cache_rows(row_range[0], row_range[1])
            self._refresh_visible_message_layout(True, 8)
            if large_refresh:
                self.updateGeometries()
            else:
                self.doItemsLayout()
                self.updateGeometries()
        finally:
            self._lightweight_resize_refresh = False
            self._resize_updates_locked = False
            if not self._controls_resize_overlay_active and not self._fullscreen_resize_transition_active:
                self._keep_stale_size_hints = False
                self._set_resize_overlay_active(False)
            if viewport is not None:
                viewport.update()

    def scrollContentsBy(self, dx, dy):
        super().scrollContentsBy(dx, dy)
        if dy and not self._visible_layout_refresh_timer.isActive() and not self._resize_updates_locked:
            self._visible_layout_refresh_timer.start(12)

    def eventFilter(self, watched, event):
        if watched is self.viewport() and event.type() in (QEvent.Resize, QEvent.Show):
            fullscreen_transition = self._update_fullscreen_resize_transition() if event.type() == QEvent.Resize else False
            if event.type() == QEvent.Show:
                self._apply_viewport_mask()
            elif not self._mask_refresh_timer.isActive():
                self._mask_refresh_timer.start(60)
            if event.type() == QEvent.Resize:
                if self._controls_resize_restore_pending:
                    self._controls_resize_restore_timer.start(120)
                width = self.viewport().width()
                show_overlay, force_overlay = self._should_show_resize_overlay_for_view_change(fullscreen_transition)
                if width != self._last_layout_width:
                    self._last_layout_width = width
                    if self._resize_overlay_active:
                        self._resize_layout_refresh_timer.start(self._resize_refresh_delay(True))
                    else:
                        self._schedule_width_layout_refresh(show_overlay, fullscreen_transition, force_overlay)
                elif show_overlay:
                    if self._resize_overlay_active:
                        self._resize_layout_refresh_timer.start(self._resize_refresh_delay(True))
                    else:
                        self._schedule_width_layout_refresh(True, fullscreen_transition, force_overlay)
        return super().eventFilter(watched, event)


    def _invalidate_message_layout_cache(self, clear_message_cache: bool = True, schedule_again: bool = True):
        if clear_message_cache:
            delegate = self.itemDelegate()
            for row in range(self.count()):
                item = self.item(row)
                if item is None:
                    continue
                payload = item.data(Qt.UserRole) or {}
                if payload.get("kind") != "message":
                    continue
                message = payload.get("message")
                if message is None:
                    continue
                if isinstance(delegate, MessageListDelegate):
                    delegate.clear_message_cache(message)
                else:
                    for attr in ("_ui_bubble_width_cache", "_ui_message_rects_cache", "_ui_size_hint_cache", "_ui_simple_size_hint_cache"):
                        if hasattr(message, attr):
                            try:
                                delattr(message, attr)
                            except Exception:
                                pass
        if self.count() > 0:
            top = self._results_model.index(0, 0)
            bottom = self._results_model.index(self.count() - 1, 0)
            self._results_model.dataChanged.emit(top, bottom, [Qt.SizeHintRole])
        self.doItemsLayout()
        self.updateGeometries()
        self.viewport().update()
        if schedule_again:
            self.schedule_deferred_layout_refresh()

    def _sync_special_item_height(self):
        if self.count() != 1:
            return
        item = self.item(0)
        if item is None:
            return
        payload = item.data(Qt.UserRole) or {}
        kind = payload.get("kind")
        if kind == "placeholder":
            height = max(120, self.viewport().height())
        elif kind == "notice" and payload.get("center"):
            height = max(180, self.viewport().height() - 12)
        else:
            return
        current = item.sizeHint()
        width = self.viewport().width()
        if current.height() != height or item._size_hint_width != width:
            item.setSizeHint(QSize(current.width(), height), width)
            row = self._results_model.row_of(item)
            if row >= 0:
                index = self._results_model.index(row, 0)
                self._results_model.dataChanged.emit(index, index, [Qt.SizeHintRole])
            self.doItemsLayout()
            self.updateGeometries()
            self._apply_viewport_mask()
            self.viewport().update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        fullscreen_transition = self._update_fullscreen_resize_transition()
        show_overlay, force_overlay = self._should_show_resize_overlay_for_view_change(fullscreen_transition)
        if self._has_message_items():
            width = self.viewport().width() if self.viewport() is not None else -1
            if width != self._last_layout_width:
                self._last_layout_width = width
                self._schedule_width_layout_refresh(show_overlay, fullscreen_transition, force_overlay)
            elif show_overlay:
                self._schedule_width_layout_refresh(True, fullscreen_transition, force_overlay)
            elif self._resize_overlay_active:
                self._resize_layout_refresh_timer.start(self._resize_refresh_delay(True))
        else:
            self._set_resize_overlay_active(False)
            self._keep_stale_size_hints = False
        if not self._mask_refresh_timer.isActive():
            self._mask_refresh_timer.start(60)
        self._sync_special_item_height()

    def showEvent(self, event):
        super().showEvent(event)
        self._apply_viewport_mask()
        self._sync_special_item_height()