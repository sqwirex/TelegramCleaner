from pathlib import Path
import asyncio
import shutil
import tempfile
import uuid

from telethon import TelegramClient
try:
    from telethon.errors import AuthKeyUnregisteredError, SessionPasswordNeededError
except Exception:
    try:
        from telethon.errors.rpcerrorlist import AuthKeyUnregisteredError, SessionPasswordNeededError
    except Exception:
        class AuthKeyUnregisteredError(Exception):
            pass

        class SessionPasswordNeededError(Exception):
            pass

from tgcleaner.core.config import APP_NAME, make_session_name
from tgcleaner.core.i18n import T, translate_telegram_error, is_flood_wait_error


def _is_invalid_session_error(error: Exception) -> bool:
    name = type(error).__name__.lower()
    text = str(error).lower()
    markers = (
        "authkeyunregistered",
        "auth key unregistered",
        "auth_key_unregistered",
        "session",
        "database disk image is malformed",
        "file is not a database",
        "not a database",
        "malformed",
        "sqlite",
    )
    return any(marker in name or marker in text for marker in markers)


def _raise_auth_start_error(error: Exception) -> None:
    translated_error = translate_telegram_error(error)
    if is_flood_wait_error(translated_error):
        raise RuntimeError(translated_error) from error
    if _is_invalid_session_error(error):
        raise RuntimeError(T.TELEGRAM_SESSION_REJECTED) from error
    raise RuntimeError(T.TELEGRAM_ERROR_NETWORK) from error


def _session_files(session_name: str) -> list[Path]:
    base = Path(session_name)
    return [
        base.with_suffix(".session"),
        Path(str(base) + ".session-journal"),
        Path(str(base) + ".session-wal"),
        Path(str(base) + ".session-shm"),
    ]


def _delete_session_files(session_name: str) -> None:
    for path in _session_files(session_name):
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass


def _remove_empty_parent(session_name: str) -> None:
    auth_dir = Path(session_name).parent
    for directory in (auth_dir, auth_dir.parent):
        try:
            directory.rmdir()
        except Exception:
            pass


class TelegramClientAuthMixin:
    def _create_client(self, session_name: str, api_id: int, api_hash: str) -> TelegramClient:
        return TelegramClient(
            session_name,
            api_id,
            api_hash,
            request_retries=0,
            connection_retries=0,
            retry_delay=0,
            timeout=7,
        )

    def _make_temp_session_name(self, phone: str) -> str:
        temp_root = Path(tempfile.gettempdir()) / APP_NAME / "auth"
        temp_root.mkdir(parents=True, exist_ok=True)
        digits = "".join(ch for ch in phone if ch.isdigit()) or "phone"
        return str(temp_root / f"tg_cleaner_session_{digits}_{uuid.uuid4().hex}")

    async def disconnect_current(self) -> None:
        if self.client is not None:
            try:
                if self.client.is_connected():
                    await self.client.disconnect()
                else:
                    self.client.session.close()
            except Exception:
                pass
        self.client = None
        self.current_phone = None
        self.current_api_id = None
        self.current_api_hash = None
        self.current_username = None
        self.current_session_name = None
        self.entity_cache = {}
        self.voice_transcription_cache = None
        self.stop_requested = False

    async def get_client(self, api_id: int, api_hash: str, phone: str, session_name: str | None = None, create_dir: bool = True) -> TelegramClient:
        target_session_name = session_name or make_session_name(phone, create_dir=create_dir)
        if (
            self.client is None
            or self.current_phone != phone
            or self.current_api_id != api_id
            or self.current_api_hash != api_hash
            or getattr(self, "current_session_name", None) != target_session_name
        ):
            await self.disconnect_current()
            self.client = self._create_client(target_session_name, api_id, api_hash)
            self.current_phone = phone
            self.current_api_id = api_id
            self.current_api_hash = api_hash
            self.current_session_name = target_session_name
        if not self.client.is_connected():
            try:
                await asyncio.wait_for(self.client.connect(), timeout=9)
            except Exception as exc:
                _raise_auth_start_error(exc)
        return self.client

    async def _promote_temp_session(self, temp_session_name: str, final_session_name: str, api_id: int, api_hash: str, phone: str) -> None:
        if self.client is not None:
            try:
                self.client.session.save()
            except Exception:
                pass
        await self.disconnect_current()
        final_base = Path(final_session_name)
        final_base.parent.mkdir(parents=True, exist_ok=True)
        _delete_session_files(final_session_name)
        temp_files = _session_files(temp_session_name)
        final_files = _session_files(final_session_name)
        if not temp_files[0].exists():
            raise RuntimeError(T.TELEGRAM_SESSION_REJECTED)
        shutil.move(str(temp_files[0]), str(final_files[0]))
        for source_path, target_path in zip(temp_files[1:], final_files[1:]):
            if source_path.exists():
                try:
                    shutil.move(str(source_path), str(target_path))
                except Exception:
                    pass
        _remove_empty_parent(temp_session_name)
        self.client = self._create_client(final_session_name, api_id, api_hash)
        self.current_phone = phone
        self.current_api_id = api_id
        self.current_api_hash = api_hash
        self.current_session_name = final_session_name
        try:
            await asyncio.wait_for(self.client.connect(), timeout=9)
        except Exception as exc:
            _raise_auth_start_error(exc)

    async def _refresh_current_username(self, tg_client: TelegramClient) -> None:
        try:
            me = await asyncio.wait_for(tg_client.get_me(), timeout=8)
            username = getattr(me, "username", None) or ""
            self.current_username = username.lstrip("@").lower() or None
        except Exception:
            self.current_username = None

    async def check_authorized(self, api_id: int, api_hash: str, phone: str) -> bool:
        try:
            tg_client = await asyncio.wait_for(self.get_client(api_id, api_hash, phone), timeout=12)
            authorized = bool(await asyncio.wait_for(tg_client.is_user_authorized(), timeout=8))
            if authorized:
                await self._refresh_current_username(tg_client)
            else:
                self.current_username = None
            return authorized
        except RuntimeError:
            raise
        except Exception as exc:
            _raise_auth_start_error(exc)

    async def send_login_code(self, api_id: int, api_hash: str, phone: str) -> None:
        temp_session_name = self._make_temp_session_name(phone)
        final_session_name = make_session_name(phone, create_dir=False)
        try:
            tg_client = await self.get_client(api_id, api_hash, phone, session_name=temp_session_name, create_dir=False)
            result = await asyncio.wait_for(tg_client.send_code_request(phone), timeout=12)
        except asyncio.TimeoutError as exc:
            await self.disconnect_current()
            _delete_session_files(temp_session_name)
            _remove_empty_parent(temp_session_name)
            raise RuntimeError(T.TELEGRAM_ERROR_NETWORK) from exc
        except AuthKeyUnregisteredError as exc:
            await self.disconnect_current()
            _delete_session_files(temp_session_name)
            _remove_empty_parent(temp_session_name)
            raise RuntimeError(T.TELEGRAM_SESSION_REJECTED) from exc
        except Exception:
            await self.disconnect_current()
            _delete_session_files(temp_session_name)
            _remove_empty_parent(temp_session_name)
            raise
        self.phone_code_hash = result.phone_code_hash
        try:
            await self._promote_temp_session(temp_session_name, final_session_name, api_id, api_hash, phone)
        except Exception:
            _delete_session_files(temp_session_name)
            _remove_empty_parent(temp_session_name)
            raise

    async def sign_in_with_code(self, api_id: int, api_hash: str, phone: str, code: str) -> None:
        tg_client = await self.get_client(api_id, api_hash, phone)
        try:
            if self.phone_code_hash:
                await asyncio.wait_for(tg_client.sign_in(phone=phone, code=code, phone_code_hash=self.phone_code_hash), timeout=12)
            else:
                await asyncio.wait_for(tg_client.sign_in(phone=phone, code=code), timeout=12)
        except asyncio.TimeoutError as exc:
            raise RuntimeError(T.TELEGRAM_ERROR_NETWORK) from exc
        except AuthKeyUnregisteredError as exc:
            raise RuntimeError(T.TELEGRAM_SESSION_REJECTED) from exc
        except SessionPasswordNeededError:
            raise
        await self._refresh_current_username(tg_client)

    async def sign_in_with_password(self, api_id: int, api_hash: str, phone: str, password: str) -> None:
        tg_client = await self.get_client(api_id, api_hash, phone)
        try:
            await asyncio.wait_for(tg_client.sign_in(password=password), timeout=12)
        except asyncio.TimeoutError as exc:
            raise RuntimeError(T.TELEGRAM_ERROR_NETWORK) from exc
        except AuthKeyUnregisteredError as exc:
            raise RuntimeError(T.TELEGRAM_SESSION_REJECTED) from exc
        await self._refresh_current_username(tg_client)

    async def ensure_authorized(self) -> TelegramClient:
        if self.client is None:
            raise RuntimeError("Telegram client is not authorized")
        if not self.client.is_connected():
            try:
                await asyncio.wait_for(self.client.connect(), timeout=9)
            except Exception as exc:
                translated_error = translate_telegram_error(exc)
                if is_flood_wait_error(translated_error):
                    raise RuntimeError(translated_error) from exc
                raise RuntimeError(T.TELEGRAM_ERROR_NETWORK) from exc
        try:
            authorized = await asyncio.wait_for(self.client.is_user_authorized(), timeout=8)
        except Exception as exc:
            _raise_auth_start_error(exc)
        if not authorized:
            raise RuntimeError("Telegram client is not authorized")
        return self.client