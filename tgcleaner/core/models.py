from dataclasses import dataclass, field
from datetime import datetime
from tgcleaner.core.i18n import T

@dataclass
class SearchTerm:
    raw: str
    value: str
    quoted: bool


@dataclass
class FoundMessage:
    peer_id: int
    chat_input: str
    sender_id: int | None
    sender_name: str
    is_outgoing: bool
    message_id: int
    date: str
    timestamp: float
    text: str
    matched_terms: list[str]
    selected: bool = True
    chat_is_group: bool = False
    content_kind: str = field(default_factory=lambda: T.CONTENT_TEXT)
    is_reaction: bool = False




def format_message_date(dt: datetime) -> str:
    try:
        local_dt = dt.astimezone()
    except Exception:
        local_dt = dt
    return local_dt.strftime("%d.%m.%Y %H:%M")


def gradient_for_sender(sender_key: str, is_outgoing: bool) -> tuple[str, str]:
    if is_outgoing:
        return "#2AABEE", "#48C6EF"
    incoming_palettes = [
        ("#7C4DFF", "#B47CFF"),
        ("#FF5E8A", "#FF8A6B"),
        ("#8E44AD", "#C77DFF"),
        ("#D35400", "#FF9F43"),
        ("#5B7CFF", "#89A5FF"),
        ("#E84393", "#FF88B8"),
        ("#6C5CE7", "#B29CFE"),
        ("#FF7675", "#FFB087"),
        ("#9B59B6", "#D2A8FF"),
        ("#F368E0", "#FF9FF3"),
        ("#4B7BEC", "#A5B8FF"),
        ("#A55EEA", "#D6A2FF"),
    ]
    index = abs(hash(sender_key or "user")) % len(incoming_palettes)
    return incoming_palettes[index]