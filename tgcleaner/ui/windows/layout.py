from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPixmap

from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from tgcleaner.ui.common import RoundedClipFrame
from tgcleaner.ui.widgets.buttons import CollapseToggleButton, EyeToggleButton, NoMouseFocusButton
from tgcleaner.ui.widgets.checkboxes import StyledCheckBox
from tgcleaner.ui.widgets.combo import KeyboardComboBox, ResponsiveStatusLabel
from tgcleaner.ui.widgets.results import ResultsListWidget
from tgcleaner.ui.widgets.text_inputs import ProtectedLineEdit, TelegramPlainTextEdit
from tgcleaner.core.i18n import T, get_language, language_options, set_language, translate_runtime_text
from tgcleaner.core.config import resource_path, save_saved_field


class PatternBackgroundWidget(QWidget):
    _tile_cache = None

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)

    def _tile(self):
        if PatternBackgroundWidget._tile_cache is not None:
            return PatternBackgroundWidget._tile_cache
        tile_size = 120
        loaded_tile = QPixmap(resource_path("assets/background_pattern.svg"))
        if not loaded_tile.isNull():
            PatternBackgroundWidget._tile_cache = loaded_tile.scaled(tile_size, tile_size, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            return PatternBackgroundWidget._tile_cache
        scale = tile_size / 100
        tile = QPixmap(tile_size, tile_size)
        tile.fill(Qt.transparent)
        painter = QPainter(tile)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(24, 58, 84, 28))
        circles = (
            (11, 11, 7), (59, 36, 7), (16, 33, 3), (79, 64, 3),
            (34, 87, 3), (90, 11, 3), (12, 82, 4), (40, 17, 4),
            (63, 5, 5), (57, 66, 4), (86, 87, 5), (32, 58, 5),
            (89, 45, 5), (80, 27, 2), (60, 89, 2), (35, 39, 2),
            (12, 58, 2),
        )
        for x, y, radius in circles:
            cx = x * scale
            cy = y * scale
            r = radius * scale
            painter.drawEllipse(int(cx - r), int(cy - r), int(r * 2), int(r * 2))
        painter.end()
        PatternBackgroundWidget._tile_cache = tile
        return tile

    def paintEvent(self, event):
        painter = QPainter(self)
        gradient = QLinearGradient(0, 0, 0, max(1, self.height()))
        gradient.setColorAt(0.0, QColor("#08131C"))
        gradient.setColorAt(1.0, QColor("#0B1823"))
        painter.fillRect(self.rect(), gradient)
        tile = self._tile()
        tile_width = tile.width()
        tile_height = tile.height()
        y = 0
        while y < self.height():
            x = 0
            while x < self.width():
                painter.drawPixmap(x, y, tile)
                x += tile_width
            y += tile_height
        painter.end()


class MainWindowLayoutMixin:
    def _build_ui(self):
        central = PatternBackgroundWidget()
        central.setFocusPolicy(Qt.StrongFocus)
        self.central_root_widget = central
        self.central_root_widget.setObjectName("AppBackground")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        header = QFrame()
        self.header_frame = header
        header.setObjectName("Header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 10, 16, 10)
        self.title_label = QLabel(T.APP_TITLE)
        self.title_label.setObjectName("Title")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        self.simple_render_checkbox = StyledCheckBox(T.CHECKBOX_SIMPLE_RENDER)
        self.simple_render_checkbox.setMinimumWidth(320)
        self.simple_render_checkbox.setChecked(bool(getattr(self, 'simple_render_enabled', False)))
        header_layout.addWidget(self.simple_render_checkbox, 0, Qt.AlignVCenter)
        self.language_label = QLabel(T.LANGUAGE_LABEL)
        self.language_label.setObjectName("SearchStatusLabel")
        self.language_combo = KeyboardComboBox()
        self.language_combo.setObjectName("HeaderComboBox")
        for code, label in language_options():
            self.language_combo.addItem(label, code)
        language_index = self.language_combo.findData(get_language())
        if language_index >= 0:
            self.language_combo.setCurrentIndex(language_index)
        self.language_combo.setMinimumWidth(128)
        header_layout.addWidget(self.language_label, 0, Qt.AlignVCenter)
        header_layout.addWidget(self.language_combo, 0, Qt.AlignVCenter)
        header_height = max(70, header.sizeHint().height())
        header.setMinimumHeight(header_height)
        header.setMaximumHeight(header_height)
        header.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        root.addWidget(header)
        self.tabs = QTabWidget()
        self.tabs.tabBar().setExpanding(False)
        self.tabs.tabBar().setFixedHeight(76)
        self.tabs.tabBar().setFocusPolicy(Qt.NoFocus)
        root.addWidget(self.tabs, 1)
        self.login_tab = PatternBackgroundWidget()
        self.login_tab.setObjectName("LoginTab")
        self.search_tab = PatternBackgroundWidget()
        self.search_tab.setObjectName("SearchTab")
        self.tabs.addTab(self.login_tab, T.TITLE_AUTH)
        self.tabs.addTab(self.search_tab, T.TITLE_SEARCH_DELETE)
        self.tabs.setTabEnabled(1, False)
        self._build_login_tab()
        self._build_search_tab()
        QTimer.singleShot(0, self._update_centered_card_widths)
        self.language_combo.currentIndexChanged.connect(self.on_language_changed)
        self.simple_render_checkbox.toggled.connect(self.on_simple_render_changed)
        self.tabs.currentChanged.connect(self._update_header_language_visibility)
        self._update_header_language_visibility(self.tabs.currentIndex())


    def _update_header_language_visibility(self, index: int | None = None):
        current_index = self.tabs.currentIndex() if index is None else index
        show_language = current_index == 0
        show_simple_render = current_index == 1
        self.language_label.setVisible(show_language)
        self.language_combo.setVisible(show_language)
        self.simple_render_checkbox.setVisible(show_simple_render)


    def _build_login_tab(self):
        layout = QVBoxLayout(self.login_tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        card = QFrame()
        self.login_card = card
        card.setObjectName("Card")
        card.setMaximumWidth(1080)
        card.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(48, 28, 48, 28)
        card_layout.setSpacing(12)
        form = QGridLayout()
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(10)
        form.setColumnStretch(1, 1)
        self.api_id_entry = self._add_entry_row(form, 0, "API ID", sensitive=False, has_eye=False, label_attr="api_id_label")
        self.api_hash_entry = self._add_entry_row(form, 1, "API HASH", sensitive=True, has_eye=True, hidden=True, label_attr="api_hash_label")
        self.phone_entry = self._add_entry_row(form, 2, T.LABEL_PHONE, sensitive=True, has_eye=True, hidden=False, label_attr="phone_label")
        self.api_id_entry.setPlaceholderText(T.AUTH_API_ID_PLACEHOLDER)
        self.api_hash_entry.setPlaceholderText(T.AUTH_API_HASH_PLACEHOLDER)
        self.phone_entry.setPlaceholderText(T.AUTH_PHONE_PLACEHOLDER)
        self.code_entry = self._add_entry_row(form, 3, T.LABEL_CODE, sensitive=False, has_eye=False, label_attr="code_label")
        self.password_entry = self._add_entry_row(form, 4, T.LABEL_2FA_PASSWORD, sensitive=True, has_eye=True, hidden=True, label_attr="password_label")
        card_layout.addLayout(form)
        self.send_code_button = NoMouseFocusButton(T.BUTTON_SEND_CODE)
        self.login_button = NoMouseFocusButton(T.BUTTON_LOGIN)
        self.password_button = NoMouseFocusButton(T.BUTTON_LOGIN_2FA)
        self.logout_button = NoMouseFocusButton(T.BUTTON_LOGOUT_DELETE_SESSION)
        for button in (self.send_code_button, self.login_button, self.password_button, self.logout_button):
            button.setMinimumHeight(42)
            card_layout.addWidget(button)
        status_bar = QFrame()
        status_bar.setObjectName("StatusBar")
        status_layout = QHBoxLayout(status_bar)
        status_layout.setContentsMargins(12, 10, 12, 10)
        self.auth_status_value = QLabel("—")
        self.auth_status_value.setWordWrap(True)
        self.auth_status_value.setAlignment(Qt.AlignCenter)
        status_layout.addWidget(self.auth_status_value, 1)
        card_layout.addWidget(status_bar)
        layout.addStretch(1)
        layout.addWidget(card, 0, Qt.AlignHCenter)
        layout.setAlignment(card, Qt.AlignHCenter)
        layout.addStretch(1)
        self._update_centered_card_widths()
        self.send_code_button.clicked.connect(self.on_send_code)
        self.login_button.clicked.connect(self.on_login)
        self.password_button.clicked.connect(self.on_login_password)
        self.logout_button.clicked.connect(self.on_logout_delete_session)


    def _add_entry_row(self, form: QGridLayout, row: int, label: str, sensitive: bool, has_eye: bool, hidden: bool = False, label_attr: str | None = None):
        label_widget = QLabel(label)
        label_widget.setObjectName("BoldLabel")
        label_widget.setMinimumWidth(96)
        if label_attr:
            setattr(self, label_attr, label_widget)
        entry = ProtectedLineEdit(sensitive=sensitive)
        entry.setMinimumHeight(38)
        entry.set_hidden_mode(hidden)
        form.addWidget(label_widget, row, 0)
        form.addWidget(entry, row, 1)
        if has_eye:
            eye = EyeToggleButton(hidden)
            eye.clicked.connect(lambda checked=False, target=entry: self.toggle_secret_field(target))
            self.eye_buttons[entry] = eye
            form.addWidget(eye, row, 2, alignment=Qt.AlignCenter)
        else:
            form.setColumnMinimumWidth(2, 34)
        return entry


    def _build_search_tab(self):
        layout = QVBoxLayout(self.search_tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        card = QFrame()
        self.search_card = card
        card.setObjectName("Card")
        card.setMaximumWidth(1080)
        card.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 18, 18, 18)
        card_layout.setSpacing(8)
        self.search_controls_collapsed = False
        self.search_controls_animating = False
        self.search_controls_resized_since_toggle = False
        self.search_controls_frame = QFrame()
        self.search_controls_frame.setObjectName("SearchControlsFrame")
        self.search_controls_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        controls_layout = QVBoxLayout(self.search_controls_frame)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(12)
        top = QHBoxLayout()
        chats_card = QFrame()
        chats_card.setObjectName("InnerCard")
        chats_layout = QVBoxLayout(chats_card)
        chats_header = QHBoxLayout()
        self.chats_label = QLabel(T.SECTION_DIALOGS)
        self.chats_label.setObjectName("SectionTitle")
        self.import_chats_button = NoMouseFocusButton(T.BUTTON_IMPORT_TXT)
        self.import_chats_button.setObjectName("SecondaryButton")
        self.import_chats_button.setMinimumHeight(32)
        self.import_chats_button.setFocusPolicy(Qt.TabFocus)
        self.all_checkbox = StyledCheckBox(T.CHECKBOX_ALL)
        self.all_checkbox.setCompactWidth(True)
        self.only_groups_checkbox = StyledCheckBox(T.CHECKBOX_ONLY_GROUPS)
        self.only_groups_checkbox.setMinimumWidth(140)
        chats_header.addWidget(self.chats_label)
        chats_header.addStretch(1)
        self.chats_hint_text = T.DIALOGS_HINT
        self.chats_textbox = TelegramPlainTextEdit()
        self.chats_textbox.setPlaceholderText(self.chats_hint_text)
        self.chats_textbox.setFixedHeight(92)
        chats_layout.addLayout(chats_header)
        chats_layout.addWidget(self.chats_textbox)
        chats_import_row = QHBoxLayout()
        chats_import_row.setContentsMargins(0, 0, 0, 0)
        chats_import_row.addWidget(self.all_checkbox, 0)
        chats_import_row.addWidget(self.only_groups_checkbox, 0)
        chats_import_row.addStretch(1)
        chats_import_row.addWidget(self.import_chats_button, 0)
        chats_layout.addLayout(chats_import_row)
        words_card = QFrame()
        words_card.setObjectName("InnerCard")
        words_layout = QVBoxLayout(words_card)
        words_header = QHBoxLayout()
        self.words_label = QLabel(T.SECTION_WORDS)
        self.words_label.setObjectName("SectionTitle")
        self.import_words_button = NoMouseFocusButton(T.BUTTON_IMPORT_TXT)
        self.import_words_button.setObjectName("SecondaryButton")
        self.import_words_button.setMinimumHeight(32)
        self.import_words_button.setFocusPolicy(Qt.TabFocus)
        self.all_messages_checkbox = StyledCheckBox(T.CHECKBOX_ALL)
        self.all_messages_checkbox.setMinimumWidth(70)
        words_header.addWidget(self.words_label)
        words_header.addSpacing(8)
        words_header.addWidget(self.all_messages_checkbox, 0)
        words_header.addStretch(1)
        self.words_hint_text = T.WORDS_HINT
        self.words_textbox = TelegramPlainTextEdit()
        self.words_textbox.setPlaceholderText(self.words_hint_text)
        self.words_textbox.setFixedHeight(92)
        words_layout.addLayout(words_header)
        words_layout.addWidget(self.words_textbox)
        self.reaction_mode_checkbox = StyledCheckBox(T.CHECKBOX_REACTIONS)
        self.reaction_mode_checkbox.setMinimumWidth(108)
        self.voice_mode_checkbox = StyledCheckBox(T.CHECKBOX_VOICE)
        self.voice_mode_checkbox.setMinimumWidth(176)
        words_import_row = QHBoxLayout()
        words_import_row.setContentsMargins(0, 0, 0, 0)
        words_import_row.addWidget(self.reaction_mode_checkbox, 0)
        words_import_row.addWidget(self.voice_mode_checkbox, 0)
        words_import_row.addStretch(1)
        words_import_row.addWidget(self.import_words_button, 0)
        words_layout.addLayout(words_import_row)
        top.addWidget(chats_card, 1)
        top.addWidget(words_card, 1)
        controls_layout.addLayout(top)
        self.revoke_checkbox = StyledCheckBox(T.CHECKBOX_REVOKE)
        self.revoke_checkbox.setChecked(True)
        self.revoke_checkbox.setMinimumWidth(170)
        buttons = QHBoxLayout()
        self.preview_button = NoMouseFocusButton(T.BUTTON_FIND)
        self.delete_button = NoMouseFocusButton(T.BUTTON_DELETE_MESSAGES)
        self.stop_loading_button = NoMouseFocusButton(T.BUTTON_STOP_LOADING)
        self.stop_loading_button.setObjectName("SecondaryButton")
        self.delete_button.setObjectName("DangerButton")
        self.preview_button.setMinimumHeight(40)
        self.delete_button.setMinimumHeight(40)
        self.delete_button.setEnabled(False)
        self.stop_loading_button.setMinimumHeight(40)
        self.stop_loading_button.setFocusPolicy(Qt.TabFocus)
        self.stop_loading_button.setCursor(Qt.PointingHandCursor)
        buttons.addWidget(self.preview_button)
        buttons.addWidget(self.stop_loading_button)
        buttons.addWidget(self.delete_button)
        controls_layout.addLayout(buttons)
        card_layout.addWidget(self.search_controls_frame, 0)
        self.search_controls_toggle_button = CollapseToggleButton()
        self.search_controls_toggle_button.clicked.connect(self.toggle_search_controls)
        card_layout.addWidget(self.search_controls_toggle_button, 0, Qt.AlignHCenter)
        result_card = QFrame()
        result_card.setObjectName("InnerCard")
        result_card.setMinimumHeight(0)
        result_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        result_layout = QVBoxLayout(result_card)
        result_layout.setContentsMargins(14, 14, 14, 14)
        result_layout.setSpacing(8)
        results_top_grid = QGridLayout()
        results_top_grid.setContentsMargins(0, 0, 0, 0)
        results_top_grid.setHorizontalSpacing(14)
        results_top_grid.setVerticalSpacing(6)
        self.results_title_label = QLabel(T.SECTION_RESULTS_ZERO)
        self.results_title_label.setObjectName("SectionTitle")
        self.export_results_button = NoMouseFocusButton(T.BUTTON_EXPORT_TXT)
        self.export_results_button.setObjectName("SecondaryButton")
        self.export_results_button.setMinimumHeight(32)
        self.export_results_button.setFocusPolicy(Qt.TabFocus)
        self.export_results_button.setEnabled(True)
        self.search_status_label = ResponsiveStatusLabel(T.SEARCH_READY_STATUS)
        self.search_status_label.setObjectName("SearchStatusLabel")
        self.search_status_label.setMinimumWidth(0)
        self.search_status_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.sender_filter_label = QLabel(T.SENDER_FILTER_LABEL)
        self.sender_filter_label.setObjectName("SearchStatusLabel")
        self.sender_filter_combo = KeyboardComboBox()
        self.sender_filter_combo.setMinimumWidth(170)
        self.sender_filter_combo.setMaximumWidth(240)
        self.sender_filter_combo.setFocusPolicy(Qt.StrongFocus)
        self.sender_filter_combo.setEnabled(False)
        self.sender_filter_combo.addItem(T.SENDER_FILTER_ALL, "__all__")
        sender_filter_row = QHBoxLayout()
        sender_filter_row.setContentsMargins(0, 0, 0, 0)
        sender_filter_row.setSpacing(8)
        sender_filter_row.addWidget(self.sender_filter_label, 0)
        sender_filter_row.addWidget(self.sender_filter_combo, 0)
        sender_filter_row.addStretch(1)
        results_top_grid.addWidget(self.results_title_label, 0, 0, Qt.AlignLeft | Qt.AlignVCenter)
        results_top_grid.addLayout(sender_filter_row, 1, 0)
        results_top_grid.addWidget(self.search_status_label, 0, 1, 2, 1, Qt.AlignRight | Qt.AlignVCenter)
        results_top_grid.setColumnStretch(0, 0)
        results_top_grid.setColumnStretch(1, 8)
        self.results_body_frame = RoundedClipFrame(radius=18, background_color="#07131E", border_color="#3E6485")
        self.results_body_frame.setObjectName("ResultsBodyFrame")
        self.results_body_frame.setMinimumHeight(0)
        self.results_body_frame.setFixedWidth(max(640, self.minimumWidth() - 88))
        self.results_body_frame.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        body_layout = QVBoxLayout(self.results_body_frame)
        body_layout.setContentsMargins(7, 7, 7, 7)
        body_layout.setSpacing(0)
        self.results_list = ResultsListWidget()
        self.results_list.setObjectName("ResultsList")
        self.results_list.setFocusPolicy(Qt.StrongFocus)
        self.results_body_frame.setFocusPolicy(Qt.NoFocus)
        self.results_list.setMinimumHeight(0)
        self.results_list.itemChanged.connect(self._on_results_item_changed)
        self.sender_filter_combo.currentIndexChanged.connect(self.on_sender_filter_changed)
        body_layout.addWidget(self.results_list, 1)
        result_layout.addLayout(results_top_grid)
        results_body_row = QHBoxLayout()
        results_body_row.setContentsMargins(0, 0, 0, 0)
        results_body_row.setSpacing(0)
        results_body_row.addStretch(1)
        results_body_row.addWidget(self.results_body_frame)
        results_body_row.addStretch(1)
        result_layout.addLayout(results_body_row, 1)
        export_row = QGridLayout()
        export_row.setContentsMargins(0, 6, 0, 0)
        export_row.setHorizontalSpacing(10)
        export_row.setVerticalSpacing(0)
        self.results_hotkey_hint_container = QWidget()
        self.results_hotkey_hint_container.setObjectName("TransparentContainer")
        self.results_hotkey_hint_container.setAttribute(Qt.WA_TranslucentBackground, True)
        self.results_hotkey_hint_container.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.results_hotkey_hint_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        results_hotkey_hint_layout = QHBoxLayout(self.results_hotkey_hint_container)
        results_hotkey_hint_layout.setContentsMargins(0, 0, 0, 0)
        results_hotkey_hint_layout.setSpacing(6)
        self.results_hotkey_hint_left_label = QLabel()
        self.results_hotkey_hint_separator_label = QLabel("•")
        self.results_hotkey_hint_right_label = QLabel()
        for label in (self.results_hotkey_hint_left_label, self.results_hotkey_hint_separator_label, self.results_hotkey_hint_right_label):
            label.setObjectName("SearchStatusLabel")
            label.setAttribute(Qt.WA_TranslucentBackground, True)
            label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            label.setStyleSheet("background: transparent;")
        self.results_hotkey_hint_left_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.results_hotkey_hint_separator_label.setAlignment(Qt.AlignCenter)
        self.results_hotkey_hint_right_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        results_hotkey_hint_layout.addWidget(self.results_hotkey_hint_left_label, 1)
        results_hotkey_hint_layout.addWidget(self.results_hotkey_hint_separator_label, 0, Qt.AlignCenter)
        results_hotkey_hint_layout.addWidget(self.results_hotkey_hint_right_label, 1)
        self.results_hotkey_hint_label = self.results_hotkey_hint_container
        self._set_results_hotkey_hint_text(T.RESULTS_HOTKEY_HINT)
        export_row.addWidget(self.results_hotkey_hint_container, 0, 0, 1, 3)
        export_row.addWidget(self.revoke_checkbox, 0, 0, Qt.AlignLeft | Qt.AlignVCenter)
        export_row.addWidget(self.export_results_button, 0, 2, Qt.AlignRight | Qt.AlignVCenter)
        export_row.setColumnStretch(0, 1)
        export_row.setColumnStretch(1, 1)
        export_row.setColumnStretch(2, 1)
        result_layout.addLayout(export_row)
        card_layout.addWidget(result_card, 1)
        card_layout.setStretchFactor(result_card, 1)
        layout.addWidget(card, 1, Qt.AlignHCenter)
        layout.setAlignment(card, Qt.AlignHCenter)
        self._update_centered_card_widths()
        self.preview_button.clicked.connect(self.on_preview)
        self.delete_button.clicked.connect(self.on_delete)
        self.stop_loading_button.clicked.connect(self.on_stop_loading)
        self.import_chats_button.clicked.connect(self.on_import_chats)
        self.import_words_button.clicked.connect(self.on_import_words)
        self.export_results_button.clicked.connect(self.on_export_results)
        self.all_checkbox.toggled.connect(self.on_all_mode_changed)
        self.only_groups_checkbox.toggled.connect(self.on_only_groups_mode_changed)
        self.all_messages_checkbox.toggled.connect(self.on_all_messages_mode_changed)
        self.reaction_mode_checkbox.toggled.connect(self.on_reaction_mode_changed)
        self.voice_mode_checkbox.toggled.connect(self.on_voice_mode_changed)
        self._refresh_all_mode_visibility()
        self._show_results_placeholder(T.RESULTS_EMPTY_PLACEHOLDER)


    def _update_centered_card_widths(self):
        available = max(0, self.width() - 24)
        login_card = getattr(self, "login_card", None)
        if login_card is not None:
            login_card.setFixedWidth(min(1080, max(720, available)))
        search_card = getattr(self, "search_card", None)
        if search_card is not None:
            search_card.setFixedWidth(min(1080, max(936, available)))

    def _set_results_hotkey_hint_text(self, text: str):
        parts = text.split("•", 1)
        left_text = parts[0].strip()
        right_text = parts[1].strip() if len(parts) > 1 else ""
        self.results_hotkey_hint_left_label.setText(left_text)
        self.results_hotkey_hint_separator_label.setText("•" if right_text else "")
        self.results_hotkey_hint_right_label.setText(right_text)



    def on_simple_render_changed(self, checked: bool):
        self.simple_render_enabled = bool(checked)
        save_saved_field('simple_render', '1' if checked else '0')


    def _refresh_language_combo_labels(self):
        current_code = self.language_combo.currentData() or get_language()
        self.language_combo.blockSignals(True)
        self.language_combo.clear()
        for code, label in language_options():
            self.language_combo.addItem(label, code)
        index = self.language_combo.findData(current_code)
        self.language_combo.setCurrentIndex(index if index >= 0 else 0)
        self.language_combo.blockSignals(False)

    def on_language_changed(self, index: int):
        code = self.language_combo.itemData(index) or "en"
        current_status_text = self.search_status_label.text() if hasattr(self, "search_status_label") else ""
        set_language(code)
        save_saved_field("language", code)
        self._pending_translated_status_text = translate_runtime_text(current_status_text)
        self._refresh_language_texts()


    def _refresh_language_texts(self):
        loading = self._is_search_loading() if hasattr(self, "_is_search_loading") else False
        preserved = {}
        if loading:
            for widget_name in (
                "chats_textbox",
                "words_textbox",
                "all_checkbox",
                "only_groups_checkbox",
                "all_messages_checkbox",
                "import_chats_button",
                "import_words_button",
                "preview_button",
                "reaction_mode_checkbox",
                "voice_mode_checkbox",
                "revoke_checkbox",
                "export_results_button",
                "simple_render_checkbox",
            ):
                widget = getattr(self, widget_name, None)
                if widget is None:
                    continue
                checked = widget.isChecked() if hasattr(widget, "isChecked") else None
                preserved[widget_name] = (widget.isEnabled(), checked)
        self.setWindowTitle(T.APP_TITLE)
        self.title_label.setText(T.APP_TITLE)
        self.language_label.setText(T.LANGUAGE_LABEL)
        self._refresh_language_combo_labels()
        self.tabs.setTabText(0, T.TITLE_AUTH)
        self.tabs.setTabText(1, T.TITLE_SEARCH_DELETE)
        self.phone_label.setText(T.LABEL_PHONE)
        self.code_label.setText(T.LABEL_CODE)
        self.password_label.setText(T.LABEL_2FA_PASSWORD)
        self.api_id_entry.setPlaceholderText(T.AUTH_API_ID_PLACEHOLDER)
        self.api_hash_entry.setPlaceholderText(T.AUTH_API_HASH_PLACEHOLDER)
        self.phone_entry.setPlaceholderText(T.AUTH_PHONE_PLACEHOLDER)
        self.send_code_button.setText(T.BUTTON_SEND_CODE)
        self.login_button.setText(T.BUTTON_LOGIN)
        self.password_button.setText(T.BUTTON_LOGIN_2FA)
        self.logout_button.setText(T.BUTTON_LOGOUT_DELETE_SESSION)
        self.chats_label.setText(T.SECTION_DIALOGS)
        self.words_label.setText(T.SECTION_WORDS)
        self.import_chats_button.setText(T.BUTTON_IMPORT_TXT)
        self.import_words_button.setText(T.BUTTON_IMPORT_TXT)
        self.export_results_button.setText(T.BUTTON_EXPORT_TXT)
        self.all_checkbox.setText(T.CHECKBOX_ALL)
        self.only_groups_checkbox.setText(T.CHECKBOX_ONLY_GROUPS)
        self.all_messages_checkbox.setText(T.CHECKBOX_ALL)
        self.reaction_mode_checkbox.setText(T.CHECKBOX_REACTIONS)
        self.voice_mode_checkbox.setText(T.CHECKBOX_VOICE)
        self.revoke_checkbox.setText(T.CHECKBOX_REVOKE)
        self.simple_render_checkbox.setText(T.CHECKBOX_SIMPLE_RENDER)
        self.preview_button.setText(T.BUTTON_FIND)
        self.stop_loading_button.setText(T.BUTTON_STOP_LOADING)
        self._apply_results_mode(getattr(self, "current_results_mode", "messages"))
        self.sender_filter_label.setText(T.SENDER_FILTER_GROUPS_LABEL if getattr(self, "result_filter_mode", "sender") == "chat" else T.SENDER_FILTER_LABEL)
        if hasattr(self, "_refresh_sender_filter_language_items"):
            self._refresh_sender_filter_language_items()
        self._set_results_hotkey_hint_text(T.RESULTS_HOTKEY_HINT)
        self.chats_hint_text = T.DIALOGS_HINT
        self.words_hint_text = T.WORDS_HINT
        self._refresh_all_mode_visibility()
        self._update_dialog_source_mode()
        self.on_all_messages_mode_changed(self.all_messages_checkbox.isChecked())
        loading = self._is_search_loading() if hasattr(self, "_is_search_loading") else False
        if hasattr(self, "all_found_messages") and not loading:
            self._populate_sender_filter()
            self.found_messages = self._filtered_messages_by_sender()
            self._set_results_title(T.RESULTS_COUNT.format(count=len(self.found_messages)) if self.found_messages else T.SECTION_RESULTS_ZERO)
            if hasattr(self, "_refresh_rendered_results_language"):
                self._refresh_rendered_results_language()
        elif loading:
            current_count = max(
                len(getattr(self, "found_messages", [])),
                getattr(self, "last_results_total_count", 0),
            )
            self._set_results_title(T.RESULTS_COUNT.format(count=current_count) if current_count else T.SECTION_RESULTS_ZERO)
            if hasattr(self, "_refresh_sender_filter_language_items"):
                self._refresh_sender_filter_language_items()
            if hasattr(self, "results_list") and getattr(self, "active_search_task_id", None) is not None:
                self._show_results_placeholder(T.LOADING_MESSAGES)
        if not loading and not getattr(self, "found_messages", []):
            self._set_results_title(T.SECTION_RESULTS_ZERO)
            self._reset_sender_filter()
            self._show_results_placeholder(T.RESULTS_EMPTY_PLACEHOLDER)
        if self.auth_state == "initial":
            self.auth_status_value.setText(T.AUTH_INITIAL)
        elif self.auth_state == "checking_session":
            self.auth_status_value.setText(T.AUTH_CHECKING_SESSION)
        elif self.auth_state == "authorized" and self.current_phone:
            self.auth_status_value.setText(T.AUTH_SESSION_FOUND.format(phone=self.current_phone))
        elif self.auth_state == "code_sent" and self.current_phone:
            self.auth_status_value.setText(T.AUTH_CODE_SENT.format(phone=self.current_phone))
        elif self.auth_state == "password_needed":
            self.auth_status_value.setText(T.AUTH_PASSWORD_NEEDED)
        pending_status_text = getattr(self, "_pending_translated_status_text", None)
        if pending_status_text:
            self.search_status_label.setText(pending_status_text)
            self._pending_translated_status_text = None
        elif not loading and not getattr(self, "found_messages", []):
            self.search_status_label.setText(T.SEARCH_READY_STATUS)
        if loading:
            for widget_name, state in preserved.items():
                widget = getattr(self, widget_name, None)
                if widget is None:
                    continue
                enabled, checked = state
                if checked is not None and hasattr(widget, "setChecked"):
                    widget.blockSignals(True)
                    widget.setChecked(checked)
                    widget.blockSignals(False)
                widget.setEnabled(enabled)


    def _reset_search_toggle_mouse_state(self):
        button = getattr(self, "search_controls_toggle_button", None)
        if button is None:
            return
        button.setDown(False)
        button._mouse_pressed = False
        button._last_trigger_by_mouse = True
        button._suppress_hover = True
        button.clearFocus()
        if hasattr(self, "central_root_widget"):
            self.central_root_widget.setFocus(Qt.OtherFocusReason)
        button.update()


    def _sync_search_controls_after_resize(self):
        frame = getattr(self, "search_controls_frame", None)
        button = getattr(self, "search_controls_toggle_button", None)
        if frame is None or button is None:
            return
        animation = getattr(self, "search_controls_animation", None)
        if animation is not None and animation.state() == QPropertyAnimation.Running:
            return
        self.search_controls_animating = False
        if getattr(self, "search_controls_collapsed", False):
            frame.setVisible(True)
            frame.setEnabled(False)
            frame.setMinimumHeight(0)
            frame.setMaximumHeight(0)
        else:
            frame.setVisible(True)
            frame.setEnabled(True)
            frame.setMinimumHeight(0)
            frame.setMaximumHeight(16777215)
        button.setEnabled(not self._is_search_loading() and not getattr(self, "final_results_rendering", False))
        button.set_collapsed_state(getattr(self, "search_controls_collapsed", False))
        self._reset_search_toggle_mouse_state()


    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_centered_card_widths()
        if hasattr(self, "search_controls_toggle_button"):
            self.search_controls_resized_since_toggle = True
            self._reset_search_toggle_mouse_state()
            QTimer.singleShot(0, self._sync_search_controls_after_resize)
            QTimer.singleShot(30, self._sync_search_controls_after_resize)


    def _search_controls_expanded_height(self):
        frame = getattr(self, "search_controls_frame", None)
        if frame is None:
            return 1
        was_visible = frame.isVisible()
        old_enabled = frame.isEnabled()
        old_maximum = frame.maximumHeight()
        old_minimum = frame.minimumHeight()
        if not was_visible:
            frame.setVisible(True)
        frame.setEnabled(True)
        frame.setMinimumHeight(0)
        frame.setMaximumHeight(16777215)
        frame.updateGeometry()
        layout = frame.layout()
        height = frame.sizeHint().height()
        if layout is not None:
            height = max(height, layout.sizeHint().height())
        frame.setMinimumHeight(old_minimum)
        if getattr(self, "search_controls_collapsed", False):
            frame.setMinimumHeight(0)
            frame.setMaximumHeight(0)
            frame.setVisible(True)
        else:
            frame.setMaximumHeight(old_maximum if old_maximum > 0 else 16777215)
            frame.setVisible(True)
        frame.setEnabled(old_enabled)
        frame.updateGeometry()
        return max(1, height)


    def toggle_search_controls(self):
        if self._is_search_loading() or getattr(self, "final_results_rendering", False):
            return
        if getattr(self, "search_controls_resized_since_toggle", False):
            animation = getattr(self, "search_controls_animation", None)
            if animation is not None and animation.state() == QPropertyAnimation.Running:
                animation.stop()
            self.search_controls_animating = False
            self.search_controls_resized_since_toggle = False
            if self.search_controls_collapsed:
                self.search_controls_frame.setVisible(True)
                self.search_controls_frame.setEnabled(False)
                self.search_controls_frame.setMinimumHeight(0)
                self.search_controls_frame.setMaximumHeight(0)
            else:
                self.search_controls_frame.setVisible(True)
                self.search_controls_frame.setEnabled(True)
                self.search_controls_frame.setMinimumHeight(0)
                self.search_controls_frame.setMaximumHeight(16777215)
        if self.search_controls_animating:
            animation = getattr(self, "search_controls_animation", None)
            if animation is not None and animation.state() == QPropertyAnimation.Running:
                return
            self.search_controls_animating = False
            self.search_controls_toggle_button.setEnabled(True)
        toggle_button = self.search_controls_toggle_button
        trigger_by_mouse = getattr(toggle_button, "_last_trigger_by_mouse", False)
        toggle_button.setDown(False)
        toggle_button._mouse_pressed = False
        toggle_button._suppress_hover = bool(trigger_by_mouse)
        restore_toggle_focus = toggle_button.hasFocus() and not trigger_by_mouse
        self.search_controls_animating = True
        toggle_button.clearFocus()
        if hasattr(self, "central_root_widget"):
            self.central_root_widget.setFocus(Qt.OtherFocusReason)
        else:
            self.setFocus(Qt.OtherFocusReason)
        expanded_height = self._search_controls_expanded_height()
        start_height = self.search_controls_frame.height() if self.search_controls_frame.isVisible() else 0
        target_collapsed = not self.search_controls_collapsed
        if self.search_controls_collapsed:
            self.search_controls_frame.setVisible(True)
            self.search_controls_frame.setEnabled(True)
            self.search_controls_frame.setMinimumHeight(0)
            self.search_controls_frame.setMaximumHeight(0)
            start_height = 0
            end_height = expanded_height
        else:
            self.search_controls_frame.setMinimumHeight(0)
            end_height = 0
        has_results = hasattr(self, "results_list") and self.results_list.count() > 1
        self.search_controls_animation = QPropertyAnimation(self.search_controls_frame, b"maximumHeight", self)
        duration = 180 if has_results else 260
        if hasattr(self, "results_list") and hasattr(self.results_list, "begin_controls_resize_transition"):
            self.results_list.begin_controls_resize_transition(duration + 120)
        self.search_controls_animation.setDuration(duration)
        self.search_controls_animation.setStartValue(start_height)
        self.search_controls_animation.setEndValue(end_height)
        self.search_controls_animation.setEasingCurve(QEasingCurve.InOutCubic)
        finished = False
        def finish():
            nonlocal finished
            if finished:
                return
            finished = True
            self.search_controls_animating = False
            self.search_controls_collapsed = target_collapsed
            if self.search_controls_collapsed:
                self.search_controls_frame.setVisible(True)
                self.search_controls_frame.setEnabled(False)
                self.search_controls_frame.setMinimumHeight(0)
                self.search_controls_frame.setMaximumHeight(0)
            else:
                self.search_controls_frame.setVisible(True)
                self.search_controls_frame.setEnabled(True)
                self.search_controls_frame.setMinimumHeight(0)
                self.search_controls_frame.setMaximumHeight(16777215)
            toggle_button.setDown(False)
            toggle_button._mouse_pressed = False
            toggle_button._suppress_hover = bool(getattr(toggle_button, "_last_trigger_by_mouse", False))
            toggle_button.set_collapsed_state(self.search_controls_collapsed)
            toggle_button.setEnabled(not self._is_search_loading() and not getattr(self, "final_results_rendering", False))
            if restore_toggle_focus and toggle_button.isEnabled():
                toggle_button._last_trigger_by_mouse = False
                toggle_button.setFocus(Qt.TabFocusReason)
            else:
                toggle_button._last_trigger_by_mouse = True
                toggle_button.clearFocus()
                if hasattr(self, "central_root_widget"):
                    self.central_root_widget.setFocus(Qt.OtherFocusReason)
                QTimer.singleShot(0, toggle_button.clearFocus)
                QTimer.singleShot(30, toggle_button.clearFocus)
            toggle_button.update()
            if hasattr(self, "results_list") and hasattr(self.results_list, "finish_controls_resize_transition"):
                self.results_list.finish_controls_resize_transition()
        self.search_controls_animation.finished.connect(finish)
        QTimer.singleShot(duration + 80, finish)
        self.search_controls_animation.start()