from typing import Optional

from telethon import TelegramClient

from tgcleaner.telegram.chats import ChatResolverMixin
from tgcleaner.telegram.client import TelegramClientAuthMixin
from tgcleaner.telegram.content import MessageContentMixin
from tgcleaner.telegram.deletion import MessageDeletionMixin
from tgcleaner.telegram.formatting import TelegramFormattingMixin
from tgcleaner.telegram.reactions import ReactionLookupMixin
from tgcleaner.telegram.search import MessageSearchMixin
from tgcleaner.telegram.transcription import VoiceTranscriptionMixin


class TelegramController(
    TelegramClientAuthMixin,
    MessageContentMixin,
    VoiceTranscriptionMixin,
    ReactionLookupMixin,
    TelegramFormattingMixin,
    ChatResolverMixin,
    MessageSearchMixin,
    MessageDeletionMixin,
):
    def __init__(self):
        self.client: Optional[TelegramClient] = None
        self.current_phone: Optional[str] = None
        self.phone_code_hash: Optional[str] = None
        self.current_api_id: Optional[int] = None
        self.current_api_hash: Optional[str] = None
        self.current_username: Optional[str] = None
        self.current_session_name: Optional[str] = None
        self.entity_cache: dict[int, object] = {}
        self.voice_transcription_cache: dict | None = None
        self.stop_requested = False