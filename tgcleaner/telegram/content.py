import asyncio
import ast
import re

from tgcleaner.core.i18n import T


class MessageContentMixin:
    def _document_attribute_names(self, message) -> set[str]:
        names = set()
        media = getattr(message, "media", None)
        document = getattr(message, "document", None) or (getattr(media, "document", None) if media is not None else None)
        for attr in getattr(document, "attributes", []) or []:
            names.add(attr.__class__.__name__)
        return names

    def _document_mime_type(self, message) -> str:
        media = getattr(message, "media", None)
        document = getattr(message, "document", None) or (getattr(media, "document", None) if media is not None else None)
        return str(getattr(document, "mime_type", "") or "").lower()

    def _is_service_message(self, message) -> bool:
        action = getattr(message, "action", None)
        if action is not None:
            return True
        return str(message.__class__.__name__).startswith("MessageService")

    def _describe_message_content_kind(self, message) -> str:
        media = getattr(message, "media", None)
        media_name = media.__class__.__name__ if media is not None else ""
        attr_names = self._document_attribute_names(message)
        mime_type = self._document_mime_type(message)
        document = getattr(message, "document", None) or (getattr(media, "document", None) if media is not None else None)
        document_attrs = getattr(document, "attributes", []) or []
        if self._is_service_message(message):
            return T.CONTENT_SERVICE
        if getattr(message, "grouped_id", None) is not None:
            return T.CONTENT_ALBUM
        if media_name in ("MessageMediaDice",) or getattr(message, "dice", None) is not None:
            return T.CONTENT_ANIMATED_EMOJI
        if media_name in ("MessageMediaGame",) or getattr(message, "game", None) is not None:
            return T.CONTENT_GAME
        if media_name in ("MessageMediaInvoice",) or getattr(message, "invoice", None) is not None or getattr(media, "invoice", None) is not None:
            return T.CONTENT_INVOICE
        if media_name in ("MessageMediaPaidMedia", "MessageMediaGiveaway", "MessageMediaGiveawayResults", "MessageMediaStory"):
            mapping = {
                "MessageMediaPaidMedia": T.CONTENT_PAID_MEDIA,
                "MessageMediaGiveaway": T.CONTENT_GIVEAWAY,
                "MessageMediaGiveawayResults": T.CONTENT_GIVEAWAY_RESULTS,
                "MessageMediaStory": T.CONTENT_STORY,
            }
            return mapping.get(media_name, T.CONTENT_MEDIA)
        if getattr(message, "todo", None) is not None or getattr(media, "todo", None) is not None or media_name in ("MessageMediaTodo", "MessageMediaChecklist", "MessageMediaToDo"):
            return T.CONTENT_TODO
        if getattr(message, "poll", None) is not None or getattr(media, "poll", None) is not None or media_name == "MessageMediaPoll":
            poll = getattr(message, "poll", None) or getattr(media, "poll", None)
            quiz = bool(getattr(poll, "quiz", False) or getattr(getattr(poll, "poll", None), "quiz", False))
            return T.CONTENT_QUIZ if quiz else T.CONTENT_POLL
        if getattr(message, "contact", None) is not None or media_name == "MessageMediaContact" or getattr(media, "phone_number", None):
            return T.CONTENT_CONTACT
        if media_name == "MessageMediaVenue" or getattr(media, "venue", None) is not None:
            return T.CONTENT_VENUE
        if media_name == "MessageMediaGeoLive" or getattr(media, "period", None) is not None and getattr(media, "geo", None) is not None:
            return T.CONTENT_LIVE_GEO
        if getattr(message, "geo", None) is not None or media_name == "MessageMediaGeo" or getattr(media, "geo", None) is not None:
            return T.CONTENT_GEO
        if getattr(message, "voice", None) is not None:
            return T.CONTENT_VOICE
        if getattr(message, "video_note", None) is not None or "DocumentAttributeVideo" in attr_names and any(getattr(attr, "round_message", False) for attr in document_attrs):
            return T.CONTENT_ROUND
        if getattr(message, "sticker", None) is not None or "DocumentAttributeSticker" in attr_names:
            return T.CONTENT_STICKER
        if "DocumentAttributeCustomEmoji" in attr_names:
            return T.CONTENT_ANIMATED_EMOJI
        if getattr(message, "gif", None) is not None or "DocumentAttributeAnimated" in attr_names or mime_type == "image/gif":
            return "GIF"
        webpage = getattr(media, "webpage", None) if media is not None else None
        if webpage is not None or media_name == "MessageMediaWebPage":
            return T.CONTENT_LINK
        if getattr(message, "photo", None) is not None:
            return T.CONTENT_PHOTO
        if getattr(message, "video", None) is not None:
            return T.CONTENT_VIDEO
        if getattr(message, "audio", None) is not None:
            return T.CONTENT_AUDIO
        if getattr(message, "document", None) is not None:
            return T.CONTENT_FILE
        if media is not None:
            return T.CONTENT_MEDIA
        return T.CONTENT_TEXT

    def _describe_message_media(self, message) -> str:
        kind = self._describe_message_content_kind(message)
        return "" if kind == T.CONTENT_TEXT else f"[{kind}]"

    def _normalize_text_value(self, value) -> str:
        if value is None or isinstance(value, (bytes, bytearray)):
            return ""
        if isinstance(value, str):
            value = value.strip()
            return value if value else ""
        return ""

    def _get_text_attr(self, source, attr_name: str) -> str:
        try:
            value = getattr(source, attr_name, "")
        except Exception:
            return ""
        if callable(value):
            try:
                value = value()
            except Exception:
                return ""
        normalized = self._normalize_text_value(value)
        if normalized:
            return normalized
        if attr_name == "message" and value is not None and value is not source:
            return self._get_message_text_from_dict(value, 0)
        return ""

    def _get_message_text_from_dict(self, data, depth: int = 0) -> str:
        if depth > 4:
            return ""
        if isinstance(data, dict):
            for key in ("raw_text", "_raw_text", "message", "text", "caption", "title", "description", "url", "address", "phone_number", "first_name", "last_name", "question"):
                value = self._normalize_text_value(data.get(key))
                if value:
                    return value
            for value in data.values():
                nested = self._get_message_text_from_dict(value, depth + 1)
                if nested:
                    return nested
        elif isinstance(data, (list, tuple)):
            for value in data:
                nested = self._get_message_text_from_dict(value, depth + 1)
                if nested:
                    return nested
        elif not isinstance(data, (str, bytes, bytearray, int, float, bool, type(None))):
            try:
                return self._get_message_text_from_dict(vars(data), depth + 1)
            except Exception:
                return ""
        return ""

    def _get_message_text_value(self, message) -> str:
        for attr_name in ("raw_text", "_raw_text", "message", "text", "caption"):
            value = self._get_text_attr(message, attr_name)
            if value:
                return value
        media = getattr(message, "media", None)
        webpage = getattr(media, "webpage", None) if media is not None else None
        document = getattr(message, "document", None) or (getattr(media, "document", None) if media is not None else None)
        poll = getattr(message, "poll", None) or (getattr(media, "poll", None) if media is not None else None)
        for source in (media, webpage, document, poll):
            if source is None:
                continue
            for attr_name in ("caption", "title", "description", "url", "address", "phone_number", "first_name", "last_name", "question"):
                value = self._get_text_attr(source, attr_name)
                if value:
                    return value
        try:
            data = message.to_dict()
        except Exception:
            data = None
        value = self._get_message_text_from_dict(data)
        if value:
            return value
        try:
            stringified = message.stringify()
        except Exception:
            stringified = ""
        repr_values = []
        try:
            repr_values.append(repr(message))
        except Exception:
            pass
        repr_values.append(stringified)
        try:
            repr_values.append(str(message))
        except Exception:
            pass
        patterns = (
            r"message=(?P<value>'(?:\\.|[^'])*')",
            r'message=(?P<value>"(?:\\.|[^"])*")',
            r"raw_text=(?P<value>'(?:\\.|[^'])*')",
            r'raw_text=(?P<value>"(?:\\.|[^"])*")',
            r"'message':\s*(?P<value>'(?:\\.|[^'])*')",
            r'"message":\s*(?P<value>"(?:\\.|[^"])*")',
            r"'raw_text':\s*(?P<value>'(?:\\.|[^'])*')",
            r'"raw_text":\s*(?P<value>"(?:\\.|[^"])*")',
        )
        for source_text in repr_values:
            for pattern in patterns:
                match = re.search(pattern, source_text)
                if not match:
                    continue
                try:
                    parsed = ast.literal_eval(match.group("value"))
                except Exception:
                    parsed = match.group("value").strip("'\"")
                normalized = self._normalize_text_value(parsed)
                if normalized:
                    return normalized
        return ""

    def _message_text_candidates(self, message) -> list[str]:
        candidates = []
        for attr_name in ("raw_text", "_raw_text", "message", "text", "caption"):
            value = self._get_text_attr(message, attr_name)
            if value:
                candidates.append(value)
        try:
            data = message.to_dict()
        except Exception:
            data = None
        if isinstance(data, dict):
            for key in ("message", "raw_text", "text", "caption"):
                value = self._normalize_text_value(data.get(key))
                if value:
                    candidates.append(value)
            value = self._get_message_text_from_dict(data)
            if value:
                candidates.append(value)
        unique = []
        seen = set()
        for value in candidates:
            normalized = value.strip()
            if normalized and normalized not in seen:
                unique.append(normalized)
                seen.add(normalized)
        return unique

    def _compose_message_text(self, message, reaction_mode: bool = False) -> str:
        text_value = ""
        candidates = self._message_text_candidates(message)
        if candidates:
            text_value = max(candidates, key=len)
        else:
            text_value = self._get_message_text_value(message)
        media_name = self._describe_message_media(message)
        if media_name and text_value:
            return f"{media_name}\n{text_value}"
        if media_name:
            return media_name
        if reaction_mode:
            return text_value or T.CONTENT_REACTION_NO_TEXT
        return text_value

    def _message_is_voice(self, message) -> bool:
        if getattr(message, "voice", None) is not None:
            return True
        if getattr(message, "video_note", None) is not None:
            return True
        media = getattr(message, "media", None)
        document = getattr(media, "document", None) if media is not None else None
        for attr in getattr(document, "attributes", []) or []:
            if attr.__class__.__name__ == "DocumentAttributeAudio" and getattr(attr, "voice", False):
                return True
        return False

    async def _sleep_or_stop(self, seconds: float) -> bool:
        elapsed = 0.0
        step = 0.1
        while elapsed < seconds:
            if self.stop_requested:
                return True
            await asyncio.sleep(min(step, seconds - elapsed))
            elapsed += step
        return self.stop_requested