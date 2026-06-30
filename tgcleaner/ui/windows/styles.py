class MainWindowStylesMixin:
    def _apply_styles(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #08131C;
                color: #E8F2F8;
                font-family: Segoe UI;
                font-size: 14px;
            }
            QTabWidget,
            QTabWidget::pane,
            QTabBar,
            QStackedWidget,
            QWidget#LoginTab,
            QWidget#SearchTab,
            QWidget#AppBackground {
                background: transparent;
                background-color: transparent;
            }
            QLabel {
                background-color: transparent;
            }
            #Header {
                background-color: #101C27;
                border-bottom: 1px solid #203241;
            }
            #Title {
                color: #FFFFFF;
                font-size: 24px;
                font-weight: 700;
            }
            QTabWidget::pane {
                border: 0;
                margin-top: 0;
            }
            QTabWidget::tab-bar {
                alignment: center;
            }
            QTabBar {
                min-height: 76px;
                max-height: 76px;
            }
            QTabBar::tab {
                background: #17212B;
                color: #AEBAC5;
                padding: 0 24px;
                height: 42px;
                min-width: 175px;
                border: 1px solid #223140;
                border-radius: 21px;
                margin-top: 24px;
                margin-left: 10px;
                margin-right: 10px;
                margin-bottom: 10px;
                outline: none;
            }
            QTabBar::tab:hover {
                background: #1F2C38;
                color: #FFFFFF;
                border: 1px solid #2E4357;
            }
            QTabBar::tab:selected {
                background: #2AABEE;
                color: #FFFFFF;
                border: 1px solid #2AABEE;
            }
            QTabBar::tab:disabled {
                background: #121A22;
                color: #51606D;
                border: 1px solid #1B2631;
            }
            QTabBar::tab:focus {
                border: 1px solid #223140;
                outline: none;
            }
            QTabBar::tab:selected:focus {
                background: #2AABEE;
                border: 1px solid #2AABEE;
                outline: none;
            }
            QTabBar::tab:disabled:focus {
                border: 1px solid #1B2631;
                outline: none;
            }
            #Card {
                background-color: #17212B;
                border: 1px solid #2F4354;
                border-radius: 18px;
            }
            #InnerCard, #StatusBar {
                background-color: #1C2733;
                border: 1px solid #2F4354;
                border-radius: 16px;
            }
            #BoldLabel {
                color: #DDE9F2;
                font-weight: 700;
            }
            #SectionTitle {
                color: #FFFFFF;
                font-size: 16px;
                font-weight: 700;
            }
            #SearchStatusLabel {
                color: #8EA1B1;
                font-size: 13px;
            }
            #SearchControlsFrame {
                background-color: transparent;
                border: 0;
            }
            #CollapseButton {
                background-color: #111A22;
                color: #AFC2D3;
                border: 1px solid #263847;
                border-radius: 9px;
                padding: 0;
                font-size: 12px;
                font-weight: 700;
            }
            #CollapseButton:hover {
                background-color: #1C2733;
                color: #FFFFFF;
                border: 1px solid #3E6485;
            }
            #CollapseButton:pressed {
                background-color: #0D151C;
                border: 1px solid #2AABEE;
            }
            #CollapseButton:focus {
                background-color: #111A22;
                color: #FFFFFF;
                border: 1px solid #5BC8FF;
            }
            #CollapseButton:disabled {
                background-color: #0D151C;
                color: #556675;
                border: 1px solid #1C2A36;
            }
            QComboBox {
                background-color: #111A22;
                color: #E8F2F8;
                border: 1px solid #334657;
                border-radius: 10px;
                padding: 6px 9px;
            }
            QComboBox:disabled {
                background-color: #0F1A23;
                color: #7F93A5;
                border: 1px solid #263848;
            }
            QComboBox:focus {
                border: 1px solid #334657;
            }
            QComboBox[keyboardFocus="true"]:focus {
                border: 1px solid #2AABEE;
            }
            QComboBox::drop-down {
                border: 0;
                width: 22px;
            }
            QComboBox QAbstractItemView {
                background-color: #17212B;
                color: #E8F2F8;
                selection-background-color: #3E6380;
                selection-color: #FFFFFF;
                border: 1px solid #334657;
                outline: none;
                padding: 4px;
            }
            QComboBox QAbstractItemView::item {
                min-height: 30px;
                padding: 5px 8px;
                border-radius: 6px;
                margin: 0;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #223140;
                color: #FFFFFF;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #3E6380;
                color: #FFFFFF;
            }
            QComboBox QAbstractItemView::item:selected:hover {
                background-color: #4A7290;
                color: #FFFFFF;
            }
            QComboBox QAbstractItemView QScrollBar:vertical {
                background: #17212B;
                background-color: #17212B;
                width: 10px;
                margin: 4px 0 4px 0;
                padding: 0;
                border: none;
            }
            QComboBox QAbstractItemView QScrollBar::handle:vertical {
                background: #3D586E;
                border-radius: 4px;
                min-height: 40px;
                margin: 0 1px 0 1px;
                border: none;
            }
            QComboBox QAbstractItemView QScrollBar::handle:vertical:hover {
                background: #5D7D95;
                border: none;
            }
            QComboBox QAbstractItemView QScrollBar::add-line:vertical,
            QComboBox QAbstractItemView QScrollBar::sub-line:vertical,
            QComboBox QAbstractItemView QScrollBar::add-page:vertical,
            QComboBox QAbstractItemView QScrollBar::sub-page:vertical {
                background: #17212B;
                background-color: #17212B;
                border: none;
                width: 0;
                height: 0;
            }
            QLineEdit {
                background-color: #111A22;
                color: #E8F2F8;
                border: 1px solid #334657;
                border-radius: 11px;
                padding: 8px 10px;
                selection-background-color: #2AABEE;
                selection-color: #FFFFFF;
            }
            QLineEdit:focus {
                border: 1px solid #2AABEE;
                background-color: #111A22;
            }
            QPlainTextEdit {
                background-color: #111A22;
                color: #E8F2F8;
                border: 1px solid #334657;
                border-radius: 11px;
                padding: 8px 10px;
                selection-background-color: #2AABEE;
                selection-color: #FFFFFF;
            }
            QPlainTextEdit:focus {
                border: 1px solid #2AABEE;
                background-color: #111A22;
            }
            QPlainTextEdit#TelegramPlainTextEdit {
                padding: 8px 10px;
            }
            #ResultsBodyFrame {
                background-color: transparent;
                border: 0;
            }
            QListWidget#ResultsList {
                background-color: transparent;
                border: 0;
                outline: none;
                padding: 0;
            }
            QListWidget#ResultsList::item {
                background: transparent;
                border: 0;
            }
            QPlainTextEdit#TelegramPlainTextEdit > QWidget {
                background-color: transparent;
                border: 0;
            }
            QPlainTextEdit#TelegramPlainTextEdit:focus > QWidget {
                background-color: transparent;
                border: 0;
            }
            #ResultsPlaceholder {
                color: #8EA1B1;
                font-size: 15px;
                padding: 24px;
            }
            #MessageCard {
                background-color: transparent;
                border: 0;
            }
            #MessageBubble {
                border-radius: 18px;
            }
            #MessageText {
                color: #FFFFFF;
                font-size: 14px;
                line-height: 1.35;
            }
            #MessageInfo {
                color: #DDE9F2;
                font-size: 12px;
                font-weight: 700;
            }
            #MessageMeta, #MatchedTerms {
                color: #9FB1C0;
                font-size: 12px;
            }
            #InfoNotice, #ErrorNotice {
                background-color: #1C2733;
                border: 1px solid #2B4054;
                border-radius: 16px;
            }
            #ErrorNotice {
                background-color: #2A2024;
                border: 1px solid #6F3A46;
            }
            #NoticeTitle {
                color: #FFFFFF;
                font-size: 14px;
                font-weight: 700;
            }
            #NoticeBody {
                color: #C9D6E0;
                font-size: 13px;
            }
            QLineEdit:disabled, QPlainTextEdit:disabled {
                background-color: #0D151C;
                color: #617180;
                border: 1px solid #223140;
            }
            QPushButton {
                background-color: #2AABEE;
                color: #FFFFFF;
                border: 1px solid transparent;
                border-radius: 12px;
                padding: 8px 14px;
                outline: none;
                font-weight: 600;
            }
            QPushButton[keyboardFocus="true"]:focus {
                border: 1px solid #92DDFF;
                background-color: #2AABEE;
                outline: none;
            }
            QPushButton[keyboardFocus="true"]:disabled:focus {
                border: 1px solid #26384A;
                background-color: #17445D;
                outline: none;
            }
            QPushButton:hover {
                background-color: #39B8F3;
            }
            QPushButton[keyboardFocus="true"]:focus:hover {
                background-color: #39B8F3;
                border: 1px solid #92DDFF;
            }
            QPushButton:pressed {
                background-color: #168AC2;
            }
            QPushButton:disabled {
                background-color: #17445D;
                color: #7890A1;
            }
            #SecondaryButton {
                background-color: #223140;
                color: #DDE9F2;
                border: 1px solid #34495C;
                padding: 6px 12px;
            }
            #SecondaryButton:hover {
                background-color: #2E4052;
                border: 1px solid #46647C;
            }
            #SecondaryButton[keyboardFocus="true"]:focus {
                background-color: #223140;
                border: 1px solid #5BC8FF;
            }
            #SecondaryButton[keyboardFocus="true"]:focus:hover {
                background-color: #2E4052;
                border: 1px solid #5BC8FF;
            }
            #SecondaryButton:pressed {
                background-color: #192633;
            }
            #SecondaryButton:disabled {
                background-color: #14202A;
                color: #607382;
                border: 1px solid #263847;
            }
            #DangerButton {
                background-color: #E04F5F;
            }
            #DangerButton:hover {
                background-color: #EF6573;
            }
            #DangerButton[keyboardFocus="true"]:focus {
                border: 1px solid #FFB5BE;
            }
            #DangerButton[keyboardFocus="true"]:focus:hover {
                background-color: #EF6573;
                border: 1px solid #FFB5BE;
            }
            #DangerButton:pressed {
                background-color: #C93E4D;
            }
            #DangerButton:disabled {
                background-color: #5C2730;
                color: #C9939B;
                border: 1px solid #6E333D;
            }
            #DangerButton[keyboardFocus="true"]:disabled:focus {
                background-color: #5C2730;
                color: #C9939B;
                border: 1px solid #7F424C;
            }
            #EyeButton {
                background-color: transparent;
                border: 0;
                padding: 0;
            }
            #EyeButton:hover {
                background-color: transparent;
            }
            QCheckBox {
                spacing: 10px;
                background-color: transparent;
                color: #E8F2F8;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 6px;
                border: 1px solid #385365;
                background-color: #17212B;
            }
            QCheckBox::indicator:hover {
                border: 1px solid #2AABEE;
            }
            QCheckBox::indicator:checked {
                background-color: #2AABEE;
                border: 1px solid #2AABEE;
                image: none;
            }
            QCheckBox::indicator:disabled {
                background-color: #0D151C;
                border: 1px solid #223140;
            }
        """)