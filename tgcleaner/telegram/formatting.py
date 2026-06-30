from tgcleaner.core.i18n import T
class TelegramFormattingMixin:
    def _format_sender_label(self, sender) -> str:
        if sender is None:
            return T.CONTENT_UNKNOWN
        username = getattr(sender, "username", None)
        if username:
            return f"@{username}"
        title = getattr(sender, "title", None)
        if title:
            return title
        first_name = getattr(sender, "first_name", "") or ""
        last_name = getattr(sender, "last_name", "") or ""
        full_name = (first_name + " " + last_name).strip()
        if full_name:
            return full_name
        phone = getattr(sender, "phone", None)
        if phone:
            return f"+{phone}"
        sender_id = getattr(sender, "id", None)
        return str(sender_id) if sender_id is not None else T.CONTENT_UNKNOWN

    def _format_entity_label(self, entity) -> str:
        username = getattr(entity, "username", None)
        if username:
            return f"@{username}"
        title = getattr(entity, "title", None)
        if title:
            return title
        first_name = getattr(entity, "first_name", "") or ""
        last_name = getattr(entity, "last_name", "") or ""
        full_name = (first_name + " " + last_name).strip()
        if full_name:
            return full_name
        phone = getattr(entity, "phone", None)
        if phone:
            return f"+{phone}"
        return str(getattr(entity, "id", T.CONTENT_UNKNOWN_CHAT))