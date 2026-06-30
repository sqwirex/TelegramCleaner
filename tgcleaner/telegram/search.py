import asyncio

from telethon import TelegramClient
from tgcleaner.core.models import FoundMessage, SearchTerm, format_message_date
from tgcleaner.core.parsing import contains_exact_word_or_phrase, match_message, match_transcription_message, parse_terms
from tgcleaner.telegram.entities import is_group_entity
from tgcleaner.core.i18n import T, translate_telegram_error, is_network_error, is_flood_wait_error, get_flood_wait_seconds


class MessageSearchMixin:
    def _short_status_title(self, title: str, limit: int = 25) -> str:
        text = str(title or "").strip()
        if not text:
            return ""
        if len(text) <= limit:
            return text
        words = text.split()
        if not words:
            return text[:limit].rstrip() + "..."
        first = words[0]
        if len(first) > limit:
            return first[:limit].rstrip() + "..."
        selected = []
        current_length = 0
        for word in words:
            next_length = len(word) if not selected else current_length + 1 + len(word)
            if next_length > limit:
                break
            selected.append(word)
            current_length = next_length
        if not selected:
            selected.append(first)
        return " ".join(selected) + "..."

    def _status_chat_label(self, display_label: str, peer_id: int, topic_id: int | None = None, force_chat_id: bool = False) -> str:
        title = str(display_label or "")
        base_title = title.split(" • ", 1)[0].strip()
        if base_title:
            label = self._short_status_title(base_title) if force_chat_id else title
        else:
            label = T.TELEGRAM_STATUS_CHAT_ID.format(chat_id=peer_id)
        if topic_id is not None and T.TELEGRAM_TOPIC_ID.format(topic_id=topic_id) not in label:
            label = f"{label} • {T.TELEGRAM_TOPIC_ID.format(topic_id=topic_id)}"
        return label



    def _export_dialog_type_key_for_entity(self, entity) -> str:
        if bool(getattr(entity, "megagroup", False)):
            return "EXPORT_SUPERGROUP"
        if entity.__class__.__name__ in ("Chat", "ChatForbidden"):
            return "EXPORT_GROUP"
        return "EXPORT_PRIVATE_DIALOG"


    def _match_message_as_topic_search(self, text: str, terms: list[SearchTerm]) -> list[SearchTerm]:
        text_normalized = str(text or "").casefold()
        matched = []
        for term in terms:
            if contains_exact_word_or_phrase(text_normalized, term.value):
                matched.append(term)
        return matched

    def _is_soft_transcription_error(self, error: str) -> bool:
        text = str(error or "").lower()
        return any(marker in text for marker in (
            "caused",
            "transcrib",
            "voice",
            "speech",
            "flood",
            "wait",
            "timeout",
            "rate",
            "limit",
            "too many",
        ))

    async def _sleep_for_search_wait(self, seconds: int, progress_callback, count_getter, processed_getter, total) -> bool:
        remaining = max(1, int(seconds))
        while remaining > 0:
            if self.stop_requested:
                return True
            step = min(5, remaining)
            await asyncio.sleep(step)
            remaining -= step
        return self.stop_requested


    async def _iter_messages_by_id_ranges(self, tg_client: TelegramClient, entity, start_id: int, progress_callback, count_getter, processed_getter, total, batch_size: int = 100, empty_batch_limit: int = 60, batch_timeout: int = 10):
        try:
            current_id = int(start_id) - 1
        except Exception:
            return
        empty_batches = 0
        while current_id > 0 and not self.stop_requested:
            lower_id = max(1, current_id - batch_size + 1)
            ids = list(range(current_id, lower_id - 1, -1))
            try:
                task = asyncio.create_task(tg_client.get_messages(entity, ids=ids))
                done, pending = await asyncio.wait({task}, timeout=batch_timeout)
                if pending:
                    task.cancel()
                    empty_batches += 1
                    if empty_batches >= empty_batch_limit:
                        return
                    await asyncio.sleep(1.0)
                    current_id = lower_id - 1
                    continue
                batch = task.result()
            except Exception as exc:
                seconds = get_flood_wait_seconds(exc)
                if seconds is None:
                    translated_error = translate_telegram_error(exc)
                    seconds = get_flood_wait_seconds(translated_error)
                if seconds is None:
                    empty_batches += 1
                    if empty_batches >= empty_batch_limit:
                        return
                    current_id = lower_id - 1
                    await asyncio.sleep(0.5)
                    continue
                stopped = await self._sleep_for_search_wait(seconds, progress_callback, count_getter, processed_getter, total)
                if stopped:
                    return
                continue
            if batch is None:
                messages = []
            elif isinstance(batch, list):
                messages = batch
            else:
                try:
                    messages = list(batch)
                except TypeError:
                    messages = [batch]
            messages = [message for message in messages if getattr(message, "id", None)]
            if not messages:
                empty_batches += 1
                if empty_batches >= empty_batch_limit:
                    return
            else:
                empty_batches = 0
                messages.sort(key=lambda message: getattr(message, "id", 0), reverse=True)
                for message in messages:
                    if self.stop_requested:
                        return
                    yield message
            current_id = lower_id - 1
            await asyncio.sleep(0.1)

    async def _iter_messages_waiting(self, tg_client: TelegramClient, entity, count_getter, processed_getter, total, progress_callback=None, **kwargs):
        offset_id = kwargs.pop("offset_id", None)
        offset_date = kwargs.pop("offset_date", None)
        retry_empty = bool(kwargs.pop("_retry_empty", False))
        empty_retry_limit = int(kwargs.pop("_empty_retry_limit", 0) or 0)
        empty_retry_seconds = int(kwargs.pop("_empty_retry_seconds", 4) or 4)
        empty_retry_after_processed = int(kwargs.pop("_empty_retry_after_processed", 0) or 0)
        manual_get_messages = bool(kwargs.pop("_manual_get_messages", False))
        ignore_total_completion = bool(kwargs.pop("_ignore_total_completion", False))
        id_range_fallback = bool(kwargs.pop("_id_range_fallback", False))
        disable_date_fallback = bool(kwargs.pop("_disable_date_fallback", False))
        manual_boundary_shift_size = int(kwargs.pop("_manual_boundary_shift_size", 25) or 25)
        batch_timeout = int(kwargs.pop("_batch_timeout", 20) or 20)
        requested_limit = kwargs.pop("limit", None)
        remaining = None
        if requested_limit is not None:
            try:
                remaining = max(0, int(requested_limit))
            except Exception:
                remaining = None
        batch_size = 100
        empty_retries = 0
        manual_boundary_shifts = 0
        manual_date_fallbacks = 0
        last_message_date = None
        yielded_total = 0
        soft_pause_after = 2800
        soft_pause_seconds = 8

        def empty_retry_settings(processed_now: int):
            should_retry_by_total = total is not None and processed_now < total and processed_now >= empty_retry_after_processed > 0
            should_retry_by_flag = retry_empty and (empty_retry_after_processed <= 0 or processed_now >= empty_retry_after_processed)
            should_retry_empty = should_retry_by_total or should_retry_by_flag
            if should_retry_by_total:
                missing_count = max(0, int(total) - int(processed_now))
                if missing_count <= 50:
                    return should_retry_empty, 1, 1
                if missing_count <= 200:
                    return should_retry_empty, 3, 3
                return should_retry_empty, 12, soft_pause_seconds
            return should_retry_empty, empty_retry_limit, empty_retry_seconds

        async def retry_empty_batch(processed_now: int) -> bool:
            nonlocal empty_retries
            should_retry_empty, current_empty_retry_limit, wait_seconds = empty_retry_settings(processed_now)
            if should_retry_empty and empty_retries < current_empty_retry_limit:
                empty_retries += 1
                stopped = await self._sleep_for_search_wait(wait_seconds, progress_callback, count_getter, processed_getter, total)
                return not stopped
            return False

        async def after_non_empty_batch():
            nonlocal yielded_total
            if yielded_total >= soft_pause_after:
                yielded_total = 0
                stopped = await self._sleep_for_search_wait(soft_pause_seconds, progress_callback, count_getter, processed_getter, total)
                return not stopped
            await asyncio.sleep(0.2)
            return True

        while not self.stop_requested:
            if remaining is not None and remaining <= 0:
                return
            current_kwargs = dict(kwargs)
            current_kwargs["limit"] = min(batch_size, remaining) if remaining is not None else batch_size
            if offset_id is not None:
                current_kwargs["offset_id"] = offset_id
            if offset_date is not None:
                current_kwargs["offset_date"] = offset_date
            yielded_count = 0
            start_offset_id = offset_id
            try:
                if manual_get_messages:
                    task = asyncio.create_task(tg_client.get_messages(entity, **current_kwargs))
                    done, pending = await asyncio.wait({task}, timeout=batch_timeout)
                    if pending:
                        task.cancel()
                        processed_now = processed_getter()
                        should_retry_empty, _, _ = empty_retry_settings(processed_now)
                        if total is not None:
                            missing_count = max(0, int(total) - int(processed_now))
                        else:
                            missing_count = 0
                        if not ignore_total_completion and processed_now >= empty_retry_after_processed > 0 and missing_count <= 100:
                            return
                        if id_range_fallback and processed_now >= empty_retry_after_processed > 0 and offset_id is not None:
                            async for fallback_message in self._iter_messages_by_id_ranges(tg_client, entity, int(offset_id), progress_callback, count_getter, processed_getter, total, batch_timeout=batch_timeout):
                                yield fallback_message
                            return
                        if should_retry_empty and await retry_empty_batch(processed_now):
                            continue
                        return
                    try:
                        batch = task.result()
                    except asyncio.CancelledError:
                        return
                    if batch is None:
                        messages = []
                    elif isinstance(batch, list):
                        messages = batch
                    else:
                        try:
                            messages = list(batch)
                        except TypeError:
                            messages = [batch]
                    messages = [message for message in messages if getattr(message, "id", None)]
                    if not messages:
                        processed_now = processed_getter()
                        if total is not None:
                            missing_count = max(0, int(total) - int(processed_now))
                        else:
                            missing_count = 0
                        if manual_get_messages and processed_now >= empty_retry_after_processed > 0 and empty_retries >= 2:
                            if ignore_total_completion and total is not None and 0 <= missing_count <= 50:
                                return
                            if not disable_date_fallback and ignore_total_completion and last_message_date is not None and manual_date_fallbacks < 12:
                                offset_date = last_message_date
                                offset_id = None
                                manual_date_fallbacks += 1
                                empty_retries = 0
                                continue
                            if offset_id is not None and manual_boundary_shifts < 80 and (ignore_total_completion or total is None or missing_count > 100):
                                try:
                                    shift = max(1, manual_boundary_shift_size if ignore_total_completion else 1)
                                    offset_id = max(1, int(offset_id) - shift)
                                except Exception:
                                    return
                                manual_boundary_shifts += 1
                                empty_retries = 0
                                continue
                        if not ignore_total_completion and processed_now >= empty_retry_after_processed > 0 and missing_count <= 100:
                            return
                        if id_range_fallback and processed_now >= empty_retry_after_processed > 0 and offset_id is not None:
                            async for fallback_message in self._iter_messages_by_id_ranges(tg_client, entity, int(offset_id), progress_callback, count_getter, processed_getter, total, batch_timeout=batch_timeout):
                                yield fallback_message
                            return
                        if await retry_empty_batch(processed_now):
                            continue
                        return
                    for message in messages:
                        message_id = getattr(message, "id", None)
                        if isinstance(message_id, int) and message_id > 0:
                            offset_id = message_id
                        if getattr(message, "date", None) is not None:
                            last_message_date = message.date
                        offset_date = None
                        yielded_count += 1
                        yielded_total += 1
                        if remaining is not None:
                            remaining -= 1
                        yield message
                        if remaining is not None and remaining <= 0:
                            return
                else:
                    async for message in tg_client.iter_messages(entity, **current_kwargs):
                        message_id = getattr(message, "id", None)
                        if isinstance(message_id, int) and message_id > 0:
                            offset_id = message_id
                        if getattr(message, "date", None) is not None:
                            last_message_date = message.date
                        offset_date = None
                        yielded_count += 1
                        yielded_total += 1
                        if remaining is not None:
                            remaining -= 1
                        yield message
                        if remaining is not None and remaining <= 0:
                            return
                    if yielded_count == 0:
                        processed_now = processed_getter()
                        if await retry_empty_batch(processed_now):
                            continue
                        return
                empty_retries = 0
                manual_boundary_shifts = 0
                manual_date_fallbacks = 0
                if offset_id == start_offset_id and offset_date is None:
                    return
                if not await after_non_empty_batch():
                    return
            except Exception as exc:
                seconds = get_flood_wait_seconds(exc)
                if seconds is None:
                    translated_error = translate_telegram_error(exc)
                    seconds = get_flood_wait_seconds(translated_error)
                if seconds is None:
                    raise
                stopped = await self._sleep_for_search_wait(seconds, progress_callback, count_getter, processed_getter, total)
                if stopped:
                    return


    async def _get_scan_total(self, tg_client: TelegramClient, entity, from_user=None, topic_id: int | None = None) -> int | None:
        try:
            kwargs = {"limit": 0}
            if from_user is not None:
                kwargs["from_user"] = from_user
            if topic_id is not None:
                kwargs["reply_to"] = topic_id
            result = await asyncio.wait_for(tg_client.get_messages(entity, **kwargs), timeout=10)
            total = getattr(result, "total", None)
            return int(total) if total is not None else None
        except Exception:
            return None

    async def find_messages_in_one_chat(
        self,
        tg_client: TelegramClient,
        peer_id: int,
        display_label: str,
        entity,
        terms: list[SearchTerm],
        all_messages_mode: bool,
        limit: int | None,
        found_index: dict[tuple[int, int], FoundMessage],
        progress_callback=None,
        reaction_mode: bool = False,
        voice_mode: bool = False,
        topic_id: int | None = None,
    ) -> bool:
        self.entity_cache[peer_id] = entity
        entity_is_group = is_group_entity(entity)
        entity_export_dialog_type_key = self._export_dialog_type_key_for_entity(entity)
        status_label = self._status_chat_label(display_label, peer_id, topic_id, force_chat_id=entity_is_group)
        my_user_id = None
        if entity_is_group:
            try:
                me = await tg_client.get_me()
                my_user_id = getattr(me, "id", None)
            except Exception:
                my_user_id = None
        from_user = "me" if entity_is_group else None

        def should_keep_message(message) -> bool:
            if not entity_is_group:
                return True
            if getattr(message, "out", False):
                return True
            return my_user_id is not None and getattr(message, "sender_id", None) == my_user_id

        def build_iter_kwargs(**extra):
            kwargs = {key: value for key, value in extra.items() if value is not None}
            if topic_id is not None:
                kwargs["reply_to"] = topic_id
            return kwargs

        def is_plain_link_search_result(message, term: SearchTerm) -> bool:
            return not term.quoted and self._describe_message_content_kind(message) == T.CONTENT_LINK

        async def add_message(message, matched_terms: list[SearchTerm], text_value: str, allow_service: bool = False) -> bool:
            if self._is_service_message(message) and not allow_service:
                return False
            key = (peer_id, message.id)
            if key not in found_index:
                while True:
                    try:
                        sender = await message.get_sender()
                        break
                    except Exception as exc:
                        seconds = get_flood_wait_seconds(exc)
                        if seconds is None:
                            translated_error = translate_telegram_error(exc)
                            seconds = get_flood_wait_seconds(translated_error)
                        if seconds is None:
                            raise
                        stopped = await self._sleep_for_search_wait(seconds, progress_callback, lambda: len(found_index), lambda: 0, None)
                        if stopped:
                            return True
                sender_id = getattr(sender, "id", None) if sender is not None else None
                found_index[key] = FoundMessage(
                    peer_id=peer_id,
                    chat_input=display_label,
                    sender_id=sender_id,
                    sender_name=self._format_sender_label(sender),
                    is_outgoing=bool(getattr(message, "out", False)),
                    message_id=message.id,
                    date=format_message_date(message.date),
                    timestamp=message.date.timestamp(),
                    text=text_value,
                    matched_terms=[],
                    chat_is_group=entity_is_group,
                    content_kind=self._describe_message_content_kind(message),
                    is_reaction=reaction_mode,
                )
                try:
                    found_index[key]._ui_topic_id = topic_id
                    found_index[key]._export_dialog_type_key = entity_export_dialog_type_key
                except Exception:
                    pass
                is_new = True
            else:
                is_new = False
            item = found_index[key]
            if topic_id is not None:
                try:
                    item._ui_topic_id = topic_id
                    item._export_dialog_type_key = entity_export_dialog_type_key
                except Exception:
                    pass
            for matched_term in matched_terms:
                if matched_term.raw not in item.matched_terms:
                    item.matched_terms.append(matched_term.raw)
            if is_new and progress_callback is not None:
                progress_callback({"type": "message", "message": item, "count": len(found_index)})
            return limit is not None and len(found_index) >= limit

        if reaction_mode and not voice_mode:
            async def get_reaction_text(message):
                source_message = message
                text_value = self._compose_message_text(source_message, reaction_mode=True)
                if text_value == T.CONTENT_REACTION_NO_TEXT or not self._message_text_candidates(source_message):
                    for fetch_ids in (message.id, [message.id]):
                        try:
                            fetched = await tg_client.get_messages(entity, ids=fetch_ids)
                        except Exception:
                            fetched = None
                        if isinstance(fetched, list):
                            fetched = fetched[0] if fetched else None
                        if fetched is not None:
                            refreshed_text = self._compose_message_text(fetched, reaction_mode=True)
                            if refreshed_text and refreshed_text != T.CONTENT_REACTION_NO_TEXT:
                                source_message = fetched
                                text_value = refreshed_text
                                break
                return source_message, text_value

            if terms and not all_messages_mode:
                for term in terms:
                    if self.stop_requested:
                        return True
                    processed = 0
                    total = None
                    if progress_callback is not None:
                        progress_callback({"type": "status", "text": T.TELEGRAM_SEARCHING_REACTIONS_CHAT.format(chat=status_label), "count": len(found_index), "chat_progress": True})
                    async for message in self._iter_messages_waiting(tg_client, entity, lambda: len(found_index), lambda: processed, total, progress_callback, **build_iter_kwargs(search=term.value, limit=None)):
                        if self.stop_requested:
                            return True
                        if self._is_service_message(message):
                            continue
                        if is_plain_link_search_result(message, term):
                            continue
                        processed += 1
                        source_message, text_value = await get_reaction_text(message)
                        if term.quoted:
                            matched_terms = match_message(text_value, [term])
                            if not matched_terms:
                                continue
                        else:
                            matched_terms = [term]
                        if not await self._message_has_my_reaction(tg_client, entity, source_message):
                            continue
                        if await add_message(source_message, matched_terms, text_value):
                            return True
                return False

            processed = 0
            total = await self._get_scan_total(tg_client, entity, topic_id=topic_id)
            reaction_retry = all_messages_mode
            reaction_manual = all_messages_mode and entity_is_group
            async for message in self._iter_messages_waiting(tg_client, entity, lambda: len(found_index), lambda: processed, total, progress_callback, **build_iter_kwargs(limit=None, _retry_empty=reaction_retry, _empty_retry_limit=48, _empty_retry_seconds=6, _empty_retry_after_processed=2500, _manual_get_messages=reaction_manual, _ignore_total_completion=reaction_manual, _disable_date_fallback=reaction_manual, _manual_boundary_shift_size=25, _batch_timeout=8 if reaction_manual else 10)):
                if self.stop_requested:
                    return True
                if self._is_service_message(message) and not all_messages_mode:
                    continue
                processed += 1
                if progress_callback is not None and (processed == 1 or processed % 25 == 0):
                    progress_callback({"type": "status", "text": T.TELEGRAM_SEARCHING_REACTIONS_CHAT.format(chat=status_label), "count": len(found_index), "processed": processed, "total": total, "chat_progress": True})
                if not await self._message_has_my_reaction(tg_client, entity, message):
                    continue
                source_message, text_value = await get_reaction_text(message)
                matched_terms = [] if all_messages_mode or not terms else match_message(text_value, terms)
                if terms and not all_messages_mode and not matched_terms:
                    continue
                if await add_message(source_message, matched_terms, text_value, allow_service=all_messages_mode):
                    return True
            if progress_callback is not None:
                progress_callback({"type": "status", "text": T.TELEGRAM_CHECKED_REACTIONS_CHAT.format(chat=status_label), "count": len(found_index), "processed": processed, "total": total})
            return False

        if voice_mode:
            voice_from_user = None if reaction_mode else from_user
            processed = 0
            total = await self._get_scan_total(tg_client, entity, from_user=voice_from_user, topic_id=topic_id)
            if progress_callback is not None:
                progress_callback({"type": "status", "text": T.TELEGRAM_CHECKING_VOICE_CHAT.format(chat=status_label), "count": len(found_index), "processed": processed, "total": total, "chat_progress": True})
            async for message in self._iter_messages_waiting(tg_client, entity, lambda: len(found_index), lambda: processed, total, progress_callback, **build_iter_kwargs(limit=None, from_user=voice_from_user, _retry_empty=all_messages_mode and reaction_mode, _empty_retry_limit=10, _empty_retry_seconds=5, _empty_retry_after_processed=2500)):
                if self.stop_requested:
                    return True
                processed += 1
                if not reaction_mode and not should_keep_message(message):
                    continue
                if progress_callback is not None and (processed == 1 or processed % 25 == 0):
                    progress_callback({"type": "status", "text": T.TELEGRAM_CHECKING_VOICE_CHAT.format(chat=status_label), "count": len(found_index), "processed": processed, "total": total, "chat_progress": True})
                if not self._message_is_voice(message):
                    continue
                if reaction_mode and not await self._message_has_my_reaction(tg_client, entity, message):
                    continue
                cached_text = self._get_cached_voice_transcription(entity, message)
                if cached_text is not None:
                    text_value = cached_text
                else:
                    if progress_callback is not None:
                        status_text = T.TELEGRAM_TRANSCRIBING_ID.format(message_id=message.id)
                        progress_callback({"type": "status", "text": status_text, "count": len(found_index), "processed": processed, "total": total, "chat_progress": True})
                    try:
                        text_value = await self._transcribe_voice_message(tg_client, entity, message)
                    except Exception as exc:
                        translated_error = translate_telegram_error(exc)
                        if is_flood_wait_error(translated_error):
                            raise RuntimeError(translated_error) from exc
                        if is_network_error(translated_error):
                            raise RuntimeError(T.TELEGRAM_ERROR_NETWORK) from exc
                        if all_messages_mode:
                            text_value = ""
                            for fetch_ids in (message.id, [message.id]):
                                try:
                                    fetched = await tg_client.get_messages(entity, ids=fetch_ids)
                                except Exception:
                                    fetched = None
                                if isinstance(fetched, list):
                                    fetched = fetched[0] if fetched else None
                                if fetched is None:
                                    continue
                                try:
                                    text_value = await self._transcribe_voice_message(tg_client, entity, fetched)
                                except Exception as retry_exc:
                                    retry_error = translate_telegram_error(retry_exc)
                                    if is_flood_wait_error(retry_error):
                                        raise RuntimeError(retry_error) from retry_exc
                                    if is_network_error(retry_error):
                                        raise RuntimeError(T.TELEGRAM_ERROR_NETWORK) from retry_exc
                                    text_value = ""
                                if text_value:
                                    message = fetched
                                    break
                            if not text_value:
                                text_value = T.CONTENT_VOICE_NO_TRANSCRIPT
                        else:
                            continue
                if not text_value:
                    text_value = T.CONTENT_VOICE_NO_TRANSCRIPT
                matched_terms = [] if all_messages_mode or not terms else match_transcription_message(text_value, terms)
                if terms and not all_messages_mode and not matched_terms:
                    continue
                if await add_message(message, matched_terms, text_value):
                    return True
            if progress_callback is not None:
                progress_callback({"type": "status", "text": T.TELEGRAM_CHECKED_VOICE_CHAT.format(chat=status_label), "count": len(found_index), "processed": processed, "total": total, "chat_progress": True})
            return False

        if all_messages_mode:
            scan_from_user = from_user if entity_is_group else None
            total = await self._get_scan_total(tg_client, entity, from_user=scan_from_user, topic_id=topic_id)
            processed = 0
            if progress_callback is not None:
                progress_callback({"type": "status", "text": T.TELEGRAM_LOADING_MESSAGES_CHAT.format(chat=status_label), "count": len(found_index), "processed": processed, "total": total, "chat_progress": True})
            async for message in self._iter_messages_waiting(tg_client, entity, lambda: len(found_index), lambda: processed, total, progress_callback, **build_iter_kwargs(limit=None, from_user=scan_from_user, _retry_empty=entity_is_group, _empty_retry_limit=24, _empty_retry_seconds=8, _empty_retry_after_processed=2500, _manual_get_messages=entity_is_group, _batch_timeout=8)):
                if self.stop_requested:
                    return True
                processed += 1
                if progress_callback is not None and (processed == 1 or processed % 25 == 0):
                    progress_callback({"type": "status", "text": T.TELEGRAM_LOADING_MESSAGES_CHAT.format(chat=status_label), "count": len(found_index), "processed": processed, "total": total, "chat_progress": True})
                if not should_keep_message(message):
                    continue
                text_value = self._compose_message_text(message)
                if not text_value:
                    continue
                if await add_message(message, [], text_value):
                    return True
            if progress_callback is not None:
                progress_callback({"type": "status", "text": T.TELEGRAM_LOADED_MESSAGES_CHAT.format(chat=status_label), "count": len(found_index), "processed": processed, "total": total, "chat_progress": True})
        else:
            if entity_is_group:
                for term in terms:
                    if self.stop_requested:
                        return True
                    processed = 0
                    total = None
                    if progress_callback is not None:
                        progress_callback({"type": "status", "text": T.TELEGRAM_SEARCHING_MESSAGES_CHAT.format(chat=status_label), "count": len(found_index), "chat_progress": True})
                    async for message in self._iter_messages_waiting(tg_client, entity, lambda: len(found_index), lambda: processed, total, progress_callback, **build_iter_kwargs(search=term.value, limit=None, from_user=from_user)):
                        if self.stop_requested:
                            return True
                        processed += 1
                        if not should_keep_message(message):
                            continue
                        if is_plain_link_search_result(message, term):
                            continue
                        text_value = self._compose_message_text(message)
                        if not text_value:
                            continue
                        if term.quoted:
                            matched_terms = match_message(text_value, [term])
                            if not matched_terms:
                                continue
                        else:
                            matched_terms = [term]
                        if await add_message(message, matched_terms, text_value):
                            return True
                    if progress_callback is not None:
                        progress_callback({"type": "status", "text": T.TELEGRAM_CHECKED_MESSAGES_CHAT.format(chat=status_label), "count": len(found_index)})
                return False
            if topic_id is not None:
                topic_search_failed = False
                for term in terms:
                    if self.stop_requested:
                        return True
                    processed = 0
                    total = None
                    searching_template = T.TELEGRAM_SEARCHING_MESSAGES_CHAT
                    checked_template = T.TELEGRAM_CHECKED_MESSAGES_CHAT
                    if progress_callback is not None:
                        progress_callback({"type": "status", "text": searching_template.format(chat=status_label), "count": len(found_index), "chat_progress": True})
                    try:
                        async for message in self._iter_messages_waiting(tg_client, entity, lambda: len(found_index), lambda: processed, total, progress_callback, search=term.value, limit=None, from_user=from_user, reply_to=topic_id):
                            if self.stop_requested:
                                return True
                            processed += 1
                            if not should_keep_message(message):
                                continue
                            if is_plain_link_search_result(message, term):
                                continue
                            text_value = self._compose_message_text(message)
                            if not text_value:
                                continue
                            matched_terms = self._match_message_as_topic_search(text_value, [term])
                            if not matched_terms:
                                continue
                            if await add_message(message, matched_terms, text_value):
                                return True
                    except Exception as exc:
                        translated_error = translate_telegram_error(exc)
                        if is_flood_wait_error(translated_error) or is_network_error(translated_error):
                            raise
                        topic_search_failed = True
                        break
                    if progress_callback is not None:
                        progress_callback({"type": "status", "text": checked_template.format(chat=status_label), "count": len(found_index)})
                if topic_search_failed:
                    processed = 0
                    total = await self._get_scan_total(tg_client, entity, from_user=from_user, topic_id=topic_id)
                    if progress_callback is not None:
                        progress_callback({"type": "status", "text": T.TELEGRAM_LOADING_MESSAGES_CHAT.format(chat=status_label), "count": len(found_index), "processed": processed, "total": total})
                    async for message in self._iter_messages_waiting(tg_client, entity, lambda: len(found_index), lambda: processed, total, progress_callback, **build_iter_kwargs(limit=None, from_user=from_user)):
                        if self.stop_requested:
                            return True
                        processed += 1
                        if progress_callback is not None and (processed == 1 or processed % 25 == 0):
                            progress_callback({"type": "status", "text": T.TELEGRAM_LOADING_MESSAGES_CHAT.format(chat=status_label), "count": len(found_index), "processed": processed, "total": total})
                        if not should_keep_message(message):
                            continue
                        text_value = self._compose_message_text(message)
                        if not text_value:
                            continue
                        matched_terms = self._match_message_as_topic_search(text_value, terms)
                        if not matched_terms:
                            continue
                        if await add_message(message, matched_terms, text_value):
                            return True
                    if progress_callback is not None:
                        progress_callback({"type": "status", "text": T.TELEGRAM_LOADED_MESSAGES_CHAT.format(chat=status_label), "count": len(found_index), "processed": processed, "total": total})
            else:
                for term in terms:
                    if self.stop_requested:
                        return True
                    processed = 0
                    total = None
                    searching_template = T.TELEGRAM_SEARCHING_MESSAGES_CHAT
                    checked_template = T.TELEGRAM_CHECKED_MESSAGES_CHAT
                    if progress_callback is not None:
                        progress_callback({"type": "status", "text": searching_template.format(chat=status_label), "count": len(found_index), "chat_progress": True})
                    async for message in self._iter_messages_waiting(tg_client, entity, lambda: len(found_index), lambda: processed, total, progress_callback, search=term.value, limit=None, from_user=from_user):
                        if self.stop_requested:
                            return True
                        processed += 1
                        if not should_keep_message(message):
                            continue
                        if is_plain_link_search_result(message, term):
                            continue
                        text_value = self._compose_message_text(message)
                        if not text_value:
                            continue
                        if term.quoted:
                            matched_terms = match_message(text_value, [term])
                            if not matched_terms:
                                continue
                        else:
                            matched_terms = [term]
                        if await add_message(message, matched_terms, text_value):
                            return True
                    if progress_callback is not None:
                        progress_callback({"type": "status", "text": checked_template.format(chat=status_label), "count": len(found_index)})
        return False

    async def find_messages(
        self,
        chat_inputs: list[str],
        words_input: str,
        limit: int | None,
        all_mode: bool = False,
        all_messages_mode: bool = False,
        only_groups_mode: bool = False,
        progress_callback=None,
        reaction_mode: bool = False,
        voice_mode: bool = False,
    ) -> tuple[list[FoundMessage], list[str], bool, int, int]:
        tg_client = await self.ensure_authorized()
        terms = parse_terms(words_input)
        if not terms and not all_messages_mode:
            return [], [T.SEARCH_WORDS_REQUIRED], False, 0, 0
        if all_mode or only_groups_mode:
            resolved_chats, resolve_errors = await self.resolve_all_searchable_chats(tg_client, groups_only=only_groups_mode)
        else:
            resolved_chats, resolve_errors = await self.resolve_unique_chats(tg_client, chat_inputs)
        errors: list[str] = list(resolve_errors)
        found_index: dict[tuple[int, int], FoundMessage] = {}
        stopped_by_limit = False

        total_chats = len(resolved_chats)
        checked_chats = 0
        for index, (peer_id, display_label, entity, topic_id) in enumerate(resolved_chats, start=1):
            status_label = self._status_chat_label(display_label, peer_id, topic_id, force_chat_id=is_group_entity(entity))
            if self.stop_requested:
                stopped_by_limit = True
                break
            chat_flood_retries = 0
            while not self.stop_requested:
                try:
                    def chat_progress_callback(payload):
                        if progress_callback is None:
                            return
                        if isinstance(payload, dict):
                            payload = dict(payload)
                            if payload.get("chat_progress"):
                                payload.setdefault("checked_chats", checked_chats)
                                payload.setdefault("total_chats", total_chats)
                        progress_callback(payload)

                    stopped_by_limit = await self.find_messages_in_one_chat(
                        tg_client,
                        peer_id,
                        display_label,
                        entity,
                        terms,
                        all_messages_mode,
                        limit,
                        found_index,
                        chat_progress_callback,
                        reaction_mode,
                        voice_mode,
                        topic_id,
                    )
                    checked_chats += 1
                    if progress_callback is not None:
                        progress_callback({
                            "type": "status",
                            "text": T.TELEGRAM_CHAT_CHECKED_CHAT.format(chat=status_label),
                            "count": len(found_index),
                            "checked_chats": checked_chats,
                            "total_chats": total_chats,
                        })
                    break
                except Exception as exc:
                    translated_error = translate_telegram_error(exc)
                    if is_flood_wait_error(translated_error):
                        seconds = get_flood_wait_seconds(exc)
                        if seconds is None:
                            seconds = get_flood_wait_seconds(translated_error)
                        seconds = int(seconds or 10)
                        chat_flood_retries += 1
                        if chat_flood_retries > 12:
                            checked_chats += 1
                            break
                        stopped = await self._sleep_for_search_wait(seconds, progress_callback, lambda: len(found_index), lambda: 0, None)
                        if stopped:
                            stopped_by_limit = True
                            break
                        continue
                    if is_network_error(translated_error):
                        raise RuntimeError(translated_error) from exc
                    checked_chats += 1
                    if not (voice_mode and self._is_soft_transcription_error(translated_error)):
                        errors.append(f"{display_label}: {translated_error}")
                        if progress_callback is not None:
                            progress_callback({
                                "type": "status",
                                "text": T.TELEGRAM_CHAT_ERROR_CHAT.format(chat=status_label),
                                "count": len(found_index),
                                "checked_chats": checked_chats,
                                "total_chats": total_chats,
                            })
                    break
            if stopped_by_limit:
                break
        all_found = list(found_index.values())
        all_found.sort(key=lambda item: item.timestamp, reverse=True)
        return all_found, errors, stopped_by_limit, checked_chats, total_chats