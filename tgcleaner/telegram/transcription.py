import asyncio
import json
import time

from telethon import TelegramClient, functions

from tgcleaner.core.config import user_session_dir
from tgcleaner.core.i18n import T, translate_telegram_error, is_network_error, is_flood_wait_error


class VoiceTranscriptionMixin:
    def _voice_transcription_cache_path(self, create: bool = False):
        phone = str(getattr(self, "current_phone", "") or "")
        if not phone:
            return None
        return user_session_dir(phone, create=create) / "voice_transcriptions.json"

    def _read_voice_transcription_items(self, path) -> dict:
        try:
            if path is not None and path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                items = data.get("items", {}) if isinstance(data, dict) else {}
                if isinstance(items, dict):
                    return items
        except Exception:
            pass
        return {}

    def _load_voice_transcription_cache(self) -> dict:
        cache = getattr(self, "voice_transcription_cache", None)
        if isinstance(cache, dict):
            return cache
        path = self._voice_transcription_cache_path(create=False)
        loaded = self._read_voice_transcription_items(path)
        self.voice_transcription_cache = loaded
        return loaded

    def _save_voice_transcription_cache(self) -> None:
        try:
            cache = self._load_voice_transcription_cache()
            path = self._voice_transcription_cache_path(create=True)
            if path is None:
                return
            tmp_path = path.with_name(path.name + ".tmp")
            data = {"version": 1, "items": cache}
            tmp_path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
            tmp_path.replace(path)
        except Exception:
            pass

    def _voice_transcription_cache_key(self, entity, message) -> str:
        entity_type = entity.__class__.__name__ if entity is not None else "Unknown"
        entity_id = str(getattr(entity, "id", "") or "")
        message_id = str(getattr(message, "id", "") or "")
        return "|".join((entity_type, entity_id, message_id))

    def _get_cached_voice_transcription(self, entity, message) -> str | None:
        key = self._voice_transcription_cache_key(entity, message)
        cache = self._load_voice_transcription_cache()
        item = cache.get(key)
        if not isinstance(item, dict):
            return None
        text = item.get("text")
        if not isinstance(text, str) or not text:
            return None
        return text

    def _set_cached_voice_transcription(self, entity, message, text: str) -> None:
        if not text:
            return
        key = self._voice_transcription_cache_key(entity, message)
        cache = self._load_voice_transcription_cache()
        cache[key] = {"text": text, "created_at": time.time()}
        self._save_voice_transcription_cache()

    async def _transcribe_voice_message(self, tg_client: TelegramClient, entity, message) -> str:
        cached_text = self._get_cached_voice_transcription(entity, message)
        if cached_text is not None:
            return cached_text

        async def wait_transcription_response():
            request = functions.messages.TranscribeAudioRequest(peer=entity, msg_id=message.id)
            task = asyncio.create_task(tg_client(request))
            failed_connection_checks = 0
            checks_waited = 0.0
            try:
                while not task.done():
                    if self.stop_requested:
                        task.cancel()
                        try:
                            await task
                        except BaseException:
                            pass
                        return None
                    await asyncio.sleep(0.5)
                    checks_waited += 0.5
                    if checks_waited < 6.0:
                        continue
                    checks_waited = 0.0
                    try:
                        is_connected = tg_client.is_connected() if hasattr(tg_client, "is_connected") else True
                        if not is_connected:
                            raise RuntimeError(T.TELEGRAM_ERROR_NETWORK)
                        if hasattr(tg_client, "get_me"):
                            await asyncio.wait_for(tg_client.get_me(), timeout=6)
                        failed_connection_checks = 0
                    except Exception as exc:
                        failed_connection_checks += 1
                        if failed_connection_checks >= 2:
                            task.cancel()
                            try:
                                await task
                            except BaseException:
                                pass
                            translated_error = translate_telegram_error(exc)
                            if is_flood_wait_error(translated_error):
                                raise RuntimeError(translated_error) from exc
                            if is_network_error(translated_error):
                                raise RuntimeError(T.TELEGRAM_ERROR_NETWORK) from exc
                            raise RuntimeError(T.TELEGRAM_ERROR_NETWORK) from exc
                return await task
            finally:
                if not task.done():
                    task.cancel()

        attempt = 0
        last_error = None
        while not self.stop_requested:
            try:
                result = await wait_transcription_response()
                if result is None or self.stop_requested:
                    return ""
                text = getattr(result, "text", "") or getattr(result, "transcription", "") or ""
                pending = bool(getattr(result, "pending", False))
                if text:
                    self._set_cached_voice_transcription(entity, message, text)
                    return text
                if not pending:
                    return ""
                stopped = await self._sleep_or_stop(min(8.0, 1.0 + attempt * 0.45))
                if stopped:
                    return ""
                attempt += 1
            except asyncio.CancelledError:
                return ""
            except Exception as exc:
                translated_error = translate_telegram_error(exc)
                if is_flood_wait_error(translated_error):
                    raise RuntimeError(translated_error) from exc
                if is_network_error(translated_error):
                    raise RuntimeError(T.TELEGRAM_ERROR_NETWORK) from exc
                last_error = exc
                if self.stop_requested:
                    return ""
                if attempt < 3:
                    stopped = await self._sleep_or_stop(1.0 + attempt * 0.45)
                    if stopped:
                        return ""
                    attempt += 1
                    continue
                raise RuntimeError(T.TELEGRAM_TRANSCRIPTION_FAILED.format(message_id=message.id, error=translated_error)) from exc
        if last_error is not None and not self.stop_requested:
            translated_error = translate_telegram_error(last_error)
            if is_flood_wait_error(translated_error):
                raise RuntimeError(translated_error) from last_error
            if is_network_error(translated_error):
                raise RuntimeError(T.TELEGRAM_ERROR_NETWORK) from last_error
            raise RuntimeError(T.TELEGRAM_TRANSCRIPTION_FAILED.format(message_id=message.id, error=translated_error)) from last_error
        return ""