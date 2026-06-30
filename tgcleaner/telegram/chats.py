import asyncio
import re

from telethon import TelegramClient
from telethon.utils import get_peer_id
from telethon.tl import functions

from tgcleaner.core.parsing import parse_chat_reference
from tgcleaner.telegram.entities import ensure_supported_dialog_entity, find_dialog_entity_by_numeric_id, iter_searchable_dialog_entities
from tgcleaner.core.i18n import T, translate_telegram_error, is_network_error, is_flood_wait_error


class ChatResolverMixin:
    def _format_resolve_error(self, chat_input: str, error: Exception) -> str:
        translated_error = translate_telegram_error(error)
        if translated_error == T.TELEGRAM_UNSUPPORTED_DIALOG_TYPE or is_flood_wait_error(translated_error):
            return translated_error
        return f"{chat_input}: {translated_error}"


    def _is_forum_topic_root_message(self, message) -> bool:
        if message is None:
            return False
        action_name = type(getattr(message, "action", None)).__name__.lower()
        if "topic" in action_name and "create" in action_name:
            return True
        replies = getattr(message, "replies", None)
        return bool(getattr(replies, "forum_topic", False))

    def _forum_topics_response_has_id(self, response, topic_id: int) -> bool:
        for topic in getattr(response, "topics", None) or []:
            if getattr(topic, "id", None) == topic_id or getattr(topic, "top_message", None) == topic_id:
                return True
        return False

    async def _resolve_topic_by_forum_api(self, tg_client: TelegramClient, entity, topic_id: int) -> int | None:
        if not bool(getattr(entity, "forum", False)):
            return None
        try:
            input_entity = await asyncio.wait_for(tg_client.get_input_entity(entity), timeout=8)
            response = await asyncio.wait_for(
                tg_client(functions.channels.GetForumTopicsByIDRequest(channel=input_entity, topics=[topic_id])),
                timeout=8,
            )
        except Exception:
            return topic_id if topic_id == 1 else None
        return topic_id if self._forum_topics_response_has_id(response, topic_id) or topic_id == 1 else None

    async def _resolve_existing_topic_id(self, tg_client: TelegramClient, entity, topic_id: int | None) -> int | None:
        if topic_id is None:
            return None
        topic_from_forum_api = await self._resolve_topic_by_forum_api(tg_client, entity, topic_id)
        if topic_from_forum_api is not None:
            return topic_from_forum_api
        try:
            message = await asyncio.wait_for(tg_client.get_messages(entity, ids=topic_id), timeout=8)
        except Exception:
            return None
        if isinstance(message, list):
            message = message[0] if message else None
        return topic_id if self._is_forum_topic_root_message(message) else None

    async def resolve_unique_chats(self, tg_client: TelegramClient, chat_inputs: list[str]) -> tuple[list[tuple[int, str, object, int | None]], list[str]]:
        resolved: dict[tuple[int, int | None], tuple[int, str, object, int | None]] = {}
        errors: list[str] = []
        for raw_input in chat_inputs:
            chat_input = raw_input.strip()
            if not chat_input:
                continue
            try:
                chat_reference = parse_chat_reference(chat_input)
                normalized = chat_reference.normalized
                topic_id = chat_reference.topic_id
                is_numeric = re.fullmatch(r"[+-]?\d+", normalized) is not None
                lookup_value = int(normalized) if is_numeric else normalized
                try:
                    entity = await tg_client.get_entity(lookup_value)
                except Exception:
                    if is_numeric:
                        entity = await find_dialog_entity_by_numeric_id(tg_client, int(lookup_value))
                    else:
                        raise
                entity = ensure_supported_dialog_entity(entity)
                if chat_reference.validate_topic:
                    topic_id = await self._resolve_existing_topic_id(tg_client, entity, topic_id)
                peer_id = get_peer_id(entity)
                display_label = self._format_entity_label(entity)
                if topic_id is not None:
                    display_label = f"{display_label} • {T.TELEGRAM_TOPIC_ID.format(topic_id=topic_id)}"
                resolved_key = (peer_id, topic_id)
                if resolved_key not in resolved:
                    resolved[resolved_key] = (peer_id, display_label, entity, topic_id)
                self.entity_cache[peer_id] = entity
            except Exception as exc:
                errors.append(self._format_resolve_error(chat_input, exc))
        return list(resolved.values()), errors

    async def resolve_all_searchable_chats(self, tg_client: TelegramClient, groups_only: bool = False) -> tuple[list[tuple[int, str, object, int | None]], list[str]]:
        resolved: dict[int, tuple[int, str, object, int | None]] = {}
        errors: list[str] = []
        try:
            async for entity in iter_searchable_dialog_entities(tg_client, groups_only=groups_only):
                if self.stop_requested:
                    break
                try:
                    entity = ensure_supported_dialog_entity(entity)
                    peer_id = get_peer_id(entity)
                    display_label = self._format_entity_label(entity)
                    if peer_id not in resolved:
                        resolved[peer_id] = (peer_id, display_label, entity, None)
                    self.entity_cache[peer_id] = entity
                except Exception as exc:
                    errors.append(translate_telegram_error(exc))
        except Exception as exc:
            translated_error = translate_telegram_error(exc)
            if is_network_error(translated_error) or is_flood_wait_error(translated_error):
                errors.append(translated_error)
            else:
                mode_name = T.TELEGRAM_ONLY_GROUPS_TITLE if groups_only else T.TELEGRAM_ALL_TITLE
                errors.append(f"{mode_name}: {translated_error}")
        return list(resolved.values()), errors