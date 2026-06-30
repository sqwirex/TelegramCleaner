from typing import Callable

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication

from tgcleaner.core.config import ADMIN_USERNAME
from tgcleaner.core.i18n import T, translate_telegram_error
from tgcleaner.core.models import FoundMessage
from tgcleaner.core.parsing import parse_chats


class MainWindowSearchMixin:
    def _all_mode_admin_enabled(self) -> bool:
        admin_username = (ADMIN_USERNAME or "").strip().lstrip("@").lower()
        username = (getattr(self.controller, "current_username", None) or "").strip().lstrip("@").lower()
        return bool(admin_username) and username == admin_username


    def _refresh_all_mode_visibility(self):
        admin_visible = self._all_mode_admin_enabled() and self.auth_state == "authorized"
        self.all_checkbox.setVisible(True)
        self.all_messages_checkbox.setVisible(admin_visible)
        if not admin_visible and self.all_messages_checkbox.isChecked():
            self.all_messages_checkbox.blockSignals(True)
            self.all_messages_checkbox.setChecked(False)
            self.all_messages_checkbox.blockSignals(False)
            self.on_all_messages_mode_changed(False)

    def _refresh_search_input_cursors_under_mouse(self):
        if hasattr(self, "_refresh_input_cursors_under_mouse"):
            self._refresh_input_cursors_under_mouse()


    def on_all_mode_changed(self, checked: bool):
        if checked and self.only_groups_checkbox.isChecked():
            self.only_groups_checkbox.blockSignals(True)
            self.only_groups_checkbox.setChecked(False)
            self.only_groups_checkbox.blockSignals(False)
        self._update_dialog_source_mode()


    def on_only_groups_mode_changed(self, checked: bool):
        if checked and self.all_checkbox.isChecked():
            self.all_checkbox.blockSignals(True)
            self.all_checkbox.setChecked(False)
            self.all_checkbox.blockSignals(False)
        self._update_dialog_source_mode()


    def _update_dialog_source_mode(self):
        checked_all = self.all_checkbox.isChecked()
        checked_groups = self.only_groups_checkbox.isChecked()
        enabled = not checked_all and not checked_groups and self.auth_state == "authorized"
        self.chats_textbox.setEnabled(enabled)
        self.import_chats_button.setEnabled(enabled)
        self._clear_disabled_input_focus_and_selection()
        if checked_groups:
            mode_text = T.DIALOGS_ONLY_GROUPS_PLACEHOLDER
        elif checked_all:
            mode_text = T.DIALOGS_ALL_PLACEHOLDER
        else:
            mode_text = ""
        if hasattr(self.chats_textbox, "setDisplayOverrideText"):
            self.chats_textbox.setDisplayOverrideText(mode_text)
        self.chats_textbox.setPlaceholderText(mode_text or self.chats_hint_text)
        self._refresh_search_input_cursors_under_mouse()


    def _update_all_messages_availability(self):
        self._refresh_all_mode_visibility()
        if self.auth_state == "authorized" and self.all_messages_checkbox.isVisible():
            self.all_messages_checkbox.setEnabled(True)
        self.on_all_messages_mode_changed(self.all_messages_checkbox.isChecked())


    def on_all_messages_mode_changed(self, checked: bool):
        if checked and not self._all_mode_admin_enabled():
            self.all_messages_checkbox.blockSignals(True)
            self.all_messages_checkbox.setChecked(False)
            self.all_messages_checkbox.blockSignals(False)
            checked = False
        enabled = not checked and self.auth_state == "authorized"
        self.words_textbox.setEnabled(enabled)
        self.import_words_button.setEnabled(enabled)
        if self.auth_state == "authorized" and self.all_messages_checkbox.isVisible():
            self.all_messages_checkbox.setEnabled(True)
        self._clear_disabled_input_focus_and_selection()
        mode_text = T.WORDS_ALL_PLACEHOLDER if checked else ""
        if hasattr(self.words_textbox, "setDisplayOverrideText"):
            self.words_textbox.setDisplayOverrideText(mode_text)
        self.words_textbox.setPlaceholderText(mode_text or self.words_hint_text)
        self._refresh_search_input_cursors_under_mouse()


    def _get_search_inputs(self):
        chats_input = self.chats_textbox.toPlainText().strip()
        words_input = self.words_textbox.toPlainText().strip()
        all_mode = self.all_checkbox.isChecked()
        only_groups_mode = self.only_groups_checkbox.isChecked()
        all_messages_mode = self.all_messages_checkbox.isChecked()
        reaction_mode = self.reaction_mode_checkbox.isChecked()
        voice_mode = self.voice_mode_checkbox.isChecked()
        has_words = bool(words_input)
        effective_all_messages_mode = all_messages_mode and self._all_mode_admin_enabled()
        chat_inputs = parse_chats(chats_input)
        if not all_mode and not only_groups_mode and not chat_inputs:
            raise ValueError(T.SEARCH_CHATS_REQUIRED)
        if effective_all_messages_mode and not (only_groups_mode or reaction_mode or voice_mode):
            raise ValueError(T.SEARCH_ALL_WORDS_REQUIRES_MODE)
        if not has_words and not effective_all_messages_mode:
            raise ValueError(T.SEARCH_WORDS_REQUIRED_ADMIN if self._all_mode_admin_enabled() else T.SEARCH_WORDS_REQUIRED)
        return chat_inputs, words_input, all_mode, effective_all_messages_mode, only_groups_mode, reaction_mode, voice_mode


    def on_preview(self):
        try:
            chat_inputs, words_input, all_mode, all_messages_mode, only_groups_mode, reaction_mode, voice_mode = self._get_search_inputs()
        except Exception as exc:
            self._show_warning_dialog(T.ERROR_TITLE, str(exc))
            return
        self.previous_result_messages_backup = []
        self.previous_result_filter_mode_backup = getattr(self, "result_filter_mode", "sender")
        self.previous_results_mode_backup = getattr(self, "current_results_mode", "messages")
        self.found_messages = []
        self.all_found_messages = []
        self._set_results_title(T.SECTION_RESULTS_ZERO)
        self.search_status_label.setText(T.STARTING_LOADING)
        self.search_status_label.repaint()
        self.pending_result_filter_mode = "chat" if only_groups_mode else "sender"
        self._reset_sender_filter()
        self.pending_result_messages.clear()
        self.pending_result_timer.stop()
        self.rendered_result_count = 0
        self.last_results_total_count = 0
        self.search_stop_requested = False
        self.controller.stop_requested = False
        self.pending_results_mode = "reactions" if reaction_mode else "messages"
        self.last_delete_had_error = False
        self.last_delete_was_stopped = False
        self.search_results_view_started = False
        self._start_search_results_view()
        if all_mode:
            export_dialogs = T.CHECKBOX_ALL
        elif only_groups_mode:
            export_dialogs = T.CHECKBOX_ONLY_GROUPS
        else:
            export_dialogs = ", ".join(chat_inputs)
        export_words = T.CHECKBOX_ALL if all_messages_mode else words_input
        self.last_search_export_metadata = {
            "words": export_words,
            "dialogs": export_dialogs,
            "all_dialogs": all_mode,
            "only_groups": only_groups_mode,
            "all_messages": all_messages_mode,
            "reactions": reaction_mode,
            "voice": voice_mode,
            "delete_for_everyone": self.revoke_checkbox.isChecked(),
            "loading": "running",
        }
        self._set_search_loading_controls(True)
        self._update_result_action_buttons()
        self.export_results_button.setEnabled(False)
        self.export_results_button.clearFocus()
        if hasattr(self, "revoke_checkbox"):
            self.revoke_checkbox.setEnabled(False)
            self.revoke_checkbox.clearFocus()
        self.preview_button.setEnabled(False)
        self.stop_loading_button.clearFocus()
        self.preview_button.clearFocus()
        if hasattr(self, "central_root_widget"):
            self.central_root_widget.setFocus(Qt.OtherFocusReason)
        else:
            self.setFocus(Qt.OtherFocusReason)
        self._force_results_placeholder_repaint()

        def start_preview_task():
            if getattr(self, "search_stop_requested", False):
                return
            self.active_search_task_id = self._run_async_with_progress(
                lambda progress: self.controller.find_messages(chat_inputs, words_input, None, all_mode, all_messages_mode, only_groups_mode, progress, reaction_mode, voice_mode),
                self._on_preview_done,
                lambda error: self._show_search_error(T.ERROR_STATUS, error),
            )

        QTimer.singleShot(60, start_preview_task)


    def _start_search_results_view(self):
        if getattr(self, "search_results_view_started", False):
            return
        self.search_results_view_started = True
        self._set_results_title(T.SECTION_RESULTS_ZERO)
        self._show_results_placeholder(T.LOADING_MESSAGES)
        self._update_result_action_buttons()

    def _force_results_placeholder_repaint(self):
        if hasattr(self, "results_list"):
            self.results_list.setUpdatesEnabled(True)
            self.results_list.viewport().setUpdatesEnabled(True)
            self.results_list.updateGeometry()
            self.results_list.updateGeometries()
            self.results_list.viewport().update()
            QApplication.sendPostedEvents(None, 0)
            self.results_list.viewport().repaint()
        if hasattr(self, "results_title_label"):
            self.results_title_label.repaint()
        QApplication.sendPostedEvents(None, 0)
        QApplication.processEvents()


    def _apply_results_mode(self, mode: str):
        self.current_results_mode = mode
        self.delete_button.setText(T.BUTTON_DELETE_REACTIONS if mode == "reactions" else T.BUTTON_DELETE_MESSAGES)
        self._update_revoke_checkbox_state()


    def _revoke_checkbox_forced_by_displayed_results(self) -> bool:
        messages = list(getattr(self, "found_messages", []) or [])
        if not messages:
            return False
        return all(
            bool(getattr(message, "is_reaction", False))
            or bool(getattr(message, "chat_is_group", False))
            for message in messages
        )


    def _update_revoke_checkbox_state(self, controls_blocked: bool | None = None):
        if not hasattr(self, "revoke_checkbox"):
            return
        forced = self._revoke_checkbox_forced_by_displayed_results()
        self.revoke_checkbox.setVisible(True)
        if forced and not self.revoke_checkbox.isChecked():
            self.revoke_checkbox.blockSignals(True)
            self.revoke_checkbox.setChecked(True)
            self.revoke_checkbox.blockSignals(False)
        if isinstance(getattr(self, "last_search_export_metadata", None), dict):
            self.last_search_export_metadata["delete_for_everyone"] = self.revoke_checkbox.isChecked()
        if controls_blocked is None:
            controls_blocked = self._is_search_loading() or getattr(self, "final_results_rendering", False) or getattr(self, "render_controls_locked", False)
        self.revoke_checkbox.setEnabled((not controls_blocked) and (not forced))


    def _apply_pending_result_filter_mode(self):
        self.result_filter_mode = getattr(self, "pending_result_filter_mode", "sender")


    def _status_with_results_hint(self, status: str) -> str:
        return status


    def _is_network_search_error_text(self, text: str) -> bool:
        lowered_error = str(text or "").lower()
        return any(token in lowered_error for token in ["network", "internet", "timed out", "timeout", "telegram не отвечает", "соедин"])


    def _translate_first_search_error(self, errors) -> str:
        if not errors:
            return T.ERROR_STATUS
        return translate_telegram_error(errors[0])


    def _handle_search_failed_before_results(self, errors):
        translated_error = self._translate_first_search_error(errors)
        self._show_error_dialog(T.ERROR_TITLE, translated_error)
        self.search_status_label.setText(T.NETWORK_SEARCH_RETRY_STATUS if self._is_network_search_error_text(translated_error) else T.ERROR_STATUS)
        self.active_search_task_id = None
        self.search_stop_requested = False
        self.controller.stop_requested = False
        self.found_messages = []
        self.all_found_messages = []
        self.previous_result_messages_backup = []
        self._reset_sender_filter()
        self._set_results_title(T.SECTION_RESULTS_ZERO)
        self._set_results_scroll_enabled(False)
        self._show_results_placeholder(T.NOTHING_FOUND)
        self._set_search_loading_controls(False)
        self._release_search_input_cursor_refresh_after_status()
        self._update_result_action_buttons()


    def _on_preview_done(self, result):
        if len(result) >= 5:
            found_messages, errors, _, checked_chats, total_chats = result
        else:
            found_messages, errors, _ = result
            checked_chats = None
            total_chats = None
        self.pending_result_messages.clear()
        self.pending_result_timer.stop()
        self._reset_results_view_state()
        self._apply_pending_result_filter_mode()
        self._set_result_message_sources(found_messages)
        self._apply_results_mode(self.pending_results_mode)
        if not found_messages and not self.search_stop_requested:
            translated_probe = self._translate_first_search_error(errors) if errors else T.TELEGRAM_ERROR_NETWORK
            if (errors and self._is_network_search_error_text(translated_probe)) or total_chats == 0:
                self._handle_search_failed_before_results(errors or [T.TELEGRAM_ERROR_NETWORK])
                return
        should_render_results = bool(found_messages) or not errors or getattr(self, "search_results_view_started", False)
        if found_messages or not errors:
            if self.search_stop_requested:
                base_status = T.STOPPED_STATUS
                self.last_search_export_metadata["loading"] = "stopped"
            else:
                base_status = T.DONE_STATUS
                self.last_search_export_metadata["loading"] = "completed"
            if checked_chats is not None and total_chats is not None:
                processed_chats = max(0, checked_chats - len(errors))
                status = f"{base_status}{T.CHECKED_CHATS_SUFFIX.format(checked=processed_chats, total=total_chats)}"
            else:
                status = base_status
            self.search_status_label.setText(self._status_with_results_hint(status))
            QApplication.processEvents()
        else:
            if errors and checked_chats is not None and total_chats is not None:
                processed_chats = max(0, checked_chats - len(errors))
                status = f"{T.DONE_STATUS}{T.CHECKED_CHATS_SUFFIX.format(checked=processed_chats, total=total_chats)}"
                self.search_status_label.setText(self._status_with_results_hint(status))
            else:
                self.search_status_label.setText(T.SEARCH_READY_STATUS)
        defer_controls_until_results_visible = bool(should_render_results and self.found_messages)
        if should_render_results:
            self._start_search_results_view()
            if defer_controls_until_results_visible:
                self.unlock_search_controls_after_final_render = True
            self._render_preview_results(self.found_messages, errors)
            self._set_results_title(T.RESULTS_COUNT.format(count=len(self.found_messages)))
        self.previous_result_messages_backup = []
        if not defer_controls_until_results_visible:
            self.active_search_task_id = None
            self.search_stop_requested = False
            self.controller.stop_requested = False
            self._set_search_loading_controls(False)
            self._release_search_input_cursor_refresh_after_status()
            self._update_result_action_buttons()


    def _queue_streamed_message(self, message: FoundMessage, total_count: int | None = None):
        self._start_search_results_view()
        self.found_messages.append(message)
        shown_count = max(len(self.found_messages), total_count or 0, getattr(self, "last_results_total_count", 0))
        self.last_results_total_count = shown_count
        self._set_results_title(T.RESULTS_COUNT.format(count=shown_count))


    def _flush_pending_result_messages(self):
        if not self.pending_result_messages:
            self.pending_result_timer.stop()
            return
        self.found_messages.extend(self.pending_result_messages)
        self.pending_result_messages.clear()
        self.pending_result_timer.stop()
        self.last_results_total_count = max(getattr(self, "last_results_total_count", 0), len(self.found_messages))
        self._set_results_title(T.RESULTS_COUNT.format(count=self.last_results_total_count))


    def _finalize_streamed_results_view(self):
        self.pending_result_timer.stop()
        self._flush_pending_result_messages()
        if self.found_messages:
            self._apply_pending_result_filter_mode()
            self._set_result_message_sources(self.found_messages)
            self.unlock_search_controls_after_final_render = True
            self._render_preview_results(self.found_messages, [])
            self._set_results_title(T.RESULTS_COUNT.format(count=len(self.found_messages)))
            return True
        if getattr(self, "search_results_view_started", False):
            self._set_results_scroll_enabled(False)
            self._show_results_placeholder(T.NOTHING_FOUND)
        return False


    def _on_async_progress(self, task_id: int, payload):
        try:
            event_type = payload.get("type")
            if task_id == getattr(self, "active_delete_task_id", None):
                if event_type == "delete_status":
                    self.search_status_label.setText(payload.get("text", T.DELETE_MESSAGES_STATUS))
                return
            if task_id != self.active_search_task_id:
                return
            if getattr(self, "search_stop_requested", False) and task_id == getattr(self, "active_search_task_id", None):
                return
            if event_type == "message":
                self._queue_streamed_message(payload["message"], payload.get("count"))
            elif event_type == "status":
                self._start_search_results_view()
                text = payload.get("text", T.SEARCH_MESSAGES)
                count = payload.get("count", len(self.found_messages))
                processed = payload.get("processed")
                total = payload.get("total")
                status_text = text
                if processed is not None and total:
                    status_text = f"{text}{T.CHECKED_TOTAL_SUFFIX.format(processed=processed, total=total, chat_suffix='')}"
                elif processed is not None:
                    status_text = f"{text}{T.CHECKED_SUFFIX.format(processed=processed, chat_suffix='')}"
                if payload.get("chat_progress"):
                    checked_chats = payload.get("checked_chats")
                    total_chats = payload.get("total_chats")
                    if checked_chats is not None and total_chats:
                        status_text = f"{status_text}{T.CHAT_PROGRESS_SUFFIX.format(checked=checked_chats, total=total_chats)}"
                self.search_status_label.setText(status_text)
                if count is not None:
                    stable_count = max(int(count), len(self.found_messages), getattr(self, "last_results_total_count", 0))
                    self.last_results_total_count = stable_count
                    self._set_results_title(T.RESULTS_COUNT.format(count=stable_count))
        except Exception as exc:
            self._show_error_dialog(T.ERROR_TITLE, str(exc))


    def on_stop_loading(self):
        if getattr(self, "final_results_rendering", False):
            self.stop_loading_button.setEnabled(False)
            self.stop_loading_button.clearFocus()
            return
        if getattr(self, "active_delete_task_id", None) is not None:
            if getattr(self, "delete_stop_requested", False):
                return
            self.delete_stop_requested = True
            self.controller.stop_requested = True
            self.search_status_label.setText(T.STOPPING_DELETION)
            self.stop_loading_button.setEnabled(False)
            self.stop_loading_button.clearFocus()
            return
        if self.active_search_task_id is None or self.search_stop_requested:
            self._show_warning_dialog(T.WARNING_STOP_TITLE, T.WARNING_STOP_NOTHING)
            return
        task_id = self.active_search_task_id
        self.search_stop_requested = True
        self.controller.stop_requested = True
        self.search_status_label.setText(T.STOPPING_LOADING)
        cancelled = self.runner.cancel(task_id)
        if cancelled:
            self.callbacks.pop(task_id, None)
            render_pending = self._finalize_streamed_results_view()
            self._apply_results_mode(self.pending_results_mode)
            self.last_search_export_metadata["loading"] = "stopped"
            self.search_status_label.setText(self._status_with_results_hint(T.LOADING_STOPPED))
            if not render_pending:
                self.active_search_task_id = None
                self.search_stop_requested = False
                self.controller.stop_requested = False
                self._set_search_loading_controls(False)
                self._release_search_input_cursor_refresh_after_status()
                if not self.found_messages:
                    self._set_results_scroll_enabled(False)
                    self._show_results_placeholder(T.NOTHING_FOUND)


    def on_delete(self):
        selected_messages = [message for message in self.found_messages if message.selected]
        if not self.found_messages:
            self._show_warning_dialog(T.WARNING_NO_MESSAGES_TITLE, T.WARNING_NO_MESSAGES_TO_DELETE)
            return
        if not selected_messages:
            self._show_warning_dialog(T.WARNING_NO_SELECTED_TITLE, T.WARNING_NO_SELECTED)
            return
        self.last_delete_had_error = False
        self.last_delete_was_stopped = False
        if self.current_results_mode == "reactions":
            if not self._confirm_dialog(T.CONFIRM_TITLE, T.CONFIRM_DELETE_REACTIONS.format(count=len(selected_messages)), danger_confirm=True):
                return
            self.delete_result_backup = list(getattr(self, "all_found_messages", None) or self.found_messages)
            self.delete_selected_keys = {self._message_delete_key(message) for message in selected_messages}
            self.delete_stop_requested = False
            self.controller.stop_requested = False
            self._show_results_placeholder(T.DELETE_REACTIONS_STATUS)
            self.search_status_label.setText(T.DELETE_REACTIONS_PROGRESS.format(deleted=0, remaining=len(selected_messages), total=len(selected_messages)))
            self._set_search_loading_controls(True)
            if hasattr(self, "sender_filter_combo"):
                self.sender_filter_combo.setEnabled(False)
            self.delete_button.setEnabled(False)
            self.export_results_button.setEnabled(False)
            self.active_delete_task_id = self._run_async_with_progress(
                lambda progress: self.controller.delete_reactions_grouped(selected_messages, progress_callback=progress),
                self._on_reactions_deleted_done,
                self._show_delete_error,
            )
            return
        if not self._confirm_dialog(T.CONFIRM_TITLE, T.CONFIRM_DELETE_MESSAGES.format(count=len(selected_messages)), danger_confirm=True):
            return
        self.delete_result_backup = list(getattr(self, "all_found_messages", None) or self.found_messages)
        self.delete_selected_keys = {self._message_delete_key(message) for message in selected_messages}
        self.delete_stop_requested = False
        self.controller.stop_requested = False
        self._show_results_placeholder(T.DELETE_MESSAGES_STATUS)
        self.search_status_label.setText(T.DELETE_MESSAGES_PROGRESS.format(deleted=0, remaining=len(selected_messages), total=len(selected_messages)))
        self._set_search_loading_controls(True)
        if hasattr(self, "sender_filter_combo"):
            self.sender_filter_combo.setEnabled(False)
        self.delete_button.setEnabled(False)
        self.export_results_button.setEnabled(False)
        self.active_delete_task_id = self._run_async_with_progress(
            lambda progress: self.controller.delete_messages_grouped(selected_messages, self.revoke_checkbox.isChecked(), progress_callback=progress),
            self._on_delete_done,
            self._show_delete_error,
        )


    def _message_delete_key(self, message: FoundMessage) -> tuple[int, int, bool]:
        return (int(getattr(message, "peer_id", 0) or 0), int(getattr(message, "message_id", 0) or 0), bool(getattr(message, "is_reaction", False)))


    def _remaining_messages_after_delete(self, failed_remaining_messages: list[FoundMessage]) -> list[FoundMessage]:
        backup_messages = list(getattr(self, "delete_result_backup", []) or [])
        if not backup_messages:
            return list(failed_remaining_messages or [])
        selected_keys = set(getattr(self, "delete_selected_keys", set()) or set())
        if not selected_keys:
            selected_keys = {self._message_delete_key(message) for message in getattr(self, "found_messages", []) if getattr(message, "selected", False)}
        failed_keys = {self._message_delete_key(message) for message in failed_remaining_messages or []}
        remaining = []
        for message in backup_messages:
            key = self._message_delete_key(message)
            if key not in selected_keys or key in failed_keys:
                remaining.append(message)
        known_keys = {self._message_delete_key(message) for message in remaining}
        for message in failed_remaining_messages or []:
            key = self._message_delete_key(message)
            if key not in known_keys:
                remaining.append(message)
                known_keys.add(key)
        return remaining


    def _show_partial_delete_error(self, deleted_count: int, remaining_count: int):
        self.last_delete_had_error = True
        self.last_delete_was_stopped = False
        self.search_status_label.setText(T.NETWORK_DELETE_RETRY_STATUS)
        message = T.DELETE_PARTIAL_NETWORK.format(deleted=deleted_count, remaining=remaining_count)
        self._show_error_dialog(T.ERROR_DELETE_TITLE, message)


    def _show_delete_stopped_info(self, deleted_count: int, remaining_count: int):
        self.last_delete_was_stopped = True
        self.search_status_label.setText(T.DELETE_STOPPED_TITLE)
        message = T.DELETE_STOPPED_MESSAGE.format(deleted=deleted_count, remaining=remaining_count)
        self._show_info_dialog(T.DELETE_STOPPED_TITLE, message)


    def _lock_controls_until_results_rendered(self):
        self.render_controls_locked = True
        self.unlock_search_controls_after_final_render = True
        self._set_search_loading_controls(True)
        if hasattr(self, "stop_loading_button"):
            self.stop_loading_button.setEnabled(False)
            self.stop_loading_button.clearFocus()
        if hasattr(self, "search_controls_toggle_button"):
            self.search_controls_toggle_button.setEnabled(False)
            self.search_controls_toggle_button.clearFocus()


    def _on_reactions_deleted_done(self, result):
        if len(result) >= 3:
            removed_count, errors, remaining_messages = result
        else:
            removed_count, errors = result
            remaining_messages = []
        stopped = bool(getattr(self, "delete_stop_requested", False))
        remaining_after_delete = self._remaining_messages_after_delete(remaining_messages)
        self.active_delete_task_id = None
        self.delete_stop_requested = False
        self.controller.stop_requested = False
        self.delete_result_backup = []
        self.delete_selected_keys = set()
        self.search_status_label.setText(T.NETWORK_DELETE_RETRY_STATUS if errors else T.SEARCH_READY_STATUS)
        self._apply_results_mode("reactions")
        if remaining_after_delete:
            self._lock_controls_until_results_rendered()
            if stopped:
                self._show_delete_stopped_info(removed_count, len(remaining_messages))
            elif errors:
                self._show_partial_delete_error(removed_count, len(remaining_messages))
            elif removed_count > 0:
                self._show_info_dialog(T.AUTH_READY_TITLE, T.DELETE_SUCCESS_MESSAGE)
            QApplication.processEvents()
            self._set_result_message_sources(remaining_after_delete)
            self._render_preview_results(self.found_messages, [])
            self._set_results_title(T.RESULTS_COUNT.format(count=len(self.found_messages)))
        else:
            self.found_messages = []
            self.all_found_messages = []
            self._reset_sender_filter()
            self._set_results_title(T.SECTION_RESULTS_ZERO)
            self._render_delete_results(removed_count, [] if stopped else errors)
            self._set_search_loading_controls(False)
            self._release_search_input_cursor_refresh_after_status()
        self._update_result_action_buttons()


    def _on_delete_done(self, result):
        if len(result) >= 3:
            deleted_count, errors, remaining_messages = result
        else:
            deleted_count, errors = result
            remaining_messages = []
        stopped = bool(getattr(self, "delete_stop_requested", False))
        remaining_after_delete = self._remaining_messages_after_delete(remaining_messages)
        self.active_delete_task_id = None
        self.delete_stop_requested = False
        self.controller.stop_requested = False
        self.delete_result_backup = []
        self.delete_selected_keys = set()
        self.search_status_label.setText(T.NETWORK_DELETE_RETRY_STATUS if errors else T.SEARCH_READY_STATUS)
        if remaining_after_delete:
            self._lock_controls_until_results_rendered()
            if stopped:
                self._show_delete_stopped_info(deleted_count, len(remaining_messages))
            elif errors:
                self._show_partial_delete_error(deleted_count, len(remaining_messages))
            elif deleted_count > 0:
                self._show_info_dialog(T.AUTH_READY_TITLE, T.DELETE_SUCCESS_MESSAGE)
            QApplication.processEvents()
            self._set_result_message_sources(remaining_after_delete)
            self._render_preview_results(self.found_messages, [])
            self._set_results_title(T.RESULTS_COUNT.format(count=len(self.found_messages)))
        else:
            self.found_messages = []
            self.all_found_messages = []
            self._reset_sender_filter()
            self._set_results_title(T.SECTION_RESULTS_ZERO)
            self._render_delete_results(deleted_count, [] if stopped else errors)
            self._set_search_loading_controls(False)
            self._release_search_input_cursor_refresh_after_status()
        self._update_result_action_buttons()


    def _run_async(self, coro, on_success: Callable, on_error: Callable):
        if self._is_app_closing():
            return None
        task_id = self.runner.submit(coro)
        self.callbacks[task_id] = (on_success, on_error)
        return task_id


    def _run_async_with_progress(self, coro_factory, on_success: Callable, on_error: Callable):
        if self._is_app_closing():
            return None
        task_id = self.runner.submit_with_progress(coro_factory)
        self.callbacks[task_id] = (on_success, on_error)
        return task_id


    def _on_async_completed(self, task_id: int, result, error):
        callbacks = self.callbacks.pop(task_id, None)
        if callbacks is None:
            return
        if self._is_app_closing():
            return
        if task_id == getattr(self, "active_delete_task_id", None):
            self.active_delete_task_id = None
        if self.search_stop_requested and task_id == self.active_search_task_id:
            render_pending = self._finalize_streamed_results_view()
            self._apply_results_mode(self.pending_results_mode)
            self.search_status_label.setText(self._status_with_results_hint(T.LOADING_STOPPED))
            if not render_pending:
                self.active_search_task_id = None
                self.search_stop_requested = False
                self.controller.stop_requested = False
                self._set_search_loading_controls(False)
                self._release_search_input_cursor_refresh_after_status()
                if not self.found_messages:
                    self._set_results_scroll_enabled(False)
                    self._show_results_placeholder(T.NOTHING_FOUND)
            return
        on_success, on_error = callbacks
        try:
            if error is not None:
                on_error(error)
            else:
                on_success(result)
        except Exception as exc:
            self.last_search_export_metadata["loading"] = "stopped"
            self._finalize_streamed_results_view()
            self._show_error_dialog(T.ERROR_TITLE, str(exc))
            self.active_search_task_id = None
            self.search_stop_requested = False
            self.controller.stop_requested = False
            self._set_search_loading_controls(False)
            self._release_search_input_cursor_refresh_after_status()


    def _show_delete_error(self, error: Exception):
        self.active_delete_task_id = None
        self.delete_stop_requested = False
        self.controller.stop_requested = False
        backup_messages = list(getattr(self, "delete_result_backup", []) or [])
        self.delete_result_backup = []
        self.delete_selected_keys = set()
        self.last_delete_had_error = True
        self.last_delete_was_stopped = False
        translated_error = translate_telegram_error(error)
        self.search_status_label.setText(T.NETWORK_DELETE_RETRY_STATUS)
        if backup_messages:
            self._lock_controls_until_results_rendered()
        else:
            self._set_search_loading_controls(False)
            self._release_search_input_cursor_refresh_after_status()
            self._update_result_action_buttons()
        self._show_error_dialog(T.ERROR_DELETE_TITLE, translated_error)
        QApplication.processEvents()
        if backup_messages:
            self._set_result_message_sources(backup_messages)
            self._render_preview_results(self.found_messages, [])
            self._set_results_title(T.RESULTS_COUNT.format(count=len(self.found_messages)))
        else:
            self._set_search_loading_controls(False)
            self._update_result_action_buttons()


    def _is_unhandled_auth_request_error(self, error: Exception) -> bool:
        text = str(error).lower()
        return "request was unsuccessful" in text


    def _is_auth_code_expired_error(self, error: Exception) -> bool:
        text = str(error).lower()
        return "confirmation code has expired" in text or "sign in request" in text or "signinrequest" in text


    def _show_auth_error(self, status: str, error: Exception):
        if self._is_auth_code_expired_error(error):
            self.auth_status_value.setText(T.AUTH_LOGIN_ERROR)
            self.update_auth_controls()
            self._show_error_dialog(T.AUTH_LOGIN_ERROR, T.AUTH_CODE_EXPIRED, copy_text="")
            return
        if self._is_unhandled_auth_request_error(error):
            self.auth_status_value.setText(T.AUTH_LOGIN_ERROR)
            self.update_auth_controls()
            self._show_error_dialog(T.AUTH_LOGIN_ERROR, T.AUTH_TRY_AGAIN, copy_text="")
            return
        self.auth_status_value.setText(status)
        self.update_auth_controls()
        self._show_error_dialog(T.ERROR_TITLE, translate_telegram_error(error))


    def _show_search_error(self, status: str, error: Exception):
        self.pending_result_timer.stop()
        self._flush_pending_result_messages()
        self.active_search_task_id = None
        self.search_stop_requested = False
        self.controller.stop_requested = False
        self.export_results_button.setEnabled(False)
        self.export_results_button.clearFocus()
        self.last_search_export_metadata["loading"] = "stopped"
        translated_error = translate_telegram_error(error)
        final_status = T.NETWORK_SEARCH_RETRY_STATUS if self._is_network_search_error_text(translated_error) else status
        has_messages_to_render = bool(self.found_messages)
        if has_messages_to_render:
            self._lock_controls_until_results_rendered()
        else:
            self._set_search_loading_controls(False)
            self._release_search_input_cursor_refresh_after_status()
        self._show_error_dialog(T.ERROR_TITLE, translated_error)
        self.search_status_label.setText(final_status)
        QApplication.processEvents()
        if self.found_messages:
            self._apply_pending_result_filter_mode()
            self._set_result_message_sources(self.found_messages)
            self._render_preview_results(self.found_messages, [])
            self._set_results_title(T.RESULTS_COUNT.format(count=len(self.found_messages)))
        else:
            self.found_messages = []
            self.all_found_messages = []
            self._reset_sender_filter()
            self._set_results_title(T.SECTION_RESULTS_ZERO)
            self._set_results_scroll_enabled(False)
            self._show_results_placeholder(T.NOTHING_FOUND)
            self._update_result_action_buttons()
        self.previous_result_messages_backup = []