import csv
import io
import os
import re
import time
from pathlib import Path
from datetime import datetime

from PySide6.QtCore import QSize, Qt, QTimer

from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QPlainTextEdit,
    QListView,
    QStyleOptionViewItem,
)

from tgcleaner.ui.widgets.results import ResultsListItem


from tgcleaner.core.models import FoundMessage
from tgcleaner.core.parsing import display_sender_name
from tgcleaner.core.i18n import T, translate_content_kind, translate_runtime_text
from tgcleaner.core.config import user_session_dir, users_dir, save_saved_field



class MainWindowResultsMixin:

    HIDDEN_FINAL_RENDER_BATCH_SIZE = 20
    HIDDEN_FINAL_RENDER_BATCH_DELAY_MS = 12
    HIDDEN_FINAL_RENDER_START_DELAY_MS = 80
    HIDDEN_FINAL_RENDER_MIN_BATCH_SIZE = 6
    HIDDEN_FINAL_RENDER_MAX_BATCH_SIZE = 60
    HIDDEN_FINAL_RENDER_MIN_DELAY_MS = 2
    HIDDEN_FINAL_RENDER_MAX_DELAY_MS = 28
    HIDDEN_FINAL_RENDER_TARGET_MS = 9.0
    FILTER_RENDERING_PLACEHOLDER_DELAY_MS = 220
    FILTER_RENDERING_PLACEHOLDER_SKIP_LIMIT = 180
    SIMPLE_RENDER_RECOMMEND_LIMIT = 5000

    def _sender_filter_mode(self) -> str:
        return getattr(self, "result_filter_mode", "sender")


    def _result_filter_key(self, message: FoundMessage) -> tuple[str, str]:
        if self._sender_filter_mode() == "chat":
            label = (getattr(message, "chat_input", "") or T.CONTENT_UNKNOWN_CHAT).strip() or T.CONTENT_UNKNOWN_CHAT
            return f"chat:{label}", label
        if message.is_outgoing:
            return "__me__", T.SENDER_FILTER_YOU
        label = display_sender_name(message) or T.CONTENT_UNKNOWN
        if message.sender_id is not None:
            return f"sender:{message.sender_id}", label
        return f"name:{label}", label


    def _reset_sender_filter(self):
        self.sender_filter_combo.blockSignals(True)
        self.sender_filter_combo.clear()
        self.sender_filter_combo.addItem(T.SENDER_FILTER_ALL, "__all__")
        self.sender_filter_label.setText(T.SENDER_FILTER_GROUPS_LABEL if self._sender_filter_mode() == "chat" else T.SENDER_FILTER_LABEL)
        self.sender_filter_combo.setCurrentIndex(0)
        self.sender_filter_combo.setEnabled(False)
        self.sender_filter_combo.blockSignals(False)




    def _refresh_sender_filter_language_items(self):
        if not hasattr(self, "sender_filter_combo"):
            return
        combo = self.sender_filter_combo
        current_index = combo.currentIndex()
        was_enabled = combo.isEnabled()
        combo.blockSignals(True)
        for index in range(combo.count()):
            data = combo.itemData(index)
            if data == "__all__":
                combo.setItemText(index, T.SENDER_FILTER_ALL)
            elif data == "__me__":
                combo.setItemText(index, T.SENDER_FILTER_YOU)
        if 0 <= current_index < combo.count():
            combo.setCurrentIndex(current_index)
        combo.setEnabled(was_enabled)
        combo.blockSignals(False)

    def _populate_sender_filter(self):
        current_key = self.sender_filter_combo.currentData() if hasattr(self, "sender_filter_combo") else "__all__"
        senders: dict[str, str] = {}
        for message in self.all_found_messages:
            key, label = self._result_filter_key(message)
            senders.setdefault(key, label)
        self.sender_filter_combo.blockSignals(True)
        self.sender_filter_combo.clear()
        self.sender_filter_combo.addItem(T.SENDER_FILTER_ALL, "__all__")
        self.sender_filter_label.setText(T.SENDER_FILTER_GROUPS_LABEL if self._sender_filter_mode() == "chat" else T.SENDER_FILTER_LABEL)
        ordered_items = sorted(senders.items(), key=lambda item: item[1].casefold())
        if self._sender_filter_mode() == "sender" and "__me__" in senders:
            self.sender_filter_combo.addItem(senders["__me__"], "__me__")
            ordered_items = [(key, label) for key, label in ordered_items if key != "__me__"]
        for key, label in ordered_items:
            self.sender_filter_combo.addItem(label, key)
        index = self.sender_filter_combo.findData(current_key)
        self.sender_filter_combo.setCurrentIndex(index if index >= 0 else 0)
        deleting = self._is_delete_loading() if hasattr(self, "_is_delete_loading") else False
        self.sender_filter_combo.setEnabled(bool(self.all_found_messages) and self.sender_filter_combo.count() > 1 and not self._is_search_loading() and not deleting)
        self.sender_filter_combo.blockSignals(False)


    def _filtered_messages_by_sender(self) -> list[FoundMessage]:
        selected_key = self.sender_filter_combo.currentData() if hasattr(self, "sender_filter_combo") else "__all__"
        messages = list(self.all_found_messages)
        if selected_key and selected_key != "__all__":
            messages = [message for message in messages if self._result_filter_key(message)[0] == selected_key]
        return sorted(messages, key=self._message_sort_key)


    def on_sender_filter_changed(self, index: int):
        if not getattr(self, "all_found_messages", None):
            return
        self.found_messages = self._filtered_messages_by_sender()
        self._reset_results_view_state()
        self._render_preview_results(self.found_messages, [], delayed_placeholder=True)
        self._set_results_title(T.RESULTS_COUNT.format(count=len(self.found_messages)))
        self._update_result_action_buttons()



    def _split_topic_chat_input(self, message: FoundMessage) -> tuple[str, str]:
        label = str(getattr(message, "chat_input", "") or "").strip()
        title, sep, suffix = label.partition(" • ")
        topic_id = getattr(message, "_ui_topic_id", None)
        if topic_id is not None:
            chat_title = title.strip() if sep else label
            return chat_title, str(topic_id).strip()
        if not sep:
            return label, ""
        cleaned_suffix = suffix.strip()
        lowered = cleaned_suffix.lower()
        if "topic id" in lowered or "топик id" in lowered:
            return title.strip(), cleaned_suffix
        return label, ""


    def _topic_id_value(self, topic_label: str) -> str:
        match = re.search(r"(\d+)", str(topic_label or ""))
        return match.group(1) if match else str(topic_label or "").strip()


    def _input_multi_topic_chat_keys(self) -> set[str]:
        widget = getattr(self, "chats_textbox", None) or getattr(self, "dialogs_input", None)
        if widget is None:
            return set()
        topics_by_chat: dict[str, set[str]] = {}
        for raw_line in widget.toPlainText().splitlines():
            line = raw_line.strip()
            if not line or "/" not in line:
                continue
            chat_part, topic_part = line.rsplit("/", 1)
            chat_key = chat_part.strip().lstrip("+").lstrip("-")
            topic_id = topic_part.strip()
            if not chat_key or not topic_id.isdigit():
                continue
            if chat_key.startswith("100") and len(chat_key) > 10:
                chat_key = chat_key[3:]
            topics_by_chat.setdefault(chat_key, set()).add(topic_id)
        return {chat_key for chat_key, topic_ids in topics_by_chat.items() if len(topic_ids) > 1}


    def _message_matches_input_topic_chat(self, message: FoundMessage, chat_keys: set[str]) -> bool:
        if not chat_keys:
            return False
        peer_digits = re.sub(r"\D", "", str(abs(int(getattr(message, "peer_id", 0) or 0))))
        if peer_digits.startswith("100") and len(peer_digits) > 10:
            peer_digits_trimmed = peer_digits[3:]
        else:
            peer_digits_trimmed = peer_digits
        return any(peer_digits.endswith(key) or peer_digits_trimmed.endswith(key) for key in chat_keys)


    def _mark_topic_ids_visibility(self, messages: list[FoundMessage]):
        input_multi_topic_chat_keys = self._input_multi_topic_chat_keys()
        topics_by_chat: dict[str, set[str]] = {}
        for message in messages:
            chat_title, topic_id = self._split_topic_chat_input(message)
            if not chat_title or not topic_id:
                continue
            topics_by_chat.setdefault(chat_title.casefold(), set()).add(self._topic_id_value(topic_id))
        for message in messages:
            chat_title, topic_id = self._split_topic_chat_input(message)
            result_has_multiple_topics = bool(topic_id and len(topics_by_chat.get(chat_title.casefold(), set())) > 1)
            input_has_multiple_topics = bool(topic_id and self._message_matches_input_topic_chat(message, input_multi_topic_chat_keys))
            show_topic = result_has_multiple_topics or input_has_multiple_topics
            try:
                message._ui_show_topic_id = show_topic
            except Exception:
                pass

    def _set_result_message_sources(self, messages: list[FoundMessage]):
        prepared_messages = list(messages)
        self._mark_topic_ids_visibility(prepared_messages)
        self.all_found_messages = sorted(prepared_messages, key=self._message_sort_key)
        self._populate_sender_filter()
        self.found_messages = self._filtered_messages_by_sender()


    def _clear_layout(self, layout):
        self.result_select_checkboxes = []
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.deleteLater()
            elif child_layout is not None:
                self._clear_layout(child_layout)


    def _set_results_title(self, text: str):
        self.results_title_label.setText(text)


    def on_reaction_mode_changed(self, checked: bool):
        self._update_all_messages_availability()
        self._update_result_action_buttons()


    def on_voice_mode_changed(self, checked: bool):
        self._update_all_messages_availability()
        self._update_result_action_buttons()


    def _set_results_scroll_enabled(self, enabled: bool):
        self.results_list.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded if enabled else Qt.ScrollBarAlwaysOff)
        self.results_list.set_scroll_locked(not enabled)
        if not enabled:
            self.results_list.verticalScrollBar().setValue(0)


    def _reset_results_view_state(self):
        self.rendered_result_count = 0
        self._scroll_load_pending = False
        self.final_render_generation = getattr(self, "final_render_generation", 0) + 1
        self.final_render_index = 0
        self.final_render_messages = []
        self.final_results_rendering = False


    def _message_sort_key(self, message: FoundMessage):
        return (message.timestamp, message.message_id)


    def _clear_results_view(self):
        self.results_list.blockSignals(True)
        self.results_list.clear()
        self.results_list.blockSignals(False)
        self.results_list._keyboard_anchor_row = None
        self.rendered_result_count = 0
        self._scroll_load_pending = False
        self.final_render_generation = getattr(self, "final_render_generation", 0) + 1
        self.final_render_index = 0
        self.final_render_messages = []
        self.final_results_rendering = False
        self.results_list._update_focus_policy()
        self.result_select_checkboxes = []


    def _create_results_item(self, payload: dict, checkable: bool = False, checked: bool = True, size_hint: QSize | None = None):
        item = ResultsListItem()
        flags = Qt.ItemIsEnabled
        if checkable:
            flags |= Qt.ItemIsSelectable
            payload["selected"] = checked
            if payload.get("kind") == "message" and "simple_render" not in payload:
                payload["simple_render"] = bool(getattr(self, "simple_render_enabled", False))
        item.setData(Qt.UserRole, payload)
        item.setFlags(flags)
        if size_hint is not None:
            item.setSizeHint(size_hint)
        if checkable:
            payload["item"] = item
        return item


    def _add_results_item(self, payload: dict, checkable: bool = False, checked: bool = True, size_hint: QSize | None = None, row: int | None = None, update_focus: bool = True):
        item = self._create_results_item(payload, checkable=checkable, checked=checked, size_hint=size_hint)
        self.results_list.blockSignals(True)
        if row is None:
            self.results_list.addItem(item)
        else:
            self.results_list.insertItem(row, item)
        self.results_list.blockSignals(False)
        if update_focus:
            self.results_list._update_focus_policy()
        return item


    def _show_results_placeholder(self, text: str):
        self._set_results_scroll_enabled(False)
        self._clear_results_view()
        self.results_list.setProperty("placeholderActive", True)
        height = max(120, self.results_list.viewport().height())
        self._add_results_item({"kind": "placeholder", "text": text}, size_hint=QSize(0, height))
        self.results_list.verticalScrollBar().setValue(0)
        self.results_list._sync_special_item_height()


    def _read_text_file(self, file_path: str) -> str:
        for encoding in ("utf-8", "utf-8-sig", "cp1251"):
            try:
                with open(file_path, "r", encoding=encoding) as file:
                    return file.read()
            except Exception:
                continue
        raise RuntimeError(T.ERROR_READ_TXT)


    def _write_export_file(self, file_path: str, text: str):
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        try:
            with open(tmp_path, "w", encoding="utf-8-sig", newline="") as file:
                file.write(text)
            try:
                os.replace(tmp_path, path)
            except PermissionError:
                raise
            except OSError as exc:
                message = str(exc).lower()
                if getattr(exc, "errno", None) in (13, 16, 26, 32) or getattr(exc, "winerror", None) in (5, 32, 33) or "permission denied" in message or "access is denied" in message or "being used" in message or "используется" in message:
                    raise PermissionError(str(exc)) from exc
                raise
        finally:
            try:
                if tmp_path.exists():
                    tmp_path.unlink()
            except Exception:
                pass


    def _export_directory(self) -> Path:
        phone = (getattr(self, "current_phone", None) or "").strip()
        if not phone and hasattr(self, "phone_entry"):
            phone = self.phone_entry.text().strip()
        try:
            directory = user_session_dir(phone, create=True) / "exports"
        except Exception:
            directory = users_dir(create=True) / "exports"
        directory.mkdir(parents=True, exist_ok=True)
        return directory


    def _export_file_path(self) -> Path:
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        return self._export_directory() / f"{T.EXPORT_FILE_PREFIX}_{stamp}.csv"


    def _normalize_export_file_path(self, file_path: str) -> str:
        value = str(file_path or "").strip()
        if value and Path(value).suffix.lower() != ".csv":
            value = f"{value}.csv"
        return value


    def _import_text_into_widget(self, target: QPlainTextEdit, title: str):
        file_path, _ = QFileDialog.getOpenFileName(self, title, "", T.TXT_FILTER)
        self._restore_focus_after_dialog()
        if not file_path:
            return
        try:
            content = self._read_text_file(file_path)
            target.setPlainText(content.strip())
            self._restore_focus_after_dialog()
        except Exception as exc:
            self._show_error_dialog(T.ERROR_TITLE, str(exc))


    def on_import_chats(self):
        self._import_text_into_widget(self.chats_textbox, T.IMPORT_DIALOGS_TITLE)


    def on_import_words(self):
        self._import_text_into_widget(self.words_textbox, T.IMPORT_WORDS_TITLE)


    def _export_dialog_type_label(self, message: FoundMessage) -> str:
        key = getattr(message, "_export_dialog_type_key", "")
        if key and hasattr(T, key):
            return getattr(T, key)
        return T.EXPORT_GROUP if message.chat_is_group else T.EXPORT_PRIVATE_DIALOG


    def _export_bool_value(self, enabled: bool) -> str:
        return T.YES if enabled else T.NO


    def _export_metadata_row(self, writer, name: str, value):
        writer.writerow([f"{name}:", value])


    def _export_message_text(self, message: FoundMessage) -> str:
        text = translate_runtime_text(message.text.strip()) if message.text else ""
        if self.current_results_mode == "reactions" and text == T.CONTENT_REACTION_NO_TEXT:
            text = f"{T.CONTENT_REACTION_ON_PREFIX}{translate_content_kind(message.content_kind)}{T.CONTENT_WITHOUT_TEXT_SUFFIX}"
        return text or f"[{translate_content_kind(message.content_kind)}{T.CONTENT_WITHOUT_TEXT_SUFFIX}"


    def _export_current_filter_value(self) -> str:
        if not hasattr(self, "sender_filter_combo"):
            return T.SENDER_FILTER_ALL
        value = (self.sender_filter_combo.currentText() or "").strip()
        return value or T.SENDER_FILTER_ALL


    def _export_loading_stopped_value(self, metadata: dict) -> str:
        return self._export_bool_value(metadata.get("loading") == "stopped")


    def _build_export_csv(self) -> str:
        metadata = getattr(self, "last_search_export_metadata", {}) or {}
        output = io.StringIO(newline="")
        writer = csv.writer(output, delimiter=";", lineterminator="\n")
        self._export_metadata_row(writer, T.EXPORT_METADATA_TOTAL_MESSAGES, len(self.found_messages))
        self._export_metadata_row(writer, T.EXPORT_METADATA_WORDS_NAME, metadata.get("words") or "—")
        self._export_metadata_row(writer, T.EXPORT_METADATA_DIALOGS_NAME, metadata.get("dialogs") or "—")
        self._export_metadata_row(writer, T.EXPORT_METADATA_FILTER_NAME, self._export_current_filter_value())
        self._export_metadata_row(writer, T.EXPORT_METADATA_REACTIONS_NAME, self._export_bool_value(bool(metadata.get("reactions"))))
        self._export_metadata_row(writer, T.EXPORT_METADATA_VOICE_NAME, self._export_bool_value(bool(metadata.get("voice"))))
        self._export_metadata_row(writer, T.EXPORT_METADATA_LOADING_NAME, self._export_loading_stopped_value(metadata))
        self._export_metadata_row(writer, T.EXPORT_METADATA_DELETE_STOPPED_NAME, self._export_bool_value(bool(getattr(self, "last_delete_was_stopped", False))))
        self._export_metadata_row(writer, T.EXPORT_METADATA_DELETE_ERROR_NAME, self._export_bool_value(bool(getattr(self, "last_delete_had_error", False))))
        writer.writerow([])
        include_found_by = not bool(metadata.get("all_messages"))
        include_message_type = bool(metadata.get("reactions"))
        header = [
            T.EXPORT_DIALOG.format(value="").rstrip(": "),
            T.EXPORT_DIALOG_TYPE.format(value="").rstrip(": "),
            "ID",
            T.EXPORT_DATE.format(value="").rstrip(": "),
            T.EXPORT_SENDER.format(value="").rstrip(": "),
        ]
        if include_message_type:
            header.append(T.EXPORT_MESSAGE_TYPE.format(value="").rstrip(": "))
        if include_found_by:
            header.append(T.EXPORT_FOUND_BY.format(value="").rstrip(": "))
        header.append(T.EXPORT_TEXT)
        writer.writerow(header)
        for message in self.found_messages:
            sender = display_sender_name(message) or ""
            row = [
                message.chat_input,
                self._export_dialog_type_label(message),
                message.message_id,
                message.date,
                sender,
            ]
            if include_message_type:
                row.append(translate_content_kind(message.content_kind))
            if include_found_by:
                row.append(", ".join(message.matched_terms or []))
            row.append(self._export_message_text(message))
            writer.writerow(row)
        return output.getvalue()


    def on_export_results(self):
        if not self.found_messages:
            self._show_warning_dialog(T.WARNING_NO_MESSAGES_TITLE, T.WARNING_NO_MESSAGES_TO_EXPORT)
            return
        selected_path, _ = QFileDialog.getSaveFileName(self, T.EXPORT_SAVE_TITLE, str(self._export_file_path()), T.CSV_FILTER)
        self._restore_focus_after_dialog()
        if not selected_path:
            return
        try:
            file_path = self._normalize_export_file_path(selected_path)
            self._write_export_file(file_path, self._build_export_csv())
            display_path = str(file_path).replace("\\", "/")
            self._show_info_dialog(T.AUTH_READY_TITLE, T.EXPORT_DONE.format(path=display_path))
        except PermissionError:
            self._show_error_dialog(T.EXPORT_SAVE_ERROR_TITLE, T.EXPORT_SAVE_PERMISSION_ERROR, copy_text="")
        except OSError as exc:
            message = str(exc).lower()
            if getattr(exc, "errno", None) in (13, 16, 26, 32) or getattr(exc, "winerror", None) in (5, 32, 33) or "permission denied" in message or "access is denied" in message or "being used" in message or "используется" in message:
                self._show_error_dialog(T.EXPORT_SAVE_ERROR_TITLE, T.EXPORT_SAVE_PERMISSION_ERROR, copy_text="")
            else:
                self._show_error_dialog(T.ERROR_TITLE, str(exc))
        except Exception as exc:
            message = str(exc).lower()
            if "permission denied" in message or "access is denied" in message or "being used" in message or "используется" in message:
                self._show_error_dialog(T.EXPORT_SAVE_ERROR_TITLE, T.EXPORT_SAVE_PERMISSION_ERROR, copy_text="")
            else:
                self._show_error_dialog(T.ERROR_TITLE, str(exc))


    def _on_results_item_changed(self, item):
        payload = item.data(Qt.UserRole) or {}
        if payload.get("kind") != "message":
            return
        message = payload.get("message")
        if message is not None:
            state = item.checkState() == Qt.Checked
            payload["selected"] = state
            item.setData(Qt.UserRole, payload)
            message.selected = state
        has_results = bool(self.found_messages)
        loading = self._is_search_loading()
        self.delete_button.setVisible(True)
        self.delete_button.setEnabled(has_results and not loading)


    def _show_rendering_results_placeholder(self):
        self._set_results_scroll_enabled(False)
        self.results_list.setUpdatesEnabled(True)
        self._show_results_placeholder(T.RENDERING_MESSAGES)
        self.results_list.viewport().update()
        self.results_list.viewport().repaint()
        if hasattr(self, "search_status_label"):
            self.search_status_label.update()
            self.search_status_label.repaint()
        QApplication.processEvents()


    def _show_rendering_results_placeholder_for_generation(self, generation: int):
        if generation != getattr(self, "final_render_generation", 0):
            return
        if not getattr(self, "final_results_rendering", False):
            return
        self._set_results_scroll_enabled(False)
        self.results_list.setUpdatesEnabled(True)
        self.results_list.blockSignals(True)
        self.results_list.clear()
        self.results_list.blockSignals(False)
        self.results_list._keyboard_anchor_row = None
        self.result_select_checkboxes = []
        self.results_list.setProperty("placeholderActive", True)
        height = max(120, self.results_list.viewport().height())
        self._add_results_item({"kind": "placeholder", "text": T.RENDERING_MESSAGES}, size_hint=QSize(0, height))
        self.results_list.verticalScrollBar().setValue(0)
        self.results_list._sync_special_item_height()
        self.results_list.viewport().update()
        self.results_list.viewport().repaint()
        if hasattr(self, "search_status_label"):
            self.search_status_label.update()
            self.search_status_label.repaint()
        QApplication.processEvents()


    def _restore_final_render_list_state(self, restore_layout_mode: bool = True):
        if not hasattr(self, "results_list"):
            return
        previous_layout_mode = getattr(self, "final_render_previous_layout_mode", None)
        if restore_layout_mode and previous_layout_mode is not None:
            self.results_list.setLayoutMode(previous_layout_mode)
            self.final_render_previous_layout_mode = None
        self.results_list.setUpdatesEnabled(True)


    def _final_render_option(self):
        option = QStyleOptionViewItem()
        option.initFrom(self.results_list)
        viewport = self.results_list.viewport()
        width = max(260, viewport.width() if viewport is not None else 760)
        option.rect = self.results_list.rect().adjusted(0, 0, 0, 0)
        option.rect.setWidth(width)
        return option, width


    def _prepare_message_render_cache(self, messages: list[FoundMessage]):
        if bool(getattr(self, "active_results_simple_render", getattr(self, "simple_render_enabled", False))):
            return
        delegate = self.results_list.itemDelegate() if hasattr(self, "results_list") else None
        if not hasattr(delegate, "prepare_message_cache"):
            return
        option, width = self._final_render_option()
        for message in messages:
            delegate.prepare_message_cache(message, option, width)


    def _cpu_threads_count(self) -> int:
        try:
            return max(1, int(os.cpu_count() or 1))
        except Exception:
            return 1


    def _initial_final_render_profile(self, total: int) -> tuple[int, int, float]:
        if bool(getattr(self, "active_results_simple_render", getattr(self, "simple_render_enabled", False))):
            if total > 2500:
                return 180, 1, 18.0
            if total > 700:
                return 240, 0, 20.0
            return 360, 0, 22.0
        threads = self._cpu_threads_count()
        if threads >= 16:
            batch_size = 40
            delay_ms = 4
            target_ms = 10.0
        elif threads >= 8:
            batch_size = 30
            delay_ms = 8
            target_ms = 9.0
        elif threads >= 4:
            batch_size = 20
            delay_ms = 12
            target_ms = 8.0
        else:
            batch_size = 10
            delay_ms = 16
            target_ms = 6.0
        if total > 2500:
            batch_size = max(self.HIDDEN_FINAL_RENDER_MIN_BATCH_SIZE, batch_size // 2)
            delay_ms = min(self.HIDDEN_FINAL_RENDER_MAX_DELAY_MS, delay_ms + 4)
        elif total < 300:
            batch_size = min(self.HIDDEN_FINAL_RENDER_MAX_BATCH_SIZE, batch_size + 10)
            delay_ms = max(self.HIDDEN_FINAL_RENDER_MIN_DELAY_MS, delay_ms - 4)
        return batch_size, delay_ms, target_ms


    def _tune_final_render_profile(self, elapsed_ms: float):
        target_ms = getattr(self, "final_render_target_ms", self.HIDDEN_FINAL_RENDER_TARGET_MS)
        batch_size = getattr(self, "final_render_batch_size", self.HIDDEN_FINAL_RENDER_BATCH_SIZE)
        delay_ms = getattr(self, "final_render_batch_delay_ms", self.HIDDEN_FINAL_RENDER_BATCH_DELAY_MS)
        fast_batches = getattr(self, "final_render_fast_batches", 0)
        if elapsed_ms > target_ms * 1.6:
            batch_size = max(self.HIDDEN_FINAL_RENDER_MIN_BATCH_SIZE, int(batch_size * 0.7))
            delay_ms = min(self.HIDDEN_FINAL_RENDER_MAX_DELAY_MS, delay_ms + 4)
            fast_batches = 0
        elif elapsed_ms < target_ms * 0.45:
            fast_batches += 1
            if fast_batches >= 3:
                batch_size = min(self.HIDDEN_FINAL_RENDER_MAX_BATCH_SIZE, batch_size + 5)
                delay_ms = max(self.HIDDEN_FINAL_RENDER_MIN_DELAY_MS, delay_ms - 2)
                fast_batches = 0
        else:
            fast_batches = 0
        self.final_render_batch_size = batch_size
        self.final_render_batch_delay_ms = delay_ms
        self.final_render_fast_batches = fast_batches


    def _set_simple_render_checkbox_enabled(self, enabled: bool):
        checkbox = getattr(self, "simple_render_checkbox", None)
        if checkbox is None:
            return
        checkbox.setEnabled(bool(enabled))
        if not enabled:
            checkbox.clearFocus()


    def _set_final_render_interactive_controls_enabled(self, enabled: bool):
        enabled = bool(enabled)
        preview_button = getattr(self, "preview_button", None)
        if preview_button is not None and self.auth_state == "authorized":
            preview_button.setEnabled(enabled)


    def _offer_simple_render_for_large_results(self, total: int):
        if total <= self.SIMPLE_RENDER_RECOMMEND_LIMIT:
            return
        if bool(getattr(self, "simple_render_enabled", False)):
            return
        if not hasattr(self, "_confirm_dialog_default_no"):
            return
        if not self._confirm_dialog_default_no(T.SIMPLE_RENDER_RECOMMEND_TITLE, T.SIMPLE_RENDER_RECOMMEND_MESSAGE):
            return
        self.simple_render_enabled = True
        checkbox = getattr(self, "simple_render_checkbox", None)
        if checkbox is not None:
            checkbox.blockSignals(True)
            checkbox.setChecked(True)
            checkbox.blockSignals(False)
        save_saved_field("simple_render", "1")


    def _start_final_results_render(self, found_messages: list[FoundMessage], delayed_placeholder: bool = False):
        self._offer_simple_render_for_large_results(len(found_messages))
        sorted_messages = sorted(found_messages, key=self._message_sort_key)
        self.found_messages = sorted_messages
        skip_placeholder = bool(delayed_placeholder and len(sorted_messages) <= self.FILTER_RENDERING_PLACEHOLDER_SKIP_LIMIT)
        delay_placeholder = bool(delayed_placeholder and not skip_placeholder)
        if not delay_placeholder:
            if skip_placeholder:
                self._set_results_scroll_enabled(False)
                self._clear_results_view()
                self.results_list.setProperty("placeholderActive", False)
            else:
                self._show_rendering_results_placeholder()
        generation = getattr(self, "final_render_generation", 0) + 1
        self.final_render_generation = generation
        self.active_results_simple_render = bool(getattr(self, "simple_render_enabled", False))
        self.final_render_messages = list(sorted_messages)
        self.final_render_index = 0
        batch_size, delay_ms, target_ms = self._initial_final_render_profile(len(sorted_messages))
        self.final_render_batch_size = batch_size
        self.final_render_batch_delay_ms = delay_ms
        self.final_render_target_ms = target_ms
        self.final_render_fast_batches = 0
        self.final_results_rendering = True
        self.rendered_result_count = 0
        self._set_final_render_interactive_controls_enabled(True)
        self._set_simple_render_checkbox_enabled(False)
        if hasattr(self, "stop_loading_button"):
            self.stop_loading_button.setEnabled(False)
            self.stop_loading_button.clearFocus()
        if hasattr(self, "search_controls_toggle_button"):
            self.search_controls_toggle_button.setEnabled(False)
            self.search_controls_toggle_button.clearFocus()
        if delay_placeholder:
            QTimer.singleShot(self.FILTER_RENDERING_PLACEHOLDER_DELAY_MS, lambda: self._show_rendering_results_placeholder_for_generation(generation))
            QTimer.singleShot(self.FILTER_RENDERING_PLACEHOLDER_DELAY_MS + self.HIDDEN_FINAL_RENDER_START_DELAY_MS, lambda: self._prepare_final_results_hidden_render(generation))
        else:
            QTimer.singleShot(self.HIDDEN_FINAL_RENDER_START_DELAY_MS, lambda: self._prepare_final_results_hidden_render(generation))


    def _prepare_final_results_hidden_render(self, generation: int):
        if generation != getattr(self, "final_render_generation", 0):
            return
        self._set_results_scroll_enabled(False)
        self.final_render_previous_layout_mode = self.results_list.layoutMode()
        self.results_list.setLayoutMode(QListView.SinglePass)
        self.results_list.setUpdatesEnabled(True)
        QTimer.singleShot(0, lambda: self._render_final_results_hidden_batch(generation))


    def _render_final_results_hidden_batch(self, generation: int):
        if generation != getattr(self, "final_render_generation", 0):
            self._restore_final_render_list_state()
            return
        messages = getattr(self, "final_render_messages", [])
        start = getattr(self, "final_render_index", 0)
        batch_size = getattr(self, "final_render_batch_size", self.HIDDEN_FINAL_RENDER_BATCH_SIZE)
        end = min(start + batch_size, len(messages))
        current_batch = messages[start:end]
        batch_started_at = time.perf_counter()
        self._prepare_message_render_cache(current_batch)
        simple_render = bool(getattr(self, "active_results_simple_render", getattr(self, "simple_render_enabled", False)))
        batch_payloads = [{"kind": "message", "message": message, "selected": bool(getattr(message, "selected", True)), "simple_render": simple_render} for message in current_batch]
        if batch_payloads:
            self.results_list.blockSignals(True)
            self.results_list.addPayloads(batch_payloads)
            self.results_list.blockSignals(False)
        elapsed_ms = (time.perf_counter() - batch_started_at) * 1000.0
        self._tune_final_render_profile(elapsed_ms)
        self.final_render_index = end
        self.rendered_result_count = end
        if end < len(messages):
            delay_ms = getattr(self, "final_render_batch_delay_ms", self.HIDDEN_FINAL_RENDER_BATCH_DELAY_MS)
            QTimer.singleShot(delay_ms, lambda: self._render_final_results_hidden_batch(generation))
            return
        self._finish_final_results_hidden_render(generation)


    def _finish_final_results_hidden_render(self, generation: int):
        if generation != getattr(self, "final_render_generation", 0):
            self._restore_final_render_list_state()
            return
        self.results_list.doItemsLayout()
        self.results_list.updateGeometries()
        self._remove_results_placeholder_items()
        self.results_list.setProperty("placeholderActive", False)
        self.results_list.verticalScrollBar().setValue(0)
        self.results_list._update_focus_policy()
        self._restore_final_render_list_state(restore_layout_mode=False)
        self.results_list.setCurrentRow(-1)
        self.results_list.viewport().repaint()
        QTimer.singleShot(0, lambda: self._show_final_results_scrollbar(generation))


    def _show_final_results_scrollbar(self, generation: int):
        if generation != getattr(self, "final_render_generation", 0):
            return
        self._set_results_scroll_enabled(True)
        self.results_list.verticalScrollBar().setValue(0)
        self.results_list.updateGeometries()
        self.results_list.viewport().update()
        self.final_results_rendering = False
        self.render_controls_locked = False
        self._set_final_render_interactive_controls_enabled(True)
        self._set_simple_render_checkbox_enabled(True)
        if hasattr(self, "stop_loading_button") and not self._is_search_loading():
            self.stop_loading_button.setEnabled(True)
        if hasattr(self, "search_controls_toggle_button") and not self._is_search_loading():
            self.search_controls_toggle_button.setEnabled(True)
        if getattr(self, "unlock_search_controls_after_final_render", False):
            self.unlock_search_controls_after_final_render = False
            self.active_search_task_id = None
            self.search_stop_requested = False
            self.controller.stop_requested = False
            self._set_search_loading_controls(False)
            self._release_search_input_cursor_refresh_after_status()
            self._update_result_action_buttons()
        elif not self._is_search_loading():
            self._set_search_loading_controls(False)
            self._update_result_action_buttons()


    def _remove_results_placeholder_items(self):
        row = 0
        while row < self.results_list.count():
            payload = self.results_list.item(row).data(Qt.UserRole) or {}
            if payload.get("kind") == "placeholder":
                self.results_list.takeItem(row)
                continue
            row += 1


    def _refresh_rendered_results_language(self):
        has_rendered_messages = False
        for row in range(self.results_list.count()):
            item = self.results_list.item(row)
            payload = item.data(Qt.UserRole) or {}
            kind = payload.get("kind")
            if kind == "message":
                has_rendered_messages = True
                message = payload.get("message")
                if message is not None:
                    delegate = self.results_list.itemDelegate()
                    if hasattr(delegate, "clear_message_cache"):
                        delegate.clear_message_cache(message)
                continue
            if kind == "placeholder":
                text = payload.get("text", "")
                if text in (
                    "Loading messages, results will appear here after loading finishes or stops",
                    "Загружаю сообщения, они появятся здесь после завершения или остановки загрузки",
                ):
                    payload["text"] = T.LOADING_MESSAGES
                elif text in ("Displaying messages", "Displaying messages...", "Отображаю сообщения", "Отображаю сообщения..."):
                    payload["text"] = T.RENDERING_MESSAGES
                elif text in ("No messages found", "Сообщения не найдены"):
                    payload["text"] = T.NOTHING_FOUND
                elif text in ("Search results will appear here", "Здесь появятся найденные сообщения"):
                    payload["text"] = T.RESULTS_EMPTY_PLACEHOLDER
                item.setData(Qt.UserRole, payload)
        if has_rendered_messages:
            self.results_list.viewport().update()
        else:
            self.results_list.viewport().update()


    def _render_preview_results(self, found_messages: list[FoundMessage], errors: list[str], delayed_placeholder: bool = False):
        if found_messages:
            self._start_final_results_render(found_messages, delayed_placeholder=delayed_placeholder)
        else:
            self._set_results_scroll_enabled(False)
            self._show_results_placeholder(T.NOTHING_FOUND)


    def _render_delete_results(self, deleted_count: int, errors: list[str]):
        self._set_results_scroll_enabled(False)
        self.results_list.setUpdatesEnabled(False)
        try:
            self._clear_results_view()
            self.results_list.setProperty("placeholderActive", True)
            height = max(120, self.results_list.viewport().height())
            self._add_results_item({"kind": "placeholder", "text": T.DELETE_SUCCESS_MESSAGE}, size_hint=QSize(0, height))
            self.results_list.verticalScrollBar().setValue(0)
            self.results_list._sync_special_item_height()
        finally:
            self.results_list.setUpdatesEnabled(True)
            self.results_list.viewport().update()
        if errors:
            self._show_error_dialog(T.ERROR_DELETE_TITLE, "\n".join(errors))