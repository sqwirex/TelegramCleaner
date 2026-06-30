import re

class T:
    APP_TITLE = 'Telegram Cleaner'
    AUTH_INITIAL = 'Enter API ID, API HASH, phone number and click "Send code".'
    AUTH_CHECKING_SESSION = 'Checking saved Telegram session...'
    AUTH_SESSION_FOUND = 'Session found. Account is already authorized for {phone}.'
    AUTH_API_ID_REQUIRED = 'Enter API ID.'
    AUTH_API_HASH_REQUIRED = 'Enter API HASH.'
    AUTH_PHONE_REQUIRED = 'Enter phone number.'
    AUTH_API_ID_NUMBER = 'API ID must be a number.'
    AUTH_SENDING_CODE = 'Sending code...'
    AUTH_CODE_SENT = 'Code sent for {phone}. Enter the code from Telegram.'
    AUTH_CODE_REQUIRED = 'Enter the code from Telegram.'
    AUTH_LOGGING_IN = 'Logging in...'
    AUTH_PASSWORD_NEEDED = '2FA password is required. Enter the password and click "Log in with 2FA".'
    AUTH_PASSWORD_REQUIRED = 'Enter 2FA password.'
    AUTH_CHECKING_PASSWORD = 'Checking 2FA password...'
    AUTH_LOGIN_DONE = 'Logged in for {phone}.'
    AUTH_READY_TITLE = 'Done'
    AUTH_READY_MESSAGE = 'Telegram account is authorized.'
    AUTH_PHONE_NOT_FOUND = 'Current phone number was not found.'
    AUTH_LOGOUT_CONFIRM = 'Log out and delete the current session?'
    AUTH_DELETING_SESSION = 'Deleting current session...'
    AUTH_SESSION_DELETED = 'Session deleted.'
    AUTH_SEND_CODE_ERROR = 'Code sending error.'
    AUTH_LOGIN_ERROR = 'Login error'
    AUTH_CODE_EXPIRED = 'The confirmation code has expired. Send the code again.'
    AUTH_TRY_AGAIN = 'Try again'
    AUTH_PASSWORD_LOGIN_ERROR = '2FA login error.'
    AUTH_DELETE_SESSION_ERROR = 'Session deletion error.'
    TITLE_AUTH = 'Authorization'
    TITLE_SEARCH_DELETE = 'Search and delete'
    LANGUAGE_LABEL = 'Language'
    LANGUAGE_RUSSIAN = 'Русский'
    LANGUAGE_ENGLISH = 'English'
    SENDER_FILTER_LABEL = 'Messages'
    SENDER_FILTER_GROUPS_LABEL = 'Groups'
    SENDER_FILTER_ALL = 'All'
    SENDER_FILTER_YOU = 'You'
    LABEL_PHONE = 'Phone'
    LABEL_CODE = 'Code'
    LABEL_2FA_PASSWORD = '2FA password'
    AUTH_API_ID_PLACEHOLDER = 'Example: 12345678'
    AUTH_API_HASH_PLACEHOLDER = 'Example: 0123456789abcdef0123456789abcdef'
    AUTH_PHONE_PLACEHOLDER = 'Example: +79991234567'
    BUTTON_SEND_CODE = 'Send code'
    BUTTON_LOGIN = 'Log in'
    BUTTON_LOGIN_2FA = 'Log in with 2FA'
    BUTTON_LOGOUT_DELETE_SESSION = 'Log out and delete current session'
    SECTION_DIALOGS = 'Dialogs'
    SECTION_WORDS = 'Words and phrases'
    SECTION_RESULTS_ZERO = 'Found messages: 0'
    BUTTON_IMPORT_TXT = 'Import TXT'
    BUTTON_EXPORT_TXT = 'Export CSV'
    CHECKBOX_ALL = 'All'
    CHECKBOX_ONLY_GROUPS = 'Groups only'
    CHECKBOX_REACTIONS = 'Reactions'
    CHECKBOX_VOICE = 'Voices and Rounds'
    CHECKBOX_REVOKE = 'Delete for everyone'
    CHECKBOX_SIMPLE_RENDER = 'Simplified render (speeds up loading)'
    SIMPLE_RENDER_RECOMMEND_TITLE = 'Large result list'
    SIMPLE_RENDER_RECOMMEND_MESSAGE = 'More than 5000 messages were found. Enable simplified render to display them faster?'
    RESULTS_HOTKEY_HINT = 'Ctrl+A — select all • Ctrl+D — clear selection'
    BUTTON_FIND = 'Find'
    BUTTON_DELETE_MESSAGES = 'Delete messages'
    BUTTON_DELETE_REACTIONS = 'Delete reactions'
    BUTTON_STOP_LOADING = 'Stop'
    SEARCH_READY_STATUS = 'Click "Find" to load'
    STARTING_LOADING = 'Starting loading...'
    NETWORK_SEARCH_RETRY_STATUS = 'Loading stopped because of an error'
    NETWORK_DELETE_RETRY_STATUS = 'Deletion stopped because of an error'
    RESULTS_EMPTY_PLACEHOLDER = 'Found messages will appear here'
    DIALOGS_HINT = 'One dialog per line.\nSupported: private dialogs, groups, supergroups and topics.\nExamples: @username, link, topic link, ID, -100ID'
    WORDS_HINT = 'One word or phrase per line.\nA word without quotes is a non-exact search.\nA word in quotes is an exact search: "needed phrase"'
    DIALOGS_ALL_PLACEHOLDER = 'All mode is enabled: dialogs field is ignored'
    DIALOGS_ONLY_GROUPS_PLACEHOLDER = 'Groups only mode is enabled: dialogs field is ignored'
    WORDS_ALL_PLACEHOLDER = 'All mode is enabled: words field is ignored'
    ERROR_TITLE = 'Error'
    ERROR_STATUS = 'Error'
    CONFIRM_TITLE = 'Confirmation'
    YES = 'Yes'
    NO = 'No'
    WARNING_STOP_TITLE = 'Stop'
    WARNING_STOP_NOTHING = 'There is nothing to stop right now.'
    WARNING_NO_MESSAGES_TITLE = 'No messages'
    WARNING_NO_MESSAGES_TO_DELETE = 'Click "Find" first to check the list.'
    WARNING_NO_MESSAGES_TO_EXPORT = 'Nothing to export.'
    WARNING_NO_SELECTED_TITLE = 'No selected messages'
    WARNING_NO_SELECTED = 'Select at least one message with the checkbox.'
    ERROR_READ_TXT = 'Failed to read TXT file.'
    ERROR_DELETE_TITLE = 'Deletion error'
    NOTHING_FOUND = 'Nothing found'
    DELETE_SUCCESS_MESSAGE = 'Messages successfully deleted'
    DELETE_PARTIAL_NETWORK = 'Deleted messages: {deleted}\nNot deleted: {remaining}\nTry again'
    EXPORT_DONE = 'Export saved to file:\n{path}'
    EXPORT_SAVE_TITLE = 'Save export'
    EXPORT_METADATA_TOTAL_MESSAGES = 'Total messages'
    EXPORT_METADATA_WORDS_NAME = 'Words and phrases'
    EXPORT_METADATA_DIALOGS_NAME = 'Dialogs'
    EXPORT_METADATA_FILTER_NAME = 'Filter'
    EXPORT_METADATA_REACTIONS_NAME = 'Reactions mode'
    EXPORT_METADATA_VOICE_NAME = 'Voice mode'
    EXPORT_METADATA_LOADING_NAME = 'Loading stopped'
    EXPORT_METADATA_DELETE_ERROR_NAME = 'Deletion error'
    EXPORT_METADATA_DELETE_STOPPED_NAME = 'Deletion stopped'
    EXPORT_SAVE_ERROR_TITLE = 'Could not save export file'
    EXPORT_SAVE_PERMISSION_ERROR = 'Close the open CSV file and try again.'
    EXPORT_METADATA_WORDS = 'Words: {value}'
    EXPORT_METADATA_DIALOGS = 'Dialogs: {value}'
    EXPORT_METADATA_LOADING = 'Loading: {value}'
    EXPORT_METADATA_LOADING_COMPLETED = 'completed'
    EXPORT_METADATA_LOADING_STOPPED = 'stopped'
    EXPORT_METADATA_ENABLED = '{name}: on'
    EXPORT_METADATA_DISABLED = '{name}: off'
    EXPORT_FILE_PREFIX = 'export'
    TXT_FILTER = 'Text files (*.txt);;All files (*.*)'
    CSV_FILTER = 'CSV files (*.csv);;All files (*.*)'
    IMPORT_DIALOGS_TITLE = 'Import dialogs from TXT'
    IMPORT_WORDS_TITLE = 'Import words and phrases from TXT'
    SEARCH_CHATS_REQUIRED = 'Specify at least one dialog or enable "All" / "Groups only" near dialogs.'
    SEARCH_WORDS_REQUIRED = 'Specify at least one word or phrase.'
    SEARCH_WORDS_REQUIRED_ADMIN = 'Specify at least one word or phrase, or enable messages "All" mode.'
    SEARCH_ALL_WORDS_REQUIRES_MODE = 'You can use words "All" mode only with "Reactions", "Voices and Rounds", or "Groups only" enabled.'
    TELEGRAM_SEARCHING_REACTIONS_CHAT = 'Searching reactions: {chat}'
    SEARCH_MESSAGES = 'Searching messages...'
    LOADING_MESSAGES = 'Loading messages, results will appear here after loading finishes or stops'
    RENDERING_MESSAGES = 'Displaying messages...'
    RESIZING_RESULTS = 'Resizing window...'
    STOPPING_LOADING = 'Stopping...'
    LOADING_STOPPED = 'Loading stopped'
    DELETE_REACTIONS_STATUS = 'Deleting reactions...'
    DELETE_MESSAGES_PROGRESS = 'Deleting messages: {remaining} left'
    DELETE_REACTIONS_PROGRESS = 'Deleting reactions: {remaining} left'
    STOPPING_DELETION = 'Stopping deletion...'
    DELETE_STOPPED_TITLE = 'Deletion stopped'
    DELETE_STOPPED_MESSAGE = 'Deletion stopped.\nDeleted: {deleted}\nNot deleted: {remaining}'
    DELETE_MESSAGES_STATUS = 'Deleting messages...'
    DONE_STATUS = 'Done'
    STOPPED_STATUS = 'Stopped'
    CHECKED_CHATS_SUFFIX = ' • {checked}/{total} chats processed'
    CHAT_SUFFIX = ' • chat: {index}/{total}'
    CHAT_PROGRESS_SUFFIX = ' • chats: {checked}/{total}'
    CHECKED_TOTAL_SUFFIX = ' • checked: {processed}/{total}{chat_suffix}'
    CHECKED_SUFFIX = ' • checked: {processed}{chat_suffix}'
    RESULTS_COUNT = 'Found messages: {count}'
    CONFIRM_DELETE_REACTIONS = 'Delete your reactions from selected messages: {count}?'
    CONFIRM_DELETE_MESSAGES = 'Delete selected messages: {count}?'
    EXPORT_REACTIONS_TITLE = 'Found reactions'
    EXPORT_MESSAGES_TITLE = 'Found messages'
    EXPORT_DIALOG = 'Dialog: {value}'
    EXPORT_DIALOG_TYPE = 'Dialog type: {value}'
    EXPORT_DATE = 'Date: {value}'
    EXPORT_FOUND_BY = 'Found by: {value}'
    EXPORT_MESSAGE_TYPE = 'Message type: {value}'
    EXPORT_SENDER = 'From: {value}'
    EXPORT_TEXT = 'Text'
    EXPORT_GROUP = 'group'
    EXPORT_SUPERGROUP = 'supergroup'
    EXPORT_PRIVATE_DIALOG = 'private dialog'
    EXPORT_DIALOG_PREFIX = 'dialog'
    MENU_UNDO = 'Undo'
    MENU_REDO = 'Redo'
    MENU_CUT = 'Cut'
    MENU_COPY = 'Copy'
    MENU_PASTE = 'Paste'
    MENU_DELETE = 'Delete'
    MENU_SELECT_ALL = 'Select all'
    CONTENT_TEXT = 'text'
    CONTENT_SERVICE = 'service message'
    CONTENT_ALBUM = 'album'
    CONTENT_ANIMATED_EMOJI = 'animated emoji'
    CONTENT_GAME = 'game'
    CONTENT_INVOICE = 'invoice'
    CONTENT_PAID_MEDIA = 'paid media'
    CONTENT_GIVEAWAY = 'giveaway'
    CONTENT_GIVEAWAY_RESULTS = 'giveaway results'
    CONTENT_STORY = 'story'
    CONTENT_MEDIA = 'media message'
    CONTENT_TODO = 'todo list'
    CONTENT_POLL = 'poll'
    CONTENT_QUIZ = 'quiz poll'
    CONTENT_CONTACT = 'contact'
    CONTENT_VENUE = 'venue'
    CONTENT_LIVE_GEO = 'live location'
    CONTENT_GEO = 'location'
    CONTENT_VOICE = 'voice message'
    CONTENT_ROUND = 'round video'
    CONTENT_STICKER = 'sticker'
    CONTENT_LINK = 'link'
    CONTENT_PHOTO = 'photo'
    CONTENT_VIDEO = 'video'
    CONTENT_AUDIO = 'audio'
    CONTENT_FILE = 'file'
    CONTENT_REACTION_NO_TEXT = '[reaction to message without text]'
    CONTENT_MESSAGE_NO_TEXT = '[message without text]'
    CONTENT_MESSAGE_LABEL = 'message'
    CONTENT_WITHOUT_TEXT_SUFFIX = ' without text]'
    CONTENT_REACTION_ON_PREFIX = '[reaction to '
    CONTENT_VOICE_NO_TRANSCRIPT = '[voice or round video without transcription text]'
    CONTENT_UNKNOWN = 'Unknown'
    CONTENT_UNKNOWN_CHAT = 'Unknown chat'
    CONTENT_YOU = 'You'
    TELEGRAM_SESSION_REJECTED = "Telegram rejected the current session. Delete this number's session file in the users folder and log in again."
    TELEGRAM_CHAT_ID_NOT_FOUND = 'Dialog with this ID was not found among chats available to the account.'
    TELEGRAM_UNSUPPORTED_DIALOG_TYPE = 'This app supports only private dialogs, groups and supergroups.'
    TELEGRAM_ONLY_GROUPS_TITLE = 'Only groups'
    TELEGRAM_ALL_TITLE = 'All'
    TELEGRAM_STATUS_CHAT_ID = 'chat ID {chat_id}'
    TELEGRAM_TOPIC_ID = 'topic ID {topic_id}'
    TELEGRAM_TRANSCRIBING_ID = 'Transcribing voice or round video ID {message_id}'
    TELEGRAM_TRANSCRIPTION_FAILED = 'Failed to transcribe voice or round video ID {message_id}: {error}'
    TELEGRAM_CHECKING_REACTIONS = 'Checking reactions: {checked}/{total}'
    TELEGRAM_CHECKED_REACTIONS = 'Checked reactions: {checked}/{total}'
    TELEGRAM_CHECKING_VOICE = 'Checking voices and rounds: {checked}/{total}'
    TELEGRAM_CHECKED_VOICE = 'Checked voices and rounds: {checked}/{total}'
    TELEGRAM_LOADING_MESSAGES = 'Loading messages: {checked}/{total}'
    TELEGRAM_LOADED_MESSAGES = 'Loaded messages: {checked}/{total}'
    TELEGRAM_SEARCHING_WORD = 'Searching messages: {checked}/{total}'
    TELEGRAM_CHECKED_WORD = 'Checked messages: {checked}/{total}'
    TELEGRAM_SEARCHING = 'Searching: {checked}/{total}'
    TELEGRAM_CHAT_CHECKED = 'Checked chat: {checked}/{total}'
    TELEGRAM_CHAT_ERROR = 'Chat error: {chat}: {error}'
    TELEGRAM_CHAT_ERROR_CHAT = 'Chat error: {chat}'
    TELEGRAM_CHAT_CHECKED_CHAT = 'Checked chat: {chat}'
    TELEGRAM_SEARCHING_CHAT = 'Searching: {chat}'
    TELEGRAM_CHECKED_WORD_CHAT = 'Checked messages: {chat}'
    TELEGRAM_SEARCHING_WORD_CHAT = 'Searching messages: {chat}'
    TELEGRAM_SEARCHING_MESSAGE_CHAT = 'Searching messages: {chat}'
    TELEGRAM_SEARCHING_MESSAGES_CHAT = 'Searching messages: {chat}'
    TELEGRAM_CHECKED_MESSAGE_CHAT = 'Checked messages: {chat}'
    TELEGRAM_CHECKED_MESSAGES_CHAT = 'Checked messages: {chat}'
    TELEGRAM_LOADED_MESSAGES_CHAT = 'Loaded messages: {chat}'
    TELEGRAM_LOADING_MESSAGES_CHAT = 'Loading messages: {chat}'
    TELEGRAM_CHECKED_VOICE_CHAT = 'Checked voices and rounds: {chat}'
    TELEGRAM_CHECKING_VOICE_CHAT = 'Checking voices and rounds: {chat}'
    TELEGRAM_CHECKED_REACTIONS_CHAT = 'Checked reactions: {chat}'
    TELEGRAM_CHECKING_REACTIONS_CHAT = 'Checking reactions: {chat}'
    TELEGRAM_ERROR_INVALID_API = 'Invalid API ID and API HASH pair.'
    TELEGRAM_ERROR_INVALID_PHONE = 'Phone number is invalid. Enter it in international format.'
    TELEGRAM_ERROR_INVALID_CODE = 'Invalid Telegram code.'
    TELEGRAM_ERROR_INVALID_PASSWORD = 'Invalid 2FA password.'
    TELEGRAM_ERROR_NETWORK = 'Connection error. Check your internet and try again.'
    TELEGRAM_ERROR_FLOOD_WAIT = 'Telegram temporarily limited requests. Try again in {seconds} sec.'
    TELEGRAM_ERROR_ENTITY_NOT_FOUND = 'Could not find the dialog. Check username, link or ID.'
    BUTTON_COPY_ERROR = 'Copy'


_EN_TRANSLATIONS = {name: value for name, value in T.__dict__.items() if name.isupper() and isinstance(value, str)}

_RU_TRANSLATIONS = {
    'APP_TITLE': 'Telegram Cleaner',
    'AUTH_INITIAL': 'Введи API ID, API HASH, телефон и нажми «Отправить код».',
    'AUTH_CHECKING_SESSION': 'Проверяю сохранённую Telegram-сессию...',
    'AUTH_SESSION_FOUND': 'Сессия найдена. Аккаунт уже авторизован для {phone}.',
    'AUTH_API_ID_REQUIRED': 'Введи API ID.',
    'AUTH_API_HASH_REQUIRED': 'Введи API HASH.',
    'AUTH_PHONE_REQUIRED': 'Введи номер телефона.',
    'AUTH_API_ID_NUMBER': 'API ID должен быть числом.',
    'AUTH_SENDING_CODE': 'Отправляю код...',
    'AUTH_CODE_SENT': 'Код отправлен для {phone}. Введи код из Telegram.',
    'AUTH_CODE_REQUIRED': 'Введи код из Telegram.',
    'AUTH_LOGGING_IN': 'Выполняю вход...',
    'AUTH_PASSWORD_NEEDED': 'Нужен пароль 2FA. Введи пароль и нажми «Войти с 2FA».',
    'AUTH_PASSWORD_REQUIRED': 'Введи пароль 2FA.',
    'AUTH_CHECKING_PASSWORD': 'Проверяю пароль 2FA...',
    'AUTH_LOGIN_DONE': 'Вход выполнен для {phone}.',
    'AUTH_READY_TITLE': 'Готово',
    'AUTH_READY_MESSAGE': 'Аккаунт Telegram авторизован.',
    'AUTH_PHONE_NOT_FOUND': 'Не найден текущий номер телефона.',
    'AUTH_LOGOUT_CONFIRM': 'Выйти и удалить текущую session?',
    'AUTH_DELETING_SESSION': 'Удаляю текущую session...',
    'AUTH_SESSION_DELETED': 'Session удалена.',
    'AUTH_SEND_CODE_ERROR': 'Ошибка отправки кода.',
    'AUTH_LOGIN_ERROR': 'Ошибка входа',
    'AUTH_CODE_EXPIRED': 'Код подтверждения истек. Отправьте код снова.',
    'AUTH_TRY_AGAIN': 'Попробуйте снова',
    'AUTH_PASSWORD_LOGIN_ERROR': 'Ошибка входа с 2FA.',
    'AUTH_DELETE_SESSION_ERROR': 'Ошибка удаления session.',
    'TITLE_AUTH': 'Авторизация',
    'TITLE_SEARCH_DELETE': 'Поиск и удаление',
    'LANGUAGE_LABEL': 'Язык',
    'LANGUAGE_RUSSIAN': 'Русский',
    'LANGUAGE_ENGLISH': 'English',
    'SENDER_FILTER_LABEL': 'Сообщения',
    'SENDER_FILTER_GROUPS_LABEL': 'Группы',
    'SENDER_FILTER_ALL': 'Все',
    'SENDER_FILTER_YOU': 'Вы',
    'LABEL_PHONE': 'Телефон',
    'LABEL_CODE': 'Код',
    'LABEL_2FA_PASSWORD': '2FA пароль',
    'AUTH_API_ID_PLACEHOLDER': 'Пример: 12345678',
    'AUTH_API_HASH_PLACEHOLDER': 'Пример: 0123456789abcdef0123456789abcdef',
    'AUTH_PHONE_PLACEHOLDER': 'Пример: +79991234567',
    'BUTTON_SEND_CODE': 'Отправить код',
    'BUTTON_LOGIN': 'Войти',
    'BUTTON_LOGIN_2FA': 'Войти с 2FA',
    'BUTTON_LOGOUT_DELETE_SESSION': 'Выйти и удалить текущую сессию',
    'SECTION_DIALOGS': 'Диалоги',
    'SECTION_WORDS': 'Слова и фразы',
    'SECTION_RESULTS_ZERO': 'Найденные сообщения: 0',
    'BUTTON_IMPORT_TXT': 'Импорт TXT',
    'BUTTON_EXPORT_TXT': 'Экспорт CSV',
    'CHECKBOX_ALL': 'Все',
    'CHECKBOX_ONLY_GROUPS': 'Только группы',
    'CHECKBOX_REACTIONS': 'Реакции',
    'CHECKBOX_VOICE': 'Голосовые и кружки',
    'CHECKBOX_REVOKE': 'Удалить для всех',
    'CHECKBOX_SIMPLE_RENDER': 'Упрощенный рендер (ускоряет загрузку)',
    'SIMPLE_RENDER_RECOMMEND_TITLE': 'Много сообщений',
    'SIMPLE_RENDER_RECOMMEND_MESSAGE': 'Найдено больше 5000 сообщений. Включить упрощенный рендер, чтобы отобразить их быстрее?',
    'RESULTS_HOTKEY_HINT': 'Ctrl+A — выделить все • Ctrl+D — снять выделение',
    'BUTTON_FIND': 'Найти',
    'BUTTON_DELETE_MESSAGES': 'Удалить сообщения',
    'BUTTON_DELETE_REACTIONS': 'Удалить реакции',
    'BUTTON_STOP_LOADING': 'Остановить',
    'SEARCH_READY_STATUS': 'Нажми «Найти» для загрузки',
    'STARTING_LOADING': 'Начинаю загрузку...',
    'NETWORK_SEARCH_RETRY_STATUS': 'Загрузка остановлена из-за ошибки',
    'NETWORK_DELETE_RETRY_STATUS': 'Удаление остановлено из-за ошибки',
    'RESULTS_EMPTY_PLACEHOLDER': 'Здесь появятся найденные сообщения',
    'DIALOGS_HINT': 'По одному диалогу на строку.\nПоддерживаются: личные диалоги, группы, супергруппы и топики.\nПримеры: @username, ссылка, ссылка на топик, ID, -100ID',
    'WORDS_HINT': 'По одному слову или фразе на строку.\nСлово без кавычек — неточный поиск.\nСлово в кавычках — точный поиск: "нужная фраза"',
    'DIALOGS_ALL_PLACEHOLDER': 'Включён режим «Все»: поле диалогов игнорируется',
    'DIALOGS_ONLY_GROUPS_PLACEHOLDER': 'Включён режим «Только группы»: поле диалогов игнорируется',
    'WORDS_ALL_PLACEHOLDER': 'Включён режим «Все»: поле слов игнорируется',
    'ERROR_TITLE': 'Ошибка',
    'ERROR_STATUS': 'Ошибка',
    'CONFIRM_TITLE': 'Подтверждение',
    'YES': 'Да',
    'NO': 'Нет',
    'WARNING_STOP_TITLE': 'Остановка',
    'WARNING_STOP_NOTHING': 'Сейчас нечего останавливать.',
    'WARNING_NO_MESSAGES_TITLE': 'Нет сообщений',
    'WARNING_NO_MESSAGES_TO_DELETE': 'Сначала нажми «Найти», чтобы проверить список.',
    'WARNING_NO_MESSAGES_TO_EXPORT': 'Нечего экспортировать.',
    'WARNING_NO_SELECTED_TITLE': 'Нет выбранных сообщений',
    'WARNING_NO_SELECTED': 'Отметь хотя бы одно сообщение галочкой.',
    'ERROR_READ_TXT': 'Не удалось прочитать TXT-файл.',
    'ERROR_DELETE_TITLE': 'Ошибка удаления',
    'NOTHING_FOUND': 'Ничего не найдено',
    'DELETE_SUCCESS_MESSAGE': 'Сообщения успешно удалены',
    'DELETE_PARTIAL_NETWORK': 'Удалено сообщений: {deleted}\nНе удалено: {remaining}\nПопробуйте снова',
    'EXPORT_DONE': 'Экспорт сохранен в файл:\n{path}',
    'EXPORT_SAVE_TITLE': 'Сохранить экспорт',
    'EXPORT_METADATA_TOTAL_MESSAGES': 'Всего сообщений',
    'EXPORT_METADATA_WORDS_NAME': 'Слова и фразы',
    'EXPORT_METADATA_DIALOGS_NAME': 'Диалоги',
    'EXPORT_METADATA_FILTER_NAME': 'Фильтр',
    'EXPORT_METADATA_REACTIONS_NAME': 'Режим реакций',
    'EXPORT_METADATA_VOICE_NAME': 'Режим голосовых',
    'EXPORT_METADATA_LOADING_NAME': 'Загрузка остановлена',
    'EXPORT_METADATA_DELETE_ERROR_NAME': 'Ошибка удаления',
    'EXPORT_METADATA_DELETE_STOPPED_NAME': 'Удаление остановлено',
    'EXPORT_SAVE_ERROR_TITLE': 'Не удалось сохранить файл экспорта',
    'EXPORT_SAVE_PERMISSION_ERROR': 'Закройте открытый CSV-файл и попробуйте снова.',
    'EXPORT_METADATA_WORDS': 'Слова: {value}',
    'EXPORT_METADATA_DIALOGS': 'Диалоги: {value}',
    'EXPORT_METADATA_LOADING': 'Загрузка: {value}',
    'EXPORT_METADATA_LOADING_COMPLETED': 'завершена',
    'EXPORT_METADATA_LOADING_STOPPED': 'остановлена',
    'EXPORT_METADATA_ENABLED': '{name}: включено',
    'EXPORT_METADATA_DISABLED': '{name}: выключено',
    'EXPORT_FILE_PREFIX': 'экспорт',
    'TXT_FILTER': 'Text files (*.txt);;All files (*.*)',
    'CSV_FILTER': 'CSV-файлы (*.csv);;Все файлы (*.*)',
    'IMPORT_DIALOGS_TITLE': 'Импорт диалогов из TXT',
    'IMPORT_WORDS_TITLE': 'Импорт слов и фраз из TXT',
    'SEARCH_CHATS_REQUIRED': 'Укажи хотя бы один диалог или включи «Все» / «Только группы» рядом с диалогами.',
    'SEARCH_WORDS_REQUIRED': 'Укажи хотя бы одно слово или фразу.',
    'SEARCH_WORDS_REQUIRED_ADMIN': 'Укажи хотя бы одно слово или фразу или включи режим «Все» у сообщений.',
    'SEARCH_ALL_WORDS_REQUIRES_MODE': 'Режим «Все» у слов можно использовать только с включёнными «Реакции», «Голосовые и кружки» или «Только группы».',
    'TELEGRAM_SEARCHING_REACTIONS_CHAT': 'Ищу реакции: {chat}',
    'SEARCH_MESSAGES': 'Ищу сообщения...',
    'LOADING_MESSAGES': 'Загружаю сообщения, они появятся здесь после завершения или остановки загрузки',
    'RENDERING_MESSAGES': 'Отображаю сообщения...',
    'RESIZING_RESULTS': 'Меняется размер окна...',
    'STOPPING_LOADING': 'Останавливаю...',
    'LOADING_STOPPED': 'Загрузка остановлена',
    'DELETE_REACTIONS_STATUS': 'Удаляю реакции...',
    'DELETE_MESSAGES_PROGRESS': 'Удаляю сообщения: осталось {remaining}',
    'DELETE_REACTIONS_PROGRESS': 'Удаляю реакции: осталось {remaining}',
    'STOPPING_DELETION': 'Останавливаю удаление...',
    'DELETE_STOPPED_TITLE': 'Удаление остановлено',
    'DELETE_STOPPED_MESSAGE': 'Удаление остановлено.\nУдалено: {deleted}\nНе удалено: {remaining}',
    'DELETE_MESSAGES_STATUS': 'Удаляю сообщения...',
    'DONE_STATUS': 'Завершено',
    'STOPPED_STATUS': 'Остановлено',
    'CHECKED_CHATS_SUFFIX': ' • {checked}/{total} чатов обработано',
    'CHAT_SUFFIX': ' • чат: {index}/{total}',
    'CHAT_PROGRESS_SUFFIX': ' • чаты: {checked}/{total}',
    'CHECKED_TOTAL_SUFFIX': ' • проверено: {processed}/{total}{chat_suffix}',
    'CHECKED_SUFFIX': ' • проверено: {processed}{chat_suffix}',
    'RESULTS_COUNT': 'Найденные сообщения: {count}',
    'CONFIRM_DELETE_REACTIONS': 'Удалить твои реакции с выбранных сообщений: {count} шт.?',
    'CONFIRM_DELETE_MESSAGES': 'Удалить выбранные сообщения: {count} шт.?',
    'EXPORT_REACTIONS_TITLE': 'Найденные реакции',
    'EXPORT_MESSAGES_TITLE': 'Найденные сообщения',
    'EXPORT_DIALOG': 'Диалог: {value}',
    'EXPORT_DIALOG_TYPE': 'Тип диалога: {value}',
    'EXPORT_DATE': 'Дата: {value}',
    'EXPORT_FOUND_BY': 'Найдено по: {value}',
    'EXPORT_MESSAGE_TYPE': 'Тип сообщения: {value}',
    'EXPORT_SENDER': 'От: {value}',
    'EXPORT_TEXT': 'Текст',
    'EXPORT_GROUP': 'группа',
    'EXPORT_SUPERGROUP': 'супергруппа',
    'EXPORT_PRIVATE_DIALOG': 'личный диалог',
    'EXPORT_DIALOG_PREFIX': 'диалог',
    'MENU_UNDO': 'Отменить',
    'MENU_REDO': 'Повторить',
    'MENU_CUT': 'Вырезать',
    'MENU_COPY': 'Копировать',
    'MENU_PASTE': 'Вставить',
    'MENU_DELETE': 'Удалить',
    'MENU_SELECT_ALL': 'Выделить всё',
    'CONTENT_TEXT': 'текст',
    'CONTENT_SERVICE': 'служебное сообщение',
    'CONTENT_ALBUM': 'альбом',
    'CONTENT_ANIMATED_EMOJI': 'анимированный эмодзи',
    'CONTENT_GAME': 'игра',
    'CONTENT_INVOICE': 'инвойс',
    'CONTENT_PAID_MEDIA': 'платное медиа',
    'CONTENT_GIVEAWAY': 'розыгрыш',
    'CONTENT_GIVEAWAY_RESULTS': 'результаты розыгрыша',
    'CONTENT_STORY': 'история',
    'CONTENT_MEDIA': 'медиа-сообщение',
    'CONTENT_TODO': 'список задач',
    'CONTENT_POLL': 'опрос',
    'CONTENT_QUIZ': 'опрос-викторина',
    'CONTENT_CONTACT': 'контакт',
    'CONTENT_VENUE': 'место',
    'CONTENT_LIVE_GEO': 'live-геопозиция',
    'CONTENT_GEO': 'геопозиция',
    'CONTENT_VOICE': 'голосовое сообщение',
    'CONTENT_ROUND': 'кружок',
    'CONTENT_STICKER': 'стикер',
    'CONTENT_LINK': 'ссылка',
    'CONTENT_PHOTO': 'фото',
    'CONTENT_VIDEO': 'видео',
    'CONTENT_AUDIO': 'аудио',
    'CONTENT_FILE': 'файл',
    'CONTENT_REACTION_NO_TEXT': '[реакция на сообщение без текста]',
    'CONTENT_MESSAGE_NO_TEXT': '[сообщение без текста]',
    'CONTENT_MESSAGE_LABEL': 'сообщение',
    'CONTENT_WITHOUT_TEXT_SUFFIX': ' без текста]',
    'CONTENT_REACTION_ON_PREFIX': '[реакция на ',
    'CONTENT_VOICE_NO_TRANSCRIPT': '[голосовое или кружок без текста транскрибации]',
    'CONTENT_UNKNOWN': 'Неизвестно',
    'CONTENT_UNKNOWN_CHAT': 'Неизвестный чат',
    'CONTENT_YOU': 'Вы',
    'TELEGRAM_SESSION_REJECTED': 'Telegram отклонил текущую session. Удали session-файл этого номера в папке users и войди заново.',
    'TELEGRAM_CHAT_ID_NOT_FOUND': 'Диалог с таким ID не найден среди доступных аккаунту чатов.',
    'TELEGRAM_UNSUPPORTED_DIALOG_TYPE': 'Приложение поддерживает только личные диалоги, группы и супергруппы.',
    'TELEGRAM_ONLY_GROUPS_TITLE': 'Только группы',
    'TELEGRAM_ALL_TITLE': 'Все',
    'TELEGRAM_STATUS_CHAT_ID': 'чат ID {chat_id}',
    'TELEGRAM_TOPIC_ID': 'топик ID {topic_id}',
    'TELEGRAM_TRANSCRIBING_ID': 'Транскрибирую голосовое или кружок ID {message_id}',
    'TELEGRAM_TRANSCRIPTION_FAILED': 'Не удалось транскрибировать голосовое или кружок ID {message_id}: {error}',
    'TELEGRAM_CHECKING_REACTIONS': 'Проверяю реакции: {checked}/{total}',
    'TELEGRAM_CHECKED_REACTIONS': 'Проверены реакции: {checked}/{total}',
    'TELEGRAM_CHECKING_VOICE': 'Проверяю голосовые и кружки: {checked}/{total}',
    'TELEGRAM_CHECKED_VOICE': 'Проверены голосовые и кружки: {checked}/{total}',
    'TELEGRAM_LOADING_MESSAGES': 'Загружаю сообщения: {checked}/{total}',
    'TELEGRAM_LOADED_MESSAGES': 'Загружены сообщения: {checked}/{total}',
    'TELEGRAM_SEARCHING_WORD': 'Ищу сообщения: {checked}/{total}',
    'TELEGRAM_CHECKED_WORD': 'Проверены сообщения: {checked}/{total}',
    'TELEGRAM_SEARCHING': 'Ищу: {checked}/{total}',
    'TELEGRAM_CHAT_CHECKED': 'Проверен чат: {checked}/{total}',
    'TELEGRAM_CHAT_ERROR': 'Ошибка в чате: {chat}: {error}',
    'TELEGRAM_CHAT_ERROR_CHAT': 'Ошибка в чате: {chat}',
    'TELEGRAM_CHAT_CHECKED_CHAT': 'Проверен чат: {chat}',
    'TELEGRAM_SEARCHING_CHAT': 'Ищу: {chat}',
    'TELEGRAM_CHECKED_WORD_CHAT': 'Проверены сообщения: {chat}',
    'TELEGRAM_SEARCHING_WORD_CHAT': 'Ищу сообщения: {chat}',
    'TELEGRAM_SEARCHING_MESSAGE_CHAT': 'Ищу сообщения: {chat}',
    'TELEGRAM_SEARCHING_MESSAGES_CHAT': 'Ищу сообщения: {chat}',
    'TELEGRAM_CHECKED_MESSAGE_CHAT': 'Проверены сообщения: {chat}',
    'TELEGRAM_CHECKED_MESSAGES_CHAT': 'Проверены сообщения: {chat}',
    'TELEGRAM_LOADED_MESSAGES_CHAT': 'Загружены сообщения: {chat}',
    'TELEGRAM_LOADING_MESSAGES_CHAT': 'Загружаю сообщения: {chat}',
    'TELEGRAM_CHECKED_VOICE_CHAT': 'Проверены голосовые и кружки: {chat}',
    'TELEGRAM_CHECKING_VOICE_CHAT': 'Проверяю голосовые и кружки: {chat}',
    'TELEGRAM_CHECKED_REACTIONS_CHAT': 'Проверены реакции: {chat}',
    'TELEGRAM_CHECKING_REACTIONS_CHAT': 'Проверяю реакции: {chat}',
    'TELEGRAM_ERROR_INVALID_API': 'Неверная связка API ID и API HASH.',
    'TELEGRAM_ERROR_INVALID_PHONE': 'Номер телефона некорректный. Введи его в международном формате.',
    'TELEGRAM_ERROR_INVALID_CODE': 'Неверный код из Telegram.',
    'TELEGRAM_ERROR_INVALID_PASSWORD': 'Неверный пароль 2FA.',
    'TELEGRAM_ERROR_NETWORK': 'Ошибка соединения. Проверь интернет и попробуй снова.',
    'TELEGRAM_ERROR_FLOOD_WAIT': 'Telegram временно ограничил запросы. Попробуй снова через {seconds} сек.',
    'TELEGRAM_ERROR_ENTITY_NOT_FOUND': 'Не удалось найти диалог. Проверь username, ссылку или ID.',
    'BUTTON_COPY_ERROR': 'Копировать',
}


_LANGUAGE_TRANSLATIONS = {
    "en": _EN_TRANSLATIONS,
    "ru": _RU_TRANSLATIONS,
}

_LANGUAGE_LABEL_KEYS = {
    "en": "LANGUAGE_ENGLISH",
    "ru": "LANGUAGE_RUSSIAN",
}

_CURRENT_LANGUAGE = "en"


def set_language(code: str) -> str:
    global _CURRENT_LANGUAGE
    selected = code if code in _LANGUAGE_TRANSLATIONS else "en"
    source = _LANGUAGE_TRANSLATIONS[selected]
    for name, value in _EN_TRANSLATIONS.items():
        setattr(T, name, source.get(name, value))
    _CURRENT_LANGUAGE = selected
    return _CURRENT_LANGUAGE


def get_language() -> str:
    return _CURRENT_LANGUAGE


def language_options() -> list[tuple[str, str]]:
    return [(code, _LANGUAGE_TRANSLATIONS[code].get(key, code)) for code, key in _LANGUAGE_LABEL_KEYS.items()]


def get_flood_wait_seconds(error: Exception | str) -> int | None:
    seconds = getattr(error, "seconds", None)
    try:
        seconds_value = int(seconds)
        if seconds_value > 0:
            return seconds_value
    except Exception:
        pass
    text = str(error or "")
    patterns = (
        r"FLOOD_WAIT[_ ](\d+)",
        r"wait of (\d+) seconds",
        r"wait (\d+) seconds",
        r"retry after (\d+) seconds",
        r"try again in (\d+) sec",
        r"попробуй снова через (\d+) сек",
        r"подожд(?:и|ите) (\d+) сек",
        r"через (\d+) сек",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                value = int(match.group(1))
                if value > 0:
                    return value
            except Exception:
                pass
    return None


def is_flood_wait_error(error: Exception | str) -> bool:
    return get_flood_wait_seconds(error) is not None


def format_flood_wait_error(seconds: int) -> str:
    return T.TELEGRAM_ERROR_FLOOD_WAIT.format(seconds=seconds)


def translate_telegram_error(error: Exception) -> str:
    flood_wait_seconds = get_flood_wait_seconds(error)
    if flood_wait_seconds is not None:
        return format_flood_wait_error(flood_wait_seconds)
    text = str(error)
    lowered = text.lower()
    if "api id/api hash combination is invalid" in lowered or "api_id/api_hash" in lowered:
        return T.TELEGRAM_ERROR_INVALID_API
    if "phone number is invalid" in lowered:
        return T.TELEGRAM_ERROR_INVALID_PHONE
    if "phone code entered was invalid" in lowered or "phone code is invalid" in lowered:
        return T.TELEGRAM_ERROR_INVALID_CODE
    if "password" in lowered and "invalid" in lowered and "checkpasswordrequest" in lowered:
        return T.TELEGRAM_ERROR_INVALID_PASSWORD
    if "password" in lowered and "invalid" in lowered:
        return T.TELEGRAM_ERROR_INVALID_PASSWORD
    entity_not_found_markers = (
        "cannot find any entity corresponding to",
        "could not find the input entity",
        "no user has",
        "nobody is using this username",
        "username is unacceptable",
        "resolveusernamerequest",
        "usernamenotoccupiederror",
        "username_not_occupied",
        "usernameinvaliderror",
        "username_invalid",
    )
    if any(marker in lowered for marker in entity_not_found_markers):
        return T.TELEGRAM_ERROR_ENTITY_NOT_FOUND
    if "telegram отклонил текущую session" in lowered or "auth key unregistered" in lowered or "authkeyunregistered" in lowered or "auth_key_unregistered" in lowered:
        return T.TELEGRAM_SESSION_REJECTED
    if "database disk image is malformed" in lowered or "file is not a database" in lowered or "not a database" in lowered or "sqlite" in lowered and "session" in lowered:
        return T.TELEGRAM_SESSION_REJECTED
    network_markers = [
        "timed out",
        "timeout",
        "connection",
        "network",
        "disconnected",
        "disconnect",
        "winerror",
        "unreachable",
        "0 bytes read",
        "expected bytes",
        "incompleteread",
        "incomplete read",
        "eof",
        "server disconnected",
        "connectionreseterror",
        "connection reset",
        "connection lost",
        "socket",
        "transport",
        "ошибка соединения",
        "telegram не отвечает",
    ]
    if any(marker in lowered for marker in network_markers):
        return T.TELEGRAM_ERROR_NETWORK
    return text

_CONTENT_KIND_KEYS = [
    "CONTENT_TEXT",
    "CONTENT_SERVICE",
    "CONTENT_ALBUM",
    "CONTENT_ANIMATED_EMOJI",
    "CONTENT_GAME",
    "CONTENT_INVOICE",
    "CONTENT_PAID_MEDIA",
    "CONTENT_GIVEAWAY",
    "CONTENT_GIVEAWAY_RESULTS",
    "CONTENT_STORY",
    "CONTENT_MEDIA",
    "CONTENT_TODO",
    "CONTENT_POLL",
    "CONTENT_QUIZ",
    "CONTENT_CONTACT",
    "CONTENT_VENUE",
    "CONTENT_LIVE_GEO",
    "CONTENT_GEO",
    "CONTENT_VOICE",
    "CONTENT_ROUND",
    "CONTENT_STICKER",
    "CONTENT_LINK",
    "CONTENT_PHOTO",
    "CONTENT_VIDEO",
    "CONTENT_AUDIO",
    "CONTENT_FILE",
]

def _all_translation_values(key: str) -> set[str]:
    return {translations.get(key, "") for translations in _LANGUAGE_TRANSLATIONS.values() if translations.get(key)}


def translate_content_kind(value: str) -> str:
    text = str(value or "")
    for key in _CONTENT_KIND_KEYS:
        if text in _all_translation_values(key):
            return getattr(T, key)
    return text


_RUNTIME_TEXT_KEYS = [
    "SEARCH_READY_STATUS",
    "STARTING_LOADING",
    "NETWORK_SEARCH_RETRY_STATUS",
    "NETWORK_DELETE_RETRY_STATUS",
    "NOTHING_FOUND",
    "LOADING_MESSAGES",
    "RENDERING_MESSAGES",
    "RESIZING_RESULTS",
    "STOPPING_LOADING",
    "LOADING_STOPPED",
    "DELETE_REACTIONS_STATUS",
    "DELETE_MESSAGES_STATUS",
    "DELETE_MESSAGES_PROGRESS",
    "DELETE_REACTIONS_PROGRESS",
    "STOPPING_DELETION",
    "DELETE_STOPPED_TITLE",
    "DELETE_STOPPED_MESSAGE",
    "DONE_STATUS",
    "STOPPED_STATUS",
    "CHECKED_CHATS_SUFFIX",
    "CHAT_SUFFIX",
    "CHAT_PROGRESS_SUFFIX",
    "CHECKED_TOTAL_SUFFIX",
    "CHECKED_SUFFIX",
    "RESULTS_HOTKEY_HINT",
    "TELEGRAM_TOPIC_ID",
    "TELEGRAM_STATUS_CHAT_ID",
    "TELEGRAM_TRANSCRIBING_ID",
    "TELEGRAM_TRANSCRIPTION_FAILED",
    "TELEGRAM_CHECKING_REACTIONS",
    "TELEGRAM_CHECKED_REACTIONS",
    "TELEGRAM_CHECKING_VOICE",
    "TELEGRAM_CHECKED_VOICE",
    "TELEGRAM_LOADING_MESSAGES",
    "TELEGRAM_LOADED_MESSAGES",
    "TELEGRAM_SEARCHING_WORD",
    "TELEGRAM_CHECKED_WORD",
    "TELEGRAM_SEARCHING",
    "TELEGRAM_CHAT_CHECKED",
    "TELEGRAM_CHAT_ERROR",
    "TELEGRAM_CHAT_ERROR_CHAT",
    "TELEGRAM_ERROR_FLOOD_WAIT",
    "TELEGRAM_CHAT_CHECKED_CHAT",
    "TELEGRAM_SEARCHING_CHAT",
    "TELEGRAM_CHECKED_WORD_CHAT",
    "TELEGRAM_SEARCHING_WORD_CHAT",
    "TELEGRAM_SEARCHING_MESSAGE_CHAT",
    "TELEGRAM_SEARCHING_MESSAGES_CHAT",
    "TELEGRAM_CHECKED_MESSAGE_CHAT",
    "TELEGRAM_CHECKED_MESSAGES_CHAT",
    "TELEGRAM_LOADED_MESSAGES_CHAT",
    "TELEGRAM_LOADING_MESSAGES_CHAT",
    "TELEGRAM_CHECKED_VOICE_CHAT",
    "TELEGRAM_CHECKING_VOICE_CHAT",
    "TELEGRAM_CHECKED_REACTIONS_CHAT",
    "TELEGRAM_CHECKING_REACTIONS_CHAT",
]

def _template_pattern(template: str):
    placeholders = re.findall(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", template)
    pattern = re.escape(template)
    for name in placeholders:
        pattern = pattern.replace(re.escape("{" + name + "}"), f"(?P<{name}>.*?)", 1)
    return re.compile(pattern), placeholders

def _format_template(template: str, values: dict[str, str]) -> str:
    try:
        return template.format(**values)
    except Exception:
        return template

def _translate_template_text(text: str, key: str) -> str:
    target = getattr(T, key, "")
    if not target:
        return text
    for source in sorted(_all_translation_values(key), key=len, reverse=True):
        if not source or source == target:
            continue
        if "{" not in source:
            text = text.replace(source, target)
            continue
        pattern, placeholders = _template_pattern(source)
        def repl(match):
            values = {name: match.group(name) for name in placeholders}
            return _format_template(target, values)
        text = pattern.sub(repl, text)
    return text

def translate_runtime_text(value: str) -> str:
    text = str(value or "")
    exact_keys = [
        "CONTENT_REACTION_NO_TEXT",
        "CONTENT_MESSAGE_NO_TEXT",
        "CONTENT_VOICE_NO_TRANSCRIPT",
    ]
    for key in exact_keys:
        if text in _all_translation_values(key):
            return getattr(T, key)
    for key in _CONTENT_KIND_KEYS:
        current_kind = getattr(T, key)
        for source_kind in _all_translation_values(key):
            if source_kind and text == f"[{source_kind}]":
                return f"[{current_kind}]"
            prefix = f"[{source_kind}]\n" if source_kind else ""
            if prefix and text.startswith(prefix):
                return f"[{current_kind}]\n{text[len(prefix):]}"
    for key in _RUNTIME_TEXT_KEYS:
        text = _translate_template_text(text, key)
    return text



def is_handled_error_text(value: str) -> bool:
    text = str(value or "").strip()
    if not text:
        return True
    handled_keys = [
        "TELEGRAM_ERROR_INVALID_API",
        "TELEGRAM_ERROR_INVALID_PHONE",
        "TELEGRAM_ERROR_INVALID_CODE",
        "TELEGRAM_ERROR_INVALID_PASSWORD",
        "TELEGRAM_ERROR_NETWORK",
        "TELEGRAM_ERROR_FLOOD_WAIT",
        "TELEGRAM_ERROR_ENTITY_NOT_FOUND",
        "TELEGRAM_SESSION_REJECTED",
        "TELEGRAM_UNSUPPORTED_DIALOG_TYPE",
        "NETWORK_DELETE_RETRY_STATUS",
        "NETWORK_SEARCH_RETRY_STATUS",
        "WARNING_NO_MESSAGES_TO_DELETE",
        "WARNING_NO_SELECTED",
        "WARNING_STOP_NOTHING",
    ]
    handled_values = set()
    for key in handled_keys:
        handled_values.update(_all_translation_values(key))
        current = getattr(T, key, "")
        if current:
            handled_values.add(current)
    handled_values = {item for item in handled_values if item}
    for item in handled_values:
        if "{" in item:
            pattern, _ = _template_pattern(item)
            if pattern.fullmatch(text):
                return True
            continue
        if text == item or item in text:
            return True
    delete_partial_templates = _all_translation_values("DELETE_PARTIAL_NETWORK") | {getattr(T, "DELETE_PARTIAL_NETWORK", "")}
    for template in delete_partial_templates:
        if not template:
            continue
        pattern, _ = _template_pattern(template)
        if pattern.fullmatch(text):
            return True
        first_line = template.splitlines()[0].split("{")[0].strip()
        if first_line and text.startswith(first_line):
            return True
    return False

def is_network_error(error: Exception | str) -> bool:
    return translate_telegram_error(error if isinstance(error, Exception) else RuntimeError(str(error))) == T.TELEGRAM_ERROR_NETWORK