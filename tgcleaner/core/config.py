import re
import sys
from pathlib import Path

try:
    import winreg
except Exception:
    winreg = None

APP_NAME = "TelegramCleaner"
ADMIN_USERNAME = ""
REG_PATH = rf"Software\{APP_NAME}"
USERS_DIR = "users"

from tgcleaner.core.i18n import T


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def resource_path(relative_path: str) -> str:
    base_path = getattr(sys, "_MEIPASS", app_dir())
    return str(Path(base_path) / relative_path)


def users_dir(create: bool = False) -> Path:
    path = app_dir() / USERS_DIR
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def normalize_phone(phone: str) -> str:
    safe_phone = re.sub(r"\D+", "", phone or "")
    if not safe_phone:
        raise ValueError(T.AUTH_PHONE_REQUIRED)
    return safe_phone


def user_session_dir(phone: str, create: bool = False) -> Path:
    path = users_dir(create) / normalize_phone(phone)
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def _session_base_files(base: Path) -> list[Path]:
    return [
        base.with_suffix(".session"),
        Path(str(base) + ".session-journal"),
        Path(str(base) + ".session-wal"),
        Path(str(base) + ".session-shm"),
    ]


def _session_base(phone: str, create_dir: bool = False) -> Path:
    return user_session_dir(phone, create_dir) / "tg_cleaner_session"


def read_saved_fields() -> dict[str, str]:
    values = {"api_id": "", "api_hash": "", "phone": "", "language": "en", "simple_render": "0"}
    if winreg is None:
        return values
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_READ)
        for name in values:
            try:
                values[name] = str(winreg.QueryValueEx(key, name)[0])
            except Exception:
                values[name] = ""
        winreg.CloseKey(key)
    except Exception:
        pass
    return values


def save_saved_field(name: str, value: str) -> None:
    if winreg is None:
        return
    try:
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_PATH)
        winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
        winreg.CloseKey(key)
    except Exception:
        pass


def make_session_name(phone: str, create_dir: bool = False) -> str:
    return str(_session_base(phone, create_dir=create_dir))


def session_related_files(phone: str) -> list[Path]:
    return _session_base_files(Path(make_session_name(phone)))


def has_session_file(phone: str) -> bool:
    try:
        return Path(make_session_name(phone)).with_suffix(".session").exists()
    except Exception:
        return False