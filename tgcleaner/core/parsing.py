import re
import unicodedata
from dataclasses import dataclass

from .models import FoundMessage, SearchTerm
from tgcleaner.core.i18n import T

def parse_chats(raw_text: str) -> list[str]:
    return [line.strip() for line in raw_text.splitlines() if line.strip()]


@dataclass(frozen=True)
class ChatReference:
    normalized: str
    topic_id: int | None = None
    validate_topic: bool = False


def _int_or_none(value: str | None) -> int | None:
    if value is None:
        return None
    value = value.strip()
    if not value.isdigit():
        return None
    try:
        return int(value)
    except Exception:
        return None


def _extract_topic_id_from_query(query: str) -> int | None:
    if not query:
        return None
    match = re.search(r"(?:^|&)(?:topic|topic_id|thread|thread_id|comment)=(\d+)(?:&|$)", query, flags=re.IGNORECASE)
    return _int_or_none(match.group(1)) if match else None


def parse_chat_reference(raw_value: str) -> ChatReference:
    value = raw_value.strip()
    topic_id = None
    if not value:
        return ChatReference(value)

    query = ""
    if "?" in value:
        value, query = value.split("?", 1)
        topic_id = _extract_topic_id_from_query(query)

    tg_chat_match = re.search(r"^tg://chat\?id=[\"']?([^\"'&]+)[\"']?", raw_value.strip(), flags=re.IGNORECASE)
    if tg_chat_match:
        return ChatReference(tg_chat_match.group(1), topic_id, topic_id is not None)

    tg_user_match = re.search(r"^tg://user\?id=[\"']?([^\"'&]+)[\"']?", raw_value.strip(), flags=re.IGNORECASE)
    if tg_user_match:
        return ChatReference(tg_user_match.group(1), topic_id, topic_id is not None)

    tg_open_message_match = re.search(r"^tg://openmessage\?.*?(?:chat_id|user_id)=[\"']?([^\"'&]+)[\"']?", raw_value.strip(), flags=re.IGNORECASE)
    if tg_open_message_match:
        query_source = raw_value.strip().split("?", 1)[1] if "?" in raw_value.strip() else ""
        topic_candidate = topic_id or _extract_topic_id_from_query(query_source)
        return ChatReference(tg_open_message_match.group(1), topic_candidate, topic_candidate is not None)

    tg_privatepost_match = re.search(r"^tg://privatepost\?.*?channel=[\"']?([^\"'&]+)[\"']?", raw_value.strip(), flags=re.IGNORECASE)
    if tg_privatepost_match:
        raise ValueError(T.TELEGRAM_UNSUPPORTED_DIALOG_TYPE)

    tg_match = re.search(r"^tg://resolve\?domain=([^&]+)", raw_value.strip(), flags=re.IGNORECASE)
    if tg_match:
        return ChatReference("@" + re.sub(r"^@", "", tg_match.group(1)), topic_id, topic_id is not None)

    value = re.sub(r"^https?://", "", value, flags=re.IGNORECASE)
    value = re.sub(r"^telegram\.dog/", "", value, flags=re.IGNORECASE)
    value = re.sub(r"^telegram\.me/", "", value, flags=re.IGNORECASE)
    value = re.sub(r"^t\.me/", "", value, flags=re.IGNORECASE)
    value = re.sub(r"^@", "", value)

    if value.startswith("s/"):
        parts = value.split("/")
        if len(parts) >= 2:
            value = "/".join(parts[1:])

    if value.startswith("c/"):
        parts = value.split("/")
        if len(parts) >= 2 and parts[1].isdigit():
            numeric_tail = [part for part in parts[2:] if part.isdigit()]
            validate_topic = topic_id is not None
            if topic_id is None and numeric_tail:
                topic_id = int(numeric_tail[0])
                validate_topic = True
            return ChatReference(f"-100{parts[1]}", topic_id, validate_topic)

    if value.startswith("joinchat/") or value.startswith("+"):
        return ChatReference(value, topic_id, topic_id is not None)

    parts = value.split("/") if value else []
    validate_topic = topic_id is not None
    if parts and len(parts) >= 2 and parts[1].isdigit() and topic_id is None:
        topic_id = int(parts[1])
        validate_topic = True
    if parts:
        value = parts[0]

    if value and not re.fullmatch(r"[+-]?\d+", value):
        value = "@" + value
    return ChatReference(value, topic_id, validate_topic)

def _is_quoted_term(value: str) -> bool:
    return len(value) >= 2 and value.startswith('"') and value.endswith('"')


def _strip_term_quotes(value: str) -> str:
    if _is_quoted_term(value):
        return value[1:-1].strip()
    return value.strip()


def parse_terms(raw_text: str) -> list[SearchTerm]:
    terms: list[SearchTerm] = []
    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue
        quoted = _is_quoted_term(line)
        value = (_strip_term_quotes(line) if quoted else line).casefold()
        if value:
            terms.append(SearchTerm(raw=line, value=value, quoted=quoted))
    return terms


def contains_exact_word_or_phrase(text: str, phrase: str) -> bool:
    pattern = rf"(?<![\w]){re.escape(phrase)}(?![\w])"
    return re.search(pattern, text, flags=re.IGNORECASE | re.UNICODE) is not None


def normalize_transcription_search_text(text: str) -> str:
    normalized = "".join(" " if unicodedata.category(char).startswith("P") else char for char in str(text or ""))
    return re.sub(r"\s+", " ", normalized.casefold()).strip()


def match_transcription_message(text: str, terms: list[SearchTerm]) -> list[SearchTerm]:
    text_normalized = normalize_transcription_search_text(text)
    matched = []
    for term in terms:
        value = normalize_transcription_search_text(term.value)
        if not value:
            continue
        if term.quoted:
            if contains_exact_word_or_phrase(text_normalized, value):
                matched.append(term)
        else:
            if value in text_normalized:
                matched.append(term)
    return matched


def match_message(text: str, terms: list[SearchTerm]) -> list[SearchTerm]:
    text_normalized = text.casefold()
    matched = []
    for term in terms:
        if term.quoted:
            if contains_exact_word_or_phrase(text_normalized, term.value):
                matched.append(term)
        else:
            if term.value in text_normalized:
                matched.append(term)
    return matched


def display_sender_name(message: FoundMessage) -> str:
    return T.CONTENT_YOU if message.is_outgoing else message.sender_name