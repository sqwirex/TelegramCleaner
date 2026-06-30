import asyncio
import shutil
from collections.abc import Callable

from telethon.errors import FloodWaitError
from telethon import functions

from tgcleaner.core.config import session_related_files, user_session_dir
from tgcleaner.core.models import FoundMessage
from tgcleaner.core.i18n import T, translate_telegram_error, is_network_error, is_flood_wait_error, get_flood_wait_seconds


REACTION_DELETE_DELAY_BETWEEN_REQUESTS = 0.5
REACTION_DELETE_PAUSE_EVERY = 3
REACTION_DELETE_PAUSE_SECONDS = 4.0
REACTION_DELETE_SOFT_RETRY_INITIAL_SECONDS = 20.0
REACTION_DELETE_SOFT_RETRY_STEP_SECONDS = 10.0
REACTION_DELETE_SOFT_RETRY_MAX_SECONDS = 60.0
REACTION_DELETE_SOFT_RETRY_MAX_ATTEMPTS = 6


class MessageDeletionMixin:
    async def _mark_client_disconnected_after_network_error(self, tg_client):
        try:
            await tg_client.disconnect()
        except Exception:
            pass

    async def _get_cached_entity_for_delete(self, tg_client, peer_id: int):
        entity = self.entity_cache.get(peer_id)
        if entity is not None:
            return entity
        soft_retry_delay = 15.0
        while True:
            if self.stop_requested:
                return None
            try:
                entity = await asyncio.wait_for(tg_client.get_entity(peer_id), timeout=12)
                self.entity_cache[peer_id] = entity
                return entity
            except FloodWaitError as exc:
                if not await self._sleep_delete_delay(float(exc.seconds) + 1.0):
                    return None
            except asyncio.TimeoutError:
                if not await self._sleep_delete_delay(soft_retry_delay):
                    return None
                soft_retry_delay = min(45.0, soft_retry_delay + 10.0)
            except Exception as exc:
                seconds = get_flood_wait_seconds(exc)
                if seconds is None:
                    raise
                if not await self._sleep_delete_delay(float(seconds) + 1.0):
                    return None

    async def _sleep_delete_delay(self, seconds: float) -> bool:
        end_at = asyncio.get_running_loop().time() + max(0.0, seconds)
        while True:
            if self.stop_requested:
                return False
            remaining = end_at - asyncio.get_running_loop().time()
            if remaining <= 0:
                return True
            await asyncio.sleep(min(1.0, remaining))

    def _emit_delete_progress(self, progress_callback: Callable | None, mode: str, deleted: int, total: int):
        if progress_callback is None:
            return
        total = max(0, int(total or 0))
        deleted = max(0, min(int(deleted or 0), total))
        remaining = max(0, total - deleted)
        text = T.DELETE_REACTIONS_PROGRESS if mode == "reactions" else T.DELETE_MESSAGES_PROGRESS
        progress_callback({
            "type": "delete_status",
            "text": text.format(deleted=deleted, remaining=remaining, total=total),
            "deleted": deleted,
            "remaining": remaining,
            "total": total,
        })

    async def _await_reaction_request_with_stop(self, awaitable) -> bool:
        task = asyncio.ensure_future(awaitable)
        while True:
            if self.stop_requested:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                return False
            done, _ = await asyncio.wait({task}, timeout=0.5)
            if task in done:
                await task
                return True

    def _is_reaction_delete_hard_error(self, error: Exception) -> bool:
        error_name = type(error).__name__.lower()
        text = str(error).lower()
        if "unauthorized" in error_name or "forbidden" in error_name:
            return True
        hard_markers = (
            "message_id_invalid",
            "msg_id_invalid",
            "peer_id_invalid",
            "channel_invalid",
            "chat_admin_required",
            "reaction_invalid",
        )
        return any(marker in text for marker in hard_markers)

    async def _delete_message_reaction_with_wait(self, tg_client, entity, message_id: int) -> bool:
        soft_retry_delay = REACTION_DELETE_SOFT_RETRY_INITIAL_SECONDS
        soft_retry_count = 0
        while True:
            if self.stop_requested:
                return False
            try:
                return await self._await_reaction_request_with_stop(
                    tg_client(functions.messages.SendReactionRequest(peer=entity, msg_id=message_id, reaction=None))
                )
            except FloodWaitError as exc:
                if not await self._sleep_delete_delay(float(exc.seconds) + 1.0):
                    return False
            except Exception as exc:
                seconds = get_flood_wait_seconds(exc)
                if seconds is not None:
                    if not await self._sleep_delete_delay(float(seconds) + 1.0):
                        return False
                    continue
                if self._is_reaction_delete_hard_error(exc):
                    raise
                soft_retry_count += 1
                if soft_retry_count > REACTION_DELETE_SOFT_RETRY_MAX_ATTEMPTS:
                    raise
                if not await self._sleep_delete_delay(soft_retry_delay):
                    return False
                soft_retry_delay = min(REACTION_DELETE_SOFT_RETRY_MAX_SECONDS, soft_retry_delay + REACTION_DELETE_SOFT_RETRY_STEP_SECONDS)

    async def delete_reactions_grouped(
        self,
        messages: list[FoundMessage],
        delay_between_chunks: float = REACTION_DELETE_DELAY_BETWEEN_REQUESTS,
        progress_callback: Callable | None = None,
    ) -> tuple[int, list[str], list[FoundMessage]]:
        tg_client = await self.ensure_authorized()
        removed_count = 0
        errors: list[str] = []
        remaining: list[FoundMessage] = []
        total = len(messages)
        self._emit_delete_progress(progress_callback, "reactions", removed_count, total)
        for index, message in enumerate(messages):
            try:
                if self.stop_requested:
                    remaining.extend(messages[index:])
                    break
                entity = await self._get_cached_entity_for_delete(tg_client, message.peer_id)
                if entity is None:
                    remaining.extend(messages[index:])
                    break
                if not await self._delete_message_reaction_with_wait(tg_client, entity, message.message_id):
                    remaining.extend(messages[index:])
                    break
                removed_count += 1
                self._emit_delete_progress(progress_callback, "reactions", removed_count, total)
                pause = REACTION_DELETE_PAUSE_SECONDS if removed_count % REACTION_DELETE_PAUSE_EVERY == 0 and removed_count < total else delay_between_chunks
                if not await self._sleep_delete_delay(pause):
                    remaining.extend(messages[index + 1:])
                    break
            except Exception as exc:
                translated_error = translate_telegram_error(exc)
                if is_network_error(translated_error):
                    await self._mark_client_disconnected_after_network_error(tg_client)
                errors.append(translated_error if is_network_error(translated_error) else f"{message.chat_input} / ID {message.message_id}: {translated_error}")
                remaining.extend(messages[index:])
                break
        self._emit_delete_progress(progress_callback, "reactions", removed_count, total)
        return removed_count, errors, remaining

    async def delete_messages_grouped(
        self,
        messages: list[FoundMessage],
        revoke: bool,
        delay_between_chunks: float = 1.2,
        progress_callback: Callable | None = None,
    ) -> tuple[int, list[str], list[FoundMessage]]:
        tg_client = await self.ensure_authorized()
        grouped: dict[int, dict[str, object]] = {}
        for message in messages:
            bucket = grouped.setdefault(message.peer_id, {"label": message.chat_input, "messages": []})
            bucket["messages"].append(message)
        deleted_count = 0
        errors: list[str] = []
        remaining: list[FoundMessage] = []
        peer_items = list(grouped.items())
        total = len(messages)
        self._emit_delete_progress(progress_callback, "messages", deleted_count, total)
        for peer_index, (peer_id, payload) in enumerate(peer_items):
            label = str(payload["label"])
            peer_messages = list(payload["messages"])
            try:
                entity = await self._get_cached_entity_for_delete(tg_client, peer_id)
                for i in range(0, len(peer_messages), 100):
                    chunk_messages = peer_messages[i:i + 100]
                    chunk_ids = [message.message_id for message in chunk_messages]
                    try:
                        if self.stop_requested:
                            remaining.extend(peer_messages[i:])
                            for _, rest_payload in peer_items[peer_index + 1:]:
                                remaining.extend(list(rest_payload["messages"]))
                            self._emit_delete_progress(progress_callback, "messages", deleted_count, total)
                            return deleted_count, errors, remaining
                        await asyncio.wait_for(tg_client.delete_messages(entity, chunk_ids, revoke=revoke), timeout=8)
                        deleted_count += len(chunk_ids)
                        self._emit_delete_progress(progress_callback, "messages", deleted_count, total)
                        if not await self._sleep_delete_delay(delay_between_chunks):
                            remaining.extend(peer_messages[i + len(chunk_messages):])
                            for _, rest_payload in peer_items[peer_index + 1:]:
                                remaining.extend(list(rest_payload["messages"]))
                            return deleted_count, errors, remaining
                    except FloodWaitError as exc:
                        if exc.seconds > 20:
                            errors.append(translate_telegram_error(exc))
                            remaining.extend(peer_messages[i:])
                            for _, rest_payload in peer_items[peer_index + 1:]:
                                remaining.extend(list(rest_payload["messages"]))
                            self._emit_delete_progress(progress_callback, "messages", deleted_count, total)
                            return deleted_count, errors, remaining
                        if not await self._sleep_delete_delay(float(exc.seconds)):
                            remaining.extend(peer_messages[i:])
                            for _, rest_payload in peer_items[peer_index + 1:]:
                                remaining.extend(list(rest_payload["messages"]))
                            return deleted_count, errors, remaining
                        await asyncio.wait_for(tg_client.delete_messages(entity, chunk_ids, revoke=revoke), timeout=8)
                        deleted_count += len(chunk_ids)
                        self._emit_delete_progress(progress_callback, "messages", deleted_count, total)
                        if not await self._sleep_delete_delay(delay_between_chunks):
                            remaining.extend(peer_messages[i + len(chunk_messages):])
                            for _, rest_payload in peer_items[peer_index + 1:]:
                                remaining.extend(list(rest_payload["messages"]))
                            return deleted_count, errors, remaining
                    except Exception as exc:
                        translated_error = translate_telegram_error(exc)
                        if is_network_error(translated_error):
                            await self._mark_client_disconnected_after_network_error(tg_client)
                        errors.append(translated_error if is_network_error(translated_error) or is_flood_wait_error(translated_error) else f"{label}: {translated_error}")
                        remaining.extend(peer_messages[i:])
                        for _, rest_payload in peer_items[peer_index + 1:]:
                            remaining.extend(list(rest_payload["messages"]))
                        self._emit_delete_progress(progress_callback, "messages", deleted_count, total)
                        return deleted_count, errors, remaining
            except Exception as exc:
                translated_error = translate_telegram_error(exc)
                if is_network_error(translated_error):
                    await self._mark_client_disconnected_after_network_error(tg_client)
                errors.append(translated_error if is_network_error(translated_error) or is_flood_wait_error(translated_error) else f"{label}: {translated_error}")
                remaining.extend(peer_messages)
                for _, rest_payload in peer_items[peer_index + 1:]:
                    remaining.extend(list(rest_payload["messages"]))
                self._emit_delete_progress(progress_callback, "messages", deleted_count, total)
                return deleted_count, errors, remaining
        self._emit_delete_progress(progress_callback, "messages", deleted_count, total)
        return deleted_count, errors, remaining

    async def logout_and_delete_session(self, phone: str) -> int:
        await self.disconnect_current()
        deleted = 0
        for path in session_related_files(phone):
            try:
                if path.exists() and path.is_file():
                    path.unlink()
                    deleted += 1
            except Exception:
                pass
        try:
            folder = user_session_dir(phone, create=False)
            if folder.exists() and folder.is_dir():
                deleted += sum(1 for item in folder.rglob("*") if item.is_file())
                shutil.rmtree(folder)
        except Exception:
            pass
        try:
            self.voice_transcription_cache = None
        except Exception:
            pass
        return deleted