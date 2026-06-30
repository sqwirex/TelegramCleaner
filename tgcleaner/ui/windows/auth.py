import re

from PySide6.QtCore import Qt, QTimer
try:
    from telethon.errors import SessionPasswordNeededError
except Exception:
    try:
        from telethon.errors.rpcerrorlist import SessionPasswordNeededError
    except Exception:
        class SessionPasswordNeededError(Exception):
            pass

from PySide6.QtWidgets import (
    QApplication,
    QLineEdit,
    QPlainTextEdit,
)

from tgcleaner.core.config import has_session_file, save_saved_field
from tgcleaner.ui.widgets.cursor import refresh_input_cursors_under_mouse
from tgcleaner.ui.widgets.text_inputs import ProtectedLineEdit
from tgcleaner.core.i18n import T, translate_telegram_error


class MainWindowAuthMixin:
    def _setup_autosave(self):
        self.api_id_entry.textChanged.connect(lambda text: save_saved_field("api_id", text))
        self.api_hash_entry.textChanged.connect(self._on_api_hash_text_changed)
        self.phone_entry.textChanged.connect(lambda text: save_saved_field("phone", text))


    def _on_api_hash_text_changed(self, text: str):
        save_saved_field("api_hash", text)
        self._auto_hide_api_hash_if_needed(text)


    def _looks_like_api_hash(self, text: str) -> bool:
        value = text.strip()
        return bool(
            len(value) == 32
            and re.fullmatch(r"[A-Fa-f0-9]{32}", value)
            and re.search(r"[A-Fa-f]", value)
            and re.search(r"\d", value)
        )


    def _auto_hide_api_hash_if_needed(self, text: str):
        if self.api_hash_entry.hidden_mode or not self._looks_like_api_hash(text):
            return
        self.api_hash_entry.set_hidden_mode(True)
        button = self.eye_buttons.get(self.api_hash_entry)
        if button is not None:
            button.set_hidden_state(True)
            button.update()


    def _auth_line_edits(self):
        return [
            self.api_id_entry,
            self.api_hash_entry,
            self.phone_entry,
            self.code_entry,
            self.password_entry,
        ]


    def _set_initial_values(self):
        self.api_id_entry.setText(self.saved.get("api_id", ""))
        self.api_hash_entry.setText(self.saved.get("api_hash", ""))
        self.phone_entry.setText(self.saved.get("phone", ""))
        self.code_entry.setText("")
        self.password_entry.setText("")
        if hasattr(self, "simple_render_checkbox"):
            checked = str(self.saved.get("simple_render", "0")).strip() == "1"
            self.simple_render_enabled = checked
            self.simple_render_checkbox.blockSignals(True)
            self.simple_render_checkbox.setChecked(checked)
            self.simple_render_checkbox.blockSignals(False)
        self.auth_status_value.setText(T.AUTH_INITIAL)
        self.update_auth_controls()


    def _check_session_on_start(self):
        api_id_raw = self.api_id_entry.text().strip()
        api_hash = self.api_hash_entry.text().strip()
        phone = self.phone_entry.text().strip()
        if not api_id_raw or not api_hash or not phone or not has_session_file(phone):
            return
        try:
            api_id = int(api_id_raw)
        except ValueError:
            return
        self.auth_state = "checking_session"
        self.auth_status_value.setText(T.AUTH_CHECKING_SESSION)
        self.update_auth_controls()
        self._run_async(
            self.controller.check_authorized(api_id, api_hash, phone),
            lambda result: self._on_start_session_checked(result, api_id, api_hash, phone),
            lambda error: self._on_start_session_error(error),
        )


    def _on_start_session_checked(self, result: bool, api_id: int, api_hash: str, phone: str):
        if result:
            self.current_api_id = api_id
            self.current_api_hash = api_hash
            self.current_phone = phone
            self.auth_state = "authorized"
            self.auth_status_value.setText(T.AUTH_SESSION_FOUND.format(phone=phone))
            self.update_auth_controls()
        elif self.auth_state != "initial":
            self.auth_state = "initial"
            self.auth_status_value.setText(T.AUTH_INITIAL)
            self.update_auth_controls()


    def _on_start_session_error(self, error: Exception):
        if self.auth_state != "initial":
            self.auth_state = "initial"
            self.auth_status_value.setText(T.AUTH_INITIAL)
            self.update_auth_controls()
        self._show_error_dialog(T.ERROR_TITLE, translate_telegram_error(error))


    def toggle_secret_field(self, entry: ProtectedLineEdit):
        entry.set_hidden_mode(not entry.hidden_mode)
        button = self.eye_buttons.get(entry)
        if button is not None:
            button.set_hidden_state(entry.hidden_mode)
            button.update()


    def _clear_text_selection_only(self, widget):
        try:
            if isinstance(widget, QLineEdit):
                widget.deselect()
            elif isinstance(widget, QPlainTextEdit):
                cursor = widget.textCursor()
                cursor.clearSelection()
                widget.setTextCursor(cursor)
        except Exception:
            pass


    def _clear_text_widget_selection(self, widget):
        try:
            if isinstance(widget, QLineEdit):
                widget.deselect()
                widget.clearFocus()
            elif isinstance(widget, QPlainTextEdit):
                cursor = widget.textCursor()
                cursor.clearSelection()
                widget.setTextCursor(cursor)
                widget.clearFocus()
        except Exception:
            pass


    def _clear_disabled_input_focus_and_selection(self):
        for widget in (
            self.api_id_entry,
            self.api_hash_entry,
            self.phone_entry,
            self.code_entry,
            self.password_entry,
            self.chats_textbox,
            self.words_textbox,
        ):
            if not widget.isEnabled():
                self._clear_text_widget_selection(widget)


    def _input_cursor_widgets(self):
        return (
            self.api_id_entry,
            self.api_hash_entry,
            self.phone_entry,
            self.code_entry,
            self.password_entry,
            self.chats_textbox,
            self.words_textbox,
        )


    def _refresh_input_cursors_under_mouse(self):
        widgets = self._input_cursor_widgets()
        refresh_input_cursors_under_mouse(widgets)
        QTimer.singleShot(25, lambda: refresh_input_cursors_under_mouse(widgets))
        QTimer.singleShot(100, lambda: refresh_input_cursors_under_mouse(widgets))


    def _is_search_loading(self) -> bool:
        return self.active_search_task_id is not None or getattr(self, "active_delete_task_id", None) is not None


    def _defer_search_input_cursor_refresh(self):
        for widget in (self.chats_textbox, self.words_textbox):
            widget.setProperty("_defer_enabled_cursor_refresh", True)


    def _release_search_input_cursor_refresh(self):
        for widget in (self.chats_textbox, self.words_textbox):
            widget.setProperty("_defer_enabled_cursor_refresh", False)
        self._refresh_input_cursors_under_mouse()


    def _release_search_input_cursor_refresh_after_status(self):
        try:
            self.search_status_label.update()
            self.search_status_label.repaint()
        except Exception:
            pass
        QTimer.singleShot(0, self._release_search_input_cursor_refresh)


    def _update_result_action_buttons(self):
        has_results = bool(self.found_messages)
        loading = self._is_search_loading() or getattr(self, "final_results_rendering", False) or getattr(self, "render_controls_locked", False)
        self.delete_button.setVisible(True)
        self.delete_button.setEnabled(has_results and not loading)
        self.export_results_button.setEnabled(has_results and not loading)
        if hasattr(self, "results_hotkey_hint_label"):
            self.results_hotkey_hint_label.setVisible(True)
        if hasattr(self, "_update_revoke_checkbox_state"):
            self._update_revoke_checkbox_state()


    def _set_search_loading_controls(self, loading: bool):
        rendering_results = getattr(self, "final_results_rendering", False) or getattr(self, "render_controls_locked", False)
        controls_blocked = loading or rendering_results
        if not controls_blocked:
            self._defer_search_input_cursor_refresh()
        else:
            for widget in (self.chats_textbox, self.words_textbox):
                widget.setProperty("_defer_enabled_cursor_refresh", False)
        self.tabs.setTabEnabled(0, not controls_blocked)
        if loading and self.tabs.currentIndex() != 1:
            self.tabs.setCurrentIndex(1)

        for widget in (
            self.chats_textbox,
            self.words_textbox,
            self.all_checkbox,
            self.only_groups_checkbox,
            self.all_messages_checkbox,
            self.reaction_mode_checkbox,
            self.voice_mode_checkbox,
            self.import_chats_button,
            self.import_words_button,
            self.preview_button,
        ):
            widget.setEnabled(not controls_blocked)
        if hasattr(self, "_update_revoke_checkbox_state"):
            self._update_revoke_checkbox_state(controls_blocked)
        self._clear_disabled_input_focus_and_selection()

        if loading and not rendering_results:
            self.stop_loading_button.setEnabled(True)
            if hasattr(self, "search_controls_toggle_button"):
                self.search_controls_toggle_button.setEnabled(False)
        else:
            self.stop_loading_button.setEnabled(False if rendering_results else not controls_blocked)
            if hasattr(self, "search_controls_toggle_button"):
                self.search_controls_toggle_button.setEnabled(False if rendering_results else not controls_blocked)
            if not controls_blocked:
                self.tabs.setTabEnabled(0, True)
                self.update_auth_controls()
        if hasattr(self, "sender_filter_combo"):
            sender_filter_enabled = (not controls_blocked) and bool(getattr(self, "all_found_messages", [])) and self.sender_filter_combo.count() > 1
            self.sender_filter_combo.setEnabled(sender_filter_enabled)
            self.sender_filter_combo.setToolTip("")
        self._update_result_action_buttons()
        if controls_blocked and hasattr(self, "revoke_checkbox"):
            self.revoke_checkbox.setEnabled(False)
            self.revoke_checkbox.clearFocus()

        for checkbox in list(self.result_select_checkboxes):
            try:
                checkbox.setEnabled(not controls_blocked)
            except Exception:
                pass
        if loading:
            self._refresh_input_cursors_under_mouse()


    def _set_search_enabled(self, enabled: bool):
        self.tabs.setTabEnabled(1, enabled)
        for widget in (
            self.chats_textbox,
            self.words_textbox,
            self.all_checkbox,
            self.only_groups_checkbox,
            self.all_messages_checkbox,
            self.preview_button,
            self.delete_button,
            self.stop_loading_button,
            self.results_list,
            self.import_chats_button,
            self.import_words_button,
            self.reaction_mode_checkbox,
            self.voice_mode_checkbox,
        ):
            widget.setEnabled(enabled)
        if hasattr(self, "_refresh_all_mode_visibility"):
            self._refresh_all_mode_visibility()
        if hasattr(self, "search_controls_toggle_button"):
            self.search_controls_toggle_button.setEnabled(enabled)
        self._clear_disabled_input_focus_and_selection()
        if hasattr(self, "_update_revoke_checkbox_state"):
            self._update_revoke_checkbox_state(not enabled)
        self._update_result_action_buttons()
        if enabled:
            self.on_all_mode_changed(self.all_checkbox.isChecked())
            self.on_only_groups_mode_changed(self.only_groups_checkbox.isChecked())
            self._update_all_messages_availability()
        if not enabled and self.tabs.currentIndex() == 1:
            self.tabs.setCurrentIndex(0)
        self._refresh_input_cursors_under_mouse()


    def update_auth_controls(self):
        state = self.auth_state
        for entry in self._auth_line_edits():
            entry.setEnabled(False)
            entry.setCursor(Qt.ArrowCursor)
        if state == "initial":
            for entry in (self.api_id_entry, self.api_hash_entry, self.phone_entry):
                entry.setEnabled(True)
                entry.setCursor(Qt.IBeamCursor)
        elif state == "code_sent":
            self.code_entry.setEnabled(True)
            self.code_entry.setCursor(Qt.IBeamCursor)
        elif state == "password_needed":
            self.password_entry.setEnabled(True)
            self.password_entry.setCursor(Qt.IBeamCursor)
        self._clear_disabled_input_focus_and_selection()
        self.send_code_button.setEnabled(state == "initial")
        self.login_button.setEnabled(state == "code_sent")
        self.password_button.setEnabled(state == "password_needed")
        self.logout_button.setEnabled(state == "authorized")
        self._set_search_enabled(state == "authorized")
        for entry in self._auth_line_edits():
            entry.setCursor(Qt.IBeamCursor if entry.isEnabled() else Qt.ArrowCursor)

        for entry, eye in self.eye_buttons.items():
            eye.setEnabled(True)
            eye.setCursor(Qt.PointingHandCursor)
        self._refresh_input_cursors_under_mouse()


    def _parse_auth_inputs(self) -> tuple[int, str, str]:
        api_id_raw = self.api_id_entry.text().strip()
        api_hash = self.api_hash_entry.text().strip()
        phone = self.phone_entry.text().strip()
        if not api_id_raw:
            raise ValueError(T.AUTH_API_ID_REQUIRED)
        if not api_hash:
            raise ValueError(T.AUTH_API_HASH_REQUIRED)
        if not phone:
            raise ValueError(T.AUTH_PHONE_REQUIRED)
        try:
            api_id = int(api_id_raw)
        except ValueError as exc:
            raise ValueError(T.AUTH_API_ID_NUMBER) from exc
        return api_id, api_hash, phone


    def on_send_code(self):
        try:
            api_id, api_hash, phone = self._parse_auth_inputs()
        except Exception as exc:
            self._show_warning_dialog(T.ERROR_TITLE, str(exc))
            return
        self.auth_status_value.setText(T.AUTH_SENDING_CODE)
        self.send_code_button.setEnabled(False)
        self._run_async(
            self.controller.send_login_code(api_id, api_hash, phone),
            lambda result: self._on_code_sent(api_id, api_hash, phone),
            lambda error: self._show_auth_error(T.AUTH_SEND_CODE_ERROR, error),
        )


    def _on_code_sent(self, api_id: int, api_hash: str, phone: str):
        self.current_api_id = api_id
        self.current_api_hash = api_hash
        self.current_phone = phone
        self.auth_state = "code_sent"
        self.auth_status_value.setText(T.AUTH_CODE_SENT.format(phone=phone))
        self.update_auth_controls()
        self.code_entry.setFocus()
        self.code_entry.deselect()


    def on_login(self):
        if self.current_api_id is None or self.current_api_hash is None or self.current_phone is None:
            try:
                self.current_api_id, self.current_api_hash, self.current_phone = self._parse_auth_inputs()
            except Exception as exc:
                self._show_warning_dialog(T.ERROR_TITLE, str(exc))
                return
        code = self.code_entry.text().strip()
        if not code:
            self._show_warning_dialog(T.ERROR_TITLE, T.AUTH_CODE_REQUIRED)
            return
        self.auth_status_value.setText(T.AUTH_LOGGING_IN)
        self.login_button.setEnabled(False)
        self._run_async(
            self.controller.sign_in_with_code(self.current_api_id, self.current_api_hash, self.current_phone, code),
            lambda result: self._on_authorized(),
            self._on_login_error,
        )


    def _on_login_error(self, error: Exception):
        if isinstance(error, SessionPasswordNeededError):
            self.auth_state = "password_needed"
            self.auth_status_value.setText(T.AUTH_PASSWORD_NEEDED)
            self.update_auth_controls()
            self.password_entry.setFocus()
            self.password_entry.deselect()
            return
        self._show_auth_error(T.AUTH_LOGIN_ERROR, error)


    def on_login_password(self):
        password = self.password_entry.text().strip()
        if not password:
            self._show_warning_dialog(T.ERROR_TITLE, T.AUTH_PASSWORD_REQUIRED)
            return
        self.auth_status_value.setText(T.AUTH_CHECKING_PASSWORD)
        self.password_button.setEnabled(False)
        self._run_async(
            self.controller.sign_in_with_password(self.current_api_id, self.current_api_hash, self.current_phone, password),
            lambda result: self._on_authorized(),
            lambda error: self._show_auth_error(T.AUTH_PASSWORD_LOGIN_ERROR, error),
        )


    def _on_authorized(self):
        self.auth_state = "authorized"
        self.auth_status_value.setText(T.AUTH_LOGIN_DONE.format(phone=self.current_phone))
        self.update_auth_controls()
        focused = QApplication.focusWidget()
        if focused is not None:
            focused.clearFocus()
        self._show_info_dialog(T.AUTH_READY_TITLE, T.AUTH_READY_MESSAGE)


    def on_logout_delete_session(self):
        phone = self.current_phone or self.phone_entry.text().strip()
        if not phone:
            self._show_warning_dialog(T.ERROR_TITLE, T.AUTH_PHONE_NOT_FOUND)
            return
        if not self._confirm_dialog(T.CONFIRM_TITLE, T.AUTH_LOGOUT_CONFIRM, danger_confirm=True):
            return
        self.auth_status_value.setText(T.AUTH_DELETING_SESSION)
        self.logout_button.setEnabled(False)
        self._run_async(
            self.controller.logout_and_delete_session(phone),
            lambda result: self._on_session_deleted(),
            lambda error: self._show_auth_error(T.AUTH_DELETE_SESSION_ERROR, error),
        )


    def _on_session_deleted(self):
        self.auth_state = "initial"
        self.current_api_id = None
        self.current_api_hash = None
        self.current_phone = None
        self.code_entry.setText("")
        self.password_entry.setText("")
        self.auth_status_value.setText(T.AUTH_SESSION_DELETED)
        self.update_auth_controls()


    def _trigger_active_auth_button(self):
        focused = QApplication.focusWidget()
        if not isinstance(focused, QLineEdit):
            return
        if self.send_code_button.isEnabled():
            self.send_code_button.click()
        elif self.login_button.isEnabled():
            self.login_button.click()
        elif self.password_button.isEnabled():
            self.password_button.click()