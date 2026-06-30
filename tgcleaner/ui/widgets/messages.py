from PySide6.QtCore import QPointF, QRect, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QLinearGradient, QPainter, QPainterPath, QPen, QTextLayout, QTextOption
from PySide6.QtWidgets import QStyledItemDelegate

from tgcleaner.core.i18n import T, translate_content_kind, translate_runtime_text
from tgcleaner.core.models import gradient_for_sender
from tgcleaner.core.parsing import display_sender_name


class MessageListDelegate(QStyledItemDelegate):
    def _language_cache_key(self):
        return (
            T.CONTENT_TEXT,
            T.CONTENT_WITHOUT_TEXT_SUFFIX,
            T.CONTENT_MESSAGE_NO_TEXT,
            T.EXPORT_DIALOG,
            T.CONTENT_MESSAGE_LABEL,
        )

    def _simple_render_enabled(self, option=None) -> bool:
        view = option.widget if option is not None else self.parent()
        if view is None:
            return False
        window = view.window()
        return bool(getattr(window, "simple_render_enabled", False))

    def _stable_paint_option(self, option, index):
        return option

    def _message_simple_render_enabled(self, data, option=None) -> bool:
        if isinstance(data, dict) and "simple_render" in data:
            return bool(data.get("simple_render"))
        return self._simple_render_enabled(option)

    def prepare_message_cache(self, message, option=None, width: int | None = None):
        self._display_text(message)
        self._header_texts(message)
        if option is not None and self._simple_render_enabled(option):
            if width is not None:
                self._simple_message_size_hint(option, message, width)
            return
        self._gradient_colors(message)
        if option is not None and width is not None:
            self._message_size_hint(option, message, width)

    def clear_message_cache(self, message):
        for attr in (
            "_ui_display_text_cache",
            "_ui_header_texts_cache",
            "_ui_gradient_cache",
            "_ui_bubble_width_cache",
            "_ui_message_rects_cache",
            "_ui_size_hint_cache",
            "_ui_simple_size_hint_cache",
        ):
            if hasattr(message, attr):
                try:
                    delattr(message, attr)
                except Exception:
                    pass

    def _short_chat_title(self, title: str, limit: int = 30) -> str:
        text = str(title or "").strip()
        if not text or len(text) <= limit:
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

    def _header_sender_label(self, message) -> str:
        sender = display_sender_name(message)
        if sender:
            return str(sender).strip()
        sender_id = getattr(message, "sender_id", None)
        return str(sender_id or "").strip()

    def _header_chat_parts(self, message):
        label = str(getattr(message, "chat_input", "") or "").strip()
        title, sep, suffix = label.partition(" • ")
        title = self._short_chat_title(title, 30)
        prefix = T.EXPORT_DIALOG.format(value="")
        show_sender = bool(getattr(message, "chat_is_group", False)) and not bool(getattr(message, "is_outgoing", False))
        parts = []
        topic_id = getattr(message, "_ui_topic_id", None)
        if bool(getattr(message, "_ui_show_topic_id", False)) and topic_id is not None:
            parts.append(T.TELEGRAM_TOPIC_ID.format(topic_id=topic_id))
        elif sep and suffix:
            cleaned_suffix = str(suffix or "").strip()
            suffix_lower = cleaned_suffix.lower()
            if cleaned_suffix and ("topic id" in suffix_lower or "топик id" in suffix_lower):
                if bool(getattr(message, "_ui_show_topic_id", False)):
                    parts.append(cleaned_suffix)
            elif cleaned_suffix:
                parts.append(cleaned_suffix)
        if show_sender:
            sender = self._header_sender_label(message)
            if sender:
                sender_part = f"{T.CONTENT_MESSAGE_LABEL}: {sender}"
                if not any(sender_part.lower() == part.lower() for part in parts):
                    parts.append(sender_part)
        extra = ""
        if parts:
            extra = " • " + " • ".join(parts)
        return prefix, title, extra

    def _normalize_display_text(self, text: str) -> str:
        value = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
        for char in ("\u200b", "\u200c", "\u200d", "\ufeff"):
            value = value.replace(char, "")
        lines = [line.rstrip() for line in value.split("\n")]
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()
        normalized = []
        blank_added = False
        for line in lines:
            if line.strip():
                normalized.append(line)
                blank_added = False
            elif not blank_added:
                normalized.append("")
                blank_added = True
        return "\n".join(normalized).strip()

    def _build_text_layouts(self, font: QFont, text: str, width: float):
        option = QTextOption()
        option.setWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        metrics = QFontMetrics(font)
        layouts = []
        y = 0.0
        text_value = str(text or " ").replace("\r\n", "\n").replace("\r", "\n")
        paragraphs = text_value.split("\n") or [" "]
        line_width = max(1.0, float(width))
        for paragraph in paragraphs:
            if paragraph == "":
                y += metrics.lineSpacing()
                continue
            layout = QTextLayout(paragraph, font)
            layout.setTextOption(option)
            layout.beginLayout()
            local_y = 0.0
            while True:
                line = layout.createLine()
                if not line.isValid():
                    break
                line.setLineWidth(line_width)
                line.setPosition(QPointF(0.0, local_y))
                local_y += line.height()
            layout.endLayout()
            if local_y <= 0.0:
                local_y = metrics.lineSpacing()
            layouts.append((layout, y))
            y += local_y
        return layouts, y

    def _wrapped_text_height(self, font: QFont, text: str, width: int) -> int:
        layouts, height = self._build_text_layouts(font, text, width)
        if height <= 0:
            return QFontMetrics(font).lineSpacing()
        return max(18, int(height + 0.999))

    def _draw_wrapped_text(self, painter: QPainter, rect: QRectF, text: str, clip_rect: QRectF | None = None):
        layouts, _ = self._build_text_layouts(painter.font(), text, rect.width())
        painter.save()
        if clip_rect is not None:
            painter.setClipRect(clip_rect)
        origin = rect.topLeft()
        for layout, y in layouts:
            layout.draw(painter, QPointF(origin.x(), origin.y() + y))
        painter.restore()

    def _text_natural_width(self, font: QFont, text: str) -> int:
        metrics = QFontMetrics(font)
        lines = str(text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
        if not lines:
            return metrics.horizontalAdvance(" ")
        return max(metrics.horizontalAdvance(line or " ") for line in lines)

    def _display_text(self, message) -> str:
        raw_text = getattr(message, "text", "") or ""
        raw_kind = (getattr(message, "content_kind", "") or "").strip()
        key = (raw_text, raw_kind, self._language_cache_key()[:3])
        cached = getattr(message, "_ui_display_text_cache", None)
        if cached and cached[0] == key:
            return cached[1]
        text = self._normalize_display_text(translate_runtime_text(raw_text))
        if text:
            value = text
        else:
            kind = translate_content_kind(raw_kind)
            if kind and kind != T.CONTENT_TEXT:
                value = f"[{kind}{T.CONTENT_WITHOUT_TEXT_SUFFIX}"
            else:
                value = T.CONTENT_MESSAGE_NO_TEXT
        try:
            message._ui_display_text_cache = (key, value)
        except Exception:
            pass
        return value

    def _header_texts(self, message):
        key = (
            getattr(message, "is_reaction", False),
            getattr(message, "chat_is_group", False),
            getattr(message, "is_outgoing", False),
            getattr(message, "chat_input", ""),
            getattr(message, "sender_name", ""),
            getattr(message, "sender_id", None),
            getattr(message, "message_id", None),
            getattr(message, "date", ""),
            getattr(message, "_ui_show_topic_id", False),
            T.EXPORT_DIALOG,
            T.CONTENT_MESSAGE_LABEL,
        )
        cached = getattr(message, "_ui_header_texts_cache", None)
        if cached and cached[0] == key:
            return cached[1]
        prefix, chat_title, suffix = self._header_chat_parts(message)
        chat_text = f"{prefix}{chat_title}{suffix}"
        meta_text = f"{message.date}"
        value = (chat_text, meta_text)
        try:
            message._ui_header_texts_cache = (key, value)
        except Exception:
            pass
        return value

    def _gradient_colors(self, message):
        key = (getattr(message, "sender_name", "") or str(getattr(message, "sender_id", "") or ""), getattr(message, "is_outgoing", False))
        cached = getattr(message, "_ui_gradient_cache", None)
        if cached and cached[0] == key:
            return cached[1]
        value = gradient_for_sender(key[0], key[1])
        try:
            message._ui_gradient_cache = (key, value)
        except Exception:
            pass
        return value

    def _mix_color(self, foreground: QColor, background: QColor, ratio: float) -> QColor:
        ratio = max(0.0, min(1.0, float(ratio)))
        inverse = 1.0 - ratio
        return QColor(
            int(foreground.red() * ratio + background.red() * inverse),
            int(foreground.green() * ratio + background.green() * inverse),
            int(foreground.blue() * ratio + background.blue() * inverse),
        )

    def _simple_message_colors(self, message, checked: bool):
        start_color, end_color = self._gradient_colors(message)
        accent = QColor(start_color)
        accent_light = QColor(end_color)
        base = QColor("#0A1621")
        selected_base = QColor("#111F2B")
        if checked:
            background = self._mix_color(accent, selected_base, 0.18)
            border = self._mix_color(accent_light, QColor("#263747"), 0.64)
        else:
            background = base
            border = self._mix_color(accent, QColor("#203040"), 0.36)
        checkbox_background = accent if checked else QColor("#111F2B")
        checkbox_border = accent if checked else self._mix_color(accent, QColor("#5B7284"), 0.72)
        return accent, background, border, checkbox_background, checkbox_border

    def _bubble_width(self, option, message, content_width: float) -> float:
        max_width = min(860.0, max(240.0, content_width * 0.90))
        key = (
            int(max_width),
            int(content_width),
            option.font.toString(),
            self._language_cache_key(),
            getattr(message, "message_id", None),
            getattr(message, "chat_input", ""),
            getattr(message, "sender_name", ""),
            getattr(message, "sender_id", None),
            getattr(message, "date", ""),
            getattr(message, "text", ""),
            getattr(message, "content_kind", ""),
            getattr(message, "is_reaction", False),
            getattr(message, "chat_is_group", False),
            getattr(message, "_ui_show_topic_id", False),
        )
        cached = getattr(message, "_ui_bubble_width_cache", None)
        if cached and cached[0] == key:
            return cached[1]
        min_width = 190.0
        font = option.font
        metrics = option.fontMetrics

        chat_text, meta_text = self._header_texts(message)

        header_font = QFont(font)
        header_font.setBold(True)
        header_metrics = QFontMetrics(header_font)

        header_width = header_metrics.horizontalAdvance(chat_text) + metrics.horizontalAdvance(meta_text) + 52
        one_line_text_width = self._text_natural_width(font, self._display_text(message)) + 34

        target_width = max(min_width, header_width, min(one_line_text_width, max_width * 0.92))
        if target_width > max_width:
            target_width = max_width
        try:
            message._ui_bubble_width_cache = (key, target_width)
        except Exception:
            pass
        return target_width

    def _message_body_height(self, option, message, bubble_width: float) -> float:
        text_width = max(1.0, float(bubble_width) - 32.0)
        return float(self._wrapped_text_height(option.font, self._display_text(message), int(text_width)))

    def _message_rects(self, option, message):
        rect = QRectF(option.rect)
        key = (
            int(rect.x()),
            int(rect.y()),
            int(rect.width()),
            option.font.toString(),
            self._language_cache_key(),
            getattr(message, "is_outgoing", False),
            getattr(message, "message_id", None),
            getattr(message, "text", ""),
            getattr(message, "content_kind", ""),
        )
        cached = getattr(message, "_ui_message_rects_cache", None)
        if cached and cached[0] == key:
            return cached[1]
        row_rect = rect.adjusted(8, 8, -8, -8)
        content_rect = QRectF(row_rect.adjusted(34, 0, -4, 0))
        bubble_width = self._bubble_width(option, message, content_rect.width())
        body_height = self._message_body_height(option, message, bubble_width)
        bubble_height = max(38.0, body_height + 24.0)
        if message.is_outgoing:
            bubble_x = content_rect.right() - bubble_width
        else:
            bubble_x = content_rect.left() - 16
        header_rect = QRectF(bubble_x, row_rect.top(), bubble_width, 22)
        bubble_rect = QRectF(bubble_x, row_rect.top() + 26, bubble_width, bubble_height)
        check_size = 20
        if message.is_outgoing:
            check_x = max(row_rect.left() + 2, bubble_rect.left() - check_size - 14)
        else:
            check_x = min(row_rect.right() - check_size - 2, bubble_rect.right() + 14)
        check_y = bubble_rect.top() + (bubble_rect.height() - check_size) / 2
        check_rect = QRectF(check_x, check_y, check_size, check_size)
        value = (header_rect, bubble_rect, check_rect)
        try:
            message._ui_message_rects_cache = (key, value)
        except Exception:
            pass
        return value

    def _simple_message_rects(self, option, message):
        rect = QRectF(option.rect)
        row_rect = rect.adjusted(8, 3, -8, -3)
        check_size = 18.0
        check_rect = QRectF(row_rect.left() + 8.0, row_rect.top() + max(0.0, (row_rect.height() - check_size) / 2.0), check_size, check_size)
        content_rect = QRectF(row_rect.left() + 38.0, row_rect.top() + 6.0, max(80.0, row_rect.width() - 50.0), max(20.0, row_rect.height() - 14.0))
        header_rect = QRectF(content_rect.left(), content_rect.top(), content_rect.width(), 20.0)
        body_rect = QRectF(content_rect.left(), header_rect.bottom() + 2.0, content_rect.width(), max(20.0, content_rect.bottom() - header_rect.bottom() - 2.0))
        return row_rect, header_rect, body_rect, check_rect

    def _simple_text_height(self, font: QFont, text: str, width: int) -> int:
        metrics = QFontMetrics(font)
        return self._wrapped_text_height(font, text, width) + max(4, metrics.descent() + 2)

    def _draw_simple_text(self, painter: QPainter, rect: QRectF, text: str):
        self._draw_wrapped_text(painter, rect, text or " ", rect.adjusted(0.0, -3.0, 10.0, 12.0))

    def _simple_message_size_hint(self, option, message, width: int):
        key = (
            width,
            self._language_cache_key(),
            option.font.toString(),
            getattr(message, "message_id", None),
            getattr(message, "chat_input", ""),
            getattr(message, "sender_name", ""),
            getattr(message, "sender_id", None),
            getattr(message, "date", ""),
            getattr(message, "text", ""),
            getattr(message, "content_kind", ""),
            getattr(message, "is_outgoing", False),
            getattr(message, "is_reaction", False),
            getattr(message, "chat_is_group", False),
            getattr(message, "_ui_show_topic_id", False),
        )
        cached = getattr(message, "_ui_simple_size_hint_cache", None)
        if cached and cached[0] == key:
            return cached[1]
        text_width = max(120, width - 66)
        body_text = self._display_text(message)
        body_height = self._simple_text_height(option.font, body_text, text_width)
        size = QSize(width, max(64, int(body_height + 64)))
        try:
            message._ui_simple_size_hint_cache = (key, size)
        except Exception:
            pass
        return size

    def _paint_simple_message(self, painter, option, index, data, message):
        row_rect, header_rect, body_rect, check_rect = self._simple_message_rects(option, message)
        checked = bool(getattr(message, "selected", data.get("selected", index.data(Qt.CheckStateRole) != Qt.Unchecked)))
        current = False
        view = option.widget
        if view is not None and view.hasFocus():
            try:
                current = view.currentIndex() == index
            except Exception:
                current = False
        accent, background, border, checkbox_background, checkbox_border = self._simple_message_colors(message, checked)
        painter.setRenderHint(QPainter.Antialiasing, False)
        painter.setPen(QPen(border, 1))
        painter.setBrush(background)
        painter.drawRect(row_rect)
        painter.fillRect(QRectF(row_rect.left(), row_rect.top(), 3.0, row_rect.height()), accent)
        painter.setPen(QPen(checkbox_border, 1))
        painter.setBrush(checkbox_background)
        painter.drawRect(check_rect)
        if checked:
            check_font = QFont(option.font)
            check_font.setBold(True)
            painter.setFont(check_font)
            painter.setPen(QColor("#FFFFFF"))
            painter.drawText(check_rect, Qt.AlignCenter, "✓")
        chat_text, meta_text = self._header_texts(message)
        header_font = QFont(option.font)
        header_font.setBold(True)
        painter.setFont(header_font)
        header_metrics = QFontMetrics(header_font)
        meta_width = min(max(96, header_metrics.horizontalAdvance(meta_text) + 12), max(96, int(header_rect.width() * 0.38)))
        chat_rect = QRectF(header_rect.left(), header_rect.top(), max(40.0, header_rect.width() - meta_width - 8), header_rect.height())
        meta_rect = QRectF(header_rect.right() - meta_width, header_rect.top(), meta_width, header_rect.height())
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(chat_rect, Qt.AlignVCenter | Qt.TextSingleLine, header_metrics.elidedText(chat_text, Qt.ElideRight, int(chat_rect.width())))
        painter.setPen(QColor("#8FA3B5"))
        painter.drawText(meta_rect, Qt.AlignRight | Qt.AlignVCenter | Qt.TextSingleLine, header_metrics.elidedText(meta_text, Qt.ElideRight, int(meta_rect.width())))
        painter.setFont(option.font)
        painter.setPen(QColor("#DCE9F3"))
        self._draw_simple_text(painter, body_rect, self._display_text(message))
        if current:
            painter.setPen(QPen(QColor("#5BC8FF"), 1))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(row_rect.adjusted(1.0, 1.0, -1.0, -1.0))


    def paint(self, painter, option, index):
        data = index.data(Qt.UserRole) or {}
        kind = data.get("kind", "message")
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(option.rect)

        if kind == "placeholder":
            painter.setPen(QColor("#AFC2D3"))
            viewport = option.widget.viewport() if option.widget is not None else None
            base_rect = QRectF(viewport.rect()) if viewport is not None else rect
            text_rect = base_rect.adjusted(24, 0, -24, 0)
            painter.drawText(text_rect, Qt.AlignCenter | Qt.TextWordWrap, data.get("text", ""))
            painter.restore()
            return

        if kind == "notice":
            base_bubble = rect.adjusted(86, 10, -86, -10)
            if data.get("center"):
                title = data.get("title", "")
                body = "\n".join(data.get("body_lines", []))
                fm = option.fontMetrics
                bubble_w = min(max(320.0, rect.width() - 240.0), 860.0)
                bubble_w = min(bubble_w, max(220.0, rect.width() - 32.0))
                text_width = max(180, int(bubble_w) - 28)
                title_h = fm.boundingRect(QRect(0, 0, text_width, 1000), Qt.TextWordWrap, title).height()
                body_h = fm.boundingRect(QRect(0, 0, text_width, 3000), Qt.TextWordWrap, body).height()
                bubble_h = max(74.0, float(title_h + body_h + 46))
                x = rect.left() + (rect.width() - bubble_w) / 2.0
                y = rect.top() + max(10.0, (rect.height() - bubble_h) / 2.0)
                bubble = QRectF(x, y, bubble_w, bubble_h)
            else:
                bubble = base_bubble
            bg = QColor("#352330") if data.get("danger") else QColor("#183246")
            border = QColor("#9A4F71") if data.get("danger") else QColor("#35688D")
            painter.setPen(QPen(border, 1.2))
            painter.setBrush(bg)
            painter.drawRoundedRect(bubble, 14, 14)
            text_width = max(80, int(bubble.width() - 28))
            title_text = data.get("title", "")
            body_text = "\n".join(data.get("body_lines", []))
            title_font = painter.font()
            title_font.setBold(True)
            painter.setFont(title_font)
            title_h = painter.fontMetrics().boundingRect(QRect(0, 0, text_width, 1000), Qt.TextWordWrap, title_text).height()
            title_rect = QRectF(bubble.left() + 14, bubble.top() + 10, text_width, max(18, title_h + 2))
            painter.setPen(QColor("#FFFFFF"))
            painter.drawText(title_rect, Qt.TextWordWrap, title_text)
            body_font = painter.font()
            body_font.setBold(False)
            painter.setFont(body_font)
            body_top = title_rect.bottom() + 4
            body_rect = QRectF(bubble.left() + 14, body_top, text_width, max(18, bubble.bottom() - body_top - 12))
            painter.setPen(QColor("#CAD8E3"))
            painter.drawText(body_rect, Qt.TextWordWrap, body_text)
            painter.restore()
            return

        message = data.get("message")
        if message is None:
            painter.restore()
            return

        paint_option = self._stable_paint_option(option, index)
        if self._message_simple_render_enabled(data, option):
            self._paint_simple_message(painter, paint_option, index, data, message)
            painter.restore()
            return

        option = paint_option
        header_rect, bubble_rect, check_rect = self._message_rects(option, message)
        body_text = self._display_text(message)
        body_font = QFont(option.font)
        checked = bool(getattr(message, "selected", data.get("selected", index.data(Qt.CheckStateRole) != Qt.Unchecked)))

        if checked:
            painter.setPen(QPen(QColor("#2AABEE"), 1.4))
            painter.setBrush(QColor("#2AABEE"))
        else:
            painter.setPen(QPen(QColor("#667F93"), 1.4))
            painter.setBrush(QColor("#17212B"))
        painter.drawEllipse(check_rect)

        if checked:
            pen = QPen(QColor("#FFFFFF"), 2.0)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(pen)
            cx = check_rect.center().x()
            cy = check_rect.center().y()
            path = QPainterPath()
            path.moveTo(cx - 5.0, cy + 0.4)
            path.lineTo(cx - 1.7, cy + 3.4)
            path.lineTo(cx + 5.0, cy - 3.5)
            painter.drawPath(path)

        chat_text, meta_text = self._header_texts(message)
        prefix_text, chat_title, suffix_text = self._header_chat_parts(message)

        base_header_font = painter.font()
        base_header_font.setBold(True)
        base_meta_font = painter.font()
        base_meta_font.setBold(False)
        header_font = QFont(base_header_font)
        meta_font = QFont(base_meta_font)
        min_point_size = max(7, header_font.pointSize() - 5)
        separator_text = " • "
        suffix_content = str(suffix_text or "").strip()
        if suffix_content.startswith("•"):
            suffix_content = suffix_content[1:].strip()

        while True:
            chat_metrics = QFontMetrics(header_font)
            meta_metrics = QFontMetrics(meta_font)
            meta_needed_width = float(meta_metrics.horizontalAdvance(meta_text) + 12)
            min_left_width = 96.0
            max_meta_width = max(60.0, header_rect.width() - min_left_width - 14)
            meta_width = min(max_meta_width, max(meta_needed_width, header_rect.width() * 0.34))
            left_width = max(40.0, header_rect.width() - meta_width - 14)
            full_left_width = float(chat_metrics.horizontalAdvance(chat_text))
            if suffix_content:
                full_left_width = float(
                    chat_metrics.horizontalAdvance(prefix_text)
                    + chat_metrics.horizontalAdvance(chat_title)
                    + chat_metrics.horizontalAdvance(separator_text)
                    + chat_metrics.horizontalAdvance(suffix_content)
                )
            if (full_left_width <= left_width and meta_needed_width <= meta_width + 0.5) or header_font.pointSize() <= min_point_size:
                break
            header_font.setPointSize(header_font.pointSize() - 1)
            meta_font.setPointSize(max(min_point_size, meta_font.pointSize() - 1))

        chat_metrics = QFontMetrics(header_font)
        meta_metrics = QFontMetrics(meta_font)
        meta_needed_width = float(meta_metrics.horizontalAdvance(meta_text) + 12)
        min_left_width = 96.0
        max_meta_width = max(60.0, header_rect.width() - min_left_width - 14)
        meta_width = min(max_meta_width, max(meta_needed_width, header_rect.width() * 0.34))
        chat_rect = QRectF(header_rect.left(), header_rect.top(), max(40.0, header_rect.width() - meta_width - 14), header_rect.height())

        painter.setFont(header_font)
        painter.setPen(QColor("#FFFFFF"))
        if suffix_content:
            prefix_width = float(chat_metrics.horizontalAdvance(prefix_text))
            separator_width = float(chat_metrics.horizontalAdvance(separator_text))
            title_left = chat_rect.left() + prefix_width
            remaining_after_prefix = max(0.0, chat_rect.right() - title_left)
            preferred_title_width = float(chat_metrics.horizontalAdvance(chat_title))
            title_min_ratio = 0.48 if suffix_content else 1.0
            min_title_width = min(
                max(92.0, remaining_after_prefix * title_min_ratio),
                max(0.0, remaining_after_prefix - separator_width),
            )
            suffix_full_width = float(chat_metrics.horizontalAdvance(suffix_content))
            max_suffix_width = max(0.0, remaining_after_prefix - min_title_width - separator_width)
            suffix_draw_width = min(suffix_full_width, max_suffix_width)
            max_title_width = min(
                preferred_title_width,
                max(0.0, remaining_after_prefix - separator_width - suffix_draw_width),
            )
            if max_title_width < min_title_width and remaining_after_prefix > separator_width + 30:
                max_title_width = min_title_width
                suffix_draw_width = max(0.0, remaining_after_prefix - max_title_width - separator_width)

            prefix_rect = QRectF(chat_rect.left(), chat_rect.top(), min(prefix_width, chat_rect.width()), chat_rect.height())
            painter.drawText(prefix_rect, Qt.AlignVCenter | Qt.TextSingleLine, prefix_text)
            title_display = ""
            title_draw_width = 0.0
            if max_title_width > 4:
                title_display = chat_metrics.elidedText(chat_title, Qt.ElideRight, int(max_title_width))
                title_draw_width = min(float(chat_metrics.horizontalAdvance(title_display)), max_title_width)
                title_rect = QRectF(title_left, chat_rect.top(), title_draw_width + 1.0, chat_rect.height())
                painter.drawText(title_rect, Qt.AlignVCenter | Qt.TextSingleLine, title_display)
            separator_left = title_left + title_draw_width
            if separator_left + separator_width <= chat_rect.right() + 0.5:
                separator_rect = QRectF(separator_left, chat_rect.top(), separator_width, chat_rect.height())
                painter.drawText(separator_rect, Qt.AlignVCenter | Qt.TextSingleLine, separator_text)
            suffix_left = separator_left + separator_width
            available_suffix_width = max(0.0, chat_rect.right() - suffix_left)
            if available_suffix_width > 4 and suffix_content:
                suffix_rect = QRectF(suffix_left, chat_rect.top(), available_suffix_width, chat_rect.height())
                suffix_display = chat_metrics.elidedText(suffix_content, Qt.ElideRight, int(available_suffix_width))
                painter.drawText(suffix_rect, Qt.AlignVCenter | Qt.TextSingleLine, suffix_display)
        else:
            painter.drawText(chat_rect, Qt.AlignVCenter | Qt.TextSingleLine, chat_metrics.elidedText(chat_text, Qt.ElideRight, int(chat_rect.width())))

        painter.setFont(meta_font)
        painter.setPen(QColor("#A6B8C5"))
        meta_rect = QRectF(header_rect.right() - meta_width, header_rect.top(), meta_width, header_rect.height())
        meta_display = meta_metrics.elidedText(meta_text, Qt.ElideRight, int(meta_rect.width()))
        painter.drawText(meta_rect, Qt.AlignRight | Qt.AlignVCenter | Qt.TextSingleLine, meta_display)

        start_color, end_color = self._gradient_colors(message)
        grad = QLinearGradient(bubble_rect.topLeft(), bubble_rect.topRight())
        grad.setColorAt(0.0, QColor(start_color))
        grad.setColorAt(1.0, QColor(end_color))
        painter.setPen(Qt.NoPen)
        painter.setBrush(grad)
        painter.drawRoundedRect(bubble_rect, 18, 18)

        painter.setFont(body_font)
        painter.setPen(QColor("#FFFFFF"))
        text_rect = bubble_rect.adjusted(16, 12, -16, -12)
        self._draw_wrapped_text(painter, text_rect, body_text, text_rect)

        current = False
        view = option.widget
        if view is not None and view.hasFocus():
            try:
                current = view.currentIndex() == index
            except Exception:
                current = False
        if current:
            focus_rect = header_rect.united(bubble_rect).adjusted(-8, -7, 8, 7)
            focus_fill = QColor("#5BC8FF")
            focus_fill.setAlpha(34)
            focus_pen_color = QColor("#5BC8FF")
            focus_pen_color.setAlpha(210)
            painter.setPen(QPen(focus_pen_color, 2.0))
            painter.setBrush(focus_fill)
            painter.drawRoundedRect(focus_rect, 18, 18)
        painter.restore()

    def _message_size_hint(self, option, message, width: int):
        key = (
            width,
            self._language_cache_key(),
            option.font.toString(),
            getattr(message, "message_id", None),
            getattr(message, "chat_input", ""),
            getattr(message, "sender_name", ""),
            getattr(message, "sender_id", None),
            getattr(message, "date", ""),
            getattr(message, "text", ""),
            getattr(message, "content_kind", ""),
            getattr(message, "is_outgoing", False),
            getattr(message, "is_reaction", False),
            getattr(message, "chat_is_group", False),
            getattr(message, "_ui_show_topic_id", False),
        )
        cached = getattr(message, "_ui_size_hint_cache", None)
        if cached and cached[0] == key:
            return cached[1]
        content_width = max(240, width - 54)
        bubble_width = float(self._bubble_width(option, message, content_width))
        text_h = self._message_body_height(option, message, bubble_width)
        size = QSize(width, max(80, int(text_h + 66.999)))
        try:
            message._ui_size_hint_cache = (key, size)
        except Exception:
            pass
        return size

    def sizeHint(self, option, index):
        data = index.data(Qt.UserRole) or {}
        kind = data.get("kind", "message")
        width = max(260, option.rect.width() if option.rect.width() > 0 else 760)
        if kind == "placeholder":
            view = option.widget
            height = max(160, (view.viewport().height() - 20) if view else 200)
            return QSize(width, height)
        if kind == "notice":
            title = data.get("title", "")
            body = "\n".join(data.get("body_lines", []))
            fm = option.fontMetrics
            if data.get("center"):
                notice_width = int(min(max(320, width - 240), 860))
                notice_width = min(notice_width, max(220, width - 32))
            else:
                notice_width = max(220, width - 220)
            title_h = fm.boundingRect(QRect(0, 0, notice_width - 28, 1000), Qt.TextWordWrap, title).height()
            body_h = fm.boundingRect(QRect(0, 0, notice_width - 28, 3000), Qt.TextWordWrap, body).height()
            if data.get("center"):
                view = option.widget
                viewport_height = view.viewport().height() if view else 220
                return QSize(width, max(180, viewport_height - 2, title_h + body_h + 46))
            return QSize(width, max(74, title_h + body_h + 46))
        message = data.get("message")
        if message is None:
            return QSize(width, 80)
        if self._message_simple_render_enabled(data, option):
            return self._simple_message_size_hint(option, message, width)
        return self._message_size_hint(option, message, width)

    def editorEvent(self, event, model, option, index):
        return False