from telethon.utils import get_peer_id
from tgcleaner.core.i18n import T


def is_group_entity(entity) -> bool:
    return bool(getattr(entity, "megagroup", False) or entity.__class__.__name__ in ("Chat", "ChatForbidden"))


def is_unsupported_dialog_entity(entity) -> bool:
    return bool(getattr(entity, "broadcast", False) and not getattr(entity, "megagroup", False))


def ensure_supported_dialog_entity(entity):
    if is_unsupported_dialog_entity(entity):
        raise ValueError(T.TELEGRAM_UNSUPPORTED_DIALOG_TYPE)
    return entity


def entity_id_candidates(entity) -> set[int]:
    candidates: set[int] = set()
    entity_id = getattr(entity, "id", None)
    if entity_id is not None:
        try:
            entity_id = int(entity_id)
            candidates.add(entity_id)
            candidates.add(-entity_id)
            if getattr(entity, "megagroup", False) or getattr(entity, "broadcast", False):
                candidates.add(int(f"-100{entity_id}"))
        except Exception:
            pass
    try:
        candidates.add(int(get_peer_id(entity)))
    except Exception:
        pass
    return candidates


async def find_dialog_entity_by_numeric_id(tg_client, numeric_id: int):
    async for dialog in tg_client.iter_dialogs():
        entity = dialog.entity
        if numeric_id in entity_id_candidates(entity):
            return ensure_supported_dialog_entity(entity)
    raise ValueError(T.TELEGRAM_CHAT_ID_NOT_FOUND)


async def iter_searchable_dialog_entities(tg_client, groups_only: bool = False):
    async for dialog in tg_client.iter_dialogs():
        entity = dialog.entity
        if is_unsupported_dialog_entity(entity):
            continue
        if groups_only and not is_group_entity(entity):
            continue
        yield entity