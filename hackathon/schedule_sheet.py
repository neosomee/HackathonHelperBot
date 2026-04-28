"""
Чтение расписания из Google Таблицы (публичный CSV export).

Формат листа: первая строка — заголовки. Обязательно колонка времени начала;
остальные — по смыслу см. docs/SCHEDULE_CSV_FORMAT.md
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterator
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

from dateutil import parser as date_parser
from django.utils import timezone

_START_ALIASES = frozenset(
    {
        "start",
        "start_datetime",
        "datetime",
        "time",
        "время",
        "время_начала",
        "дата_время",
        "начало",
    }
)
_TITLE_ALIASES = frozenset({"title", "name", "название", "событие", "мероприятие"})
_DESC_ALIASES = frozenset({"description", "описание", "details", "комментарий"})
_NOTIFY_ALIASES = frozenset(
    {
        "notify_minutes_before",
        "notify",
        "за_минут",
        "напомнить_за_минут",
        "minutes_before",
    }
)


@dataclass(frozen=True)
class ScheduleEventRow:
    start: datetime  # aware, UTC or local per sheet
    title: str
    description: str
    notify_minutes_before: int


def parse_spreadsheet_id_and_gid(sheet_url: str) -> tuple[str, str]:
    if not sheet_url or "docs.google.com/spreadsheets" not in sheet_url:
        raise ValueError("Нужна ссылка вида https://docs.google.com/spreadsheets/d/...")

    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", sheet_url)
    if not m:
        raise ValueError("Не удалось извлечь id таблицы из URL.")
    spreadsheet_id = m.group(1)

    parsed = urlparse(sheet_url)
    gid = "0"
    frag = parsed.fragment
    if frag and "gid=" in frag:
        g = re.search(r"gid=(\d+)", frag)
        if g:
            gid = g.group(1)
    qs = parse_qs(parsed.query)
    if "gid" in qs and qs["gid"]:
        gid = qs["gid"][0]

    return spreadsheet_id, gid


def build_csv_export_url(sheet_url: str) -> str:
    spreadsheet_id, gid = parse_spreadsheet_id_and_gid(sheet_url)
    return (
        f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export"
        f"?format=csv&gid={gid}"
    )


def fetch_sheet_csv(sheet_url: str, timeout: int = 25) -> str:
    export_url = build_csv_export_url(sheet_url)
    req = Request(
        export_url,
        headers={"User-Agent": "HackathonHelperBot/1.0 (schedule sync)"},
    )
    with urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    return raw.decode("utf-8", errors="replace")


def _norm_key(key: str) -> str:
    return key.strip().lower().replace(" ", "_")


def _pick_column(header_map: dict[str, str], aliases: frozenset) -> str | None:
    for h, original in header_map.items():
        if h in aliases:
            return original
    return None


def parse_schedule_csv(csv_text: str, *, default_notify_minutes: int = 15) -> list[ScheduleEventRow]:
    if not csv_text.strip():
        return []

    reader = csv.DictReader(io.StringIO(csv_text))
    if not reader.fieldnames:
        return []

    header_map = {_norm_key(fn): fn for fn in reader.fieldnames if fn}

    col_start = _pick_column(header_map, _START_ALIASES)
    col_title = _pick_column(header_map, _TITLE_ALIASES)
    col_desc = _pick_column(header_map, _DESC_ALIASES)
    col_notify = _pick_column(header_map, _NOTIFY_ALIASES)

    if not col_start:
        raise ValueError(
            "В таблице нужна колонка времени начала (например start, start_datetime, время_начала)."
        )

    events: list[ScheduleEventRow] = []
    tz = timezone.get_current_timezone()

    for row in reader:
        raw_time = (row.get(col_start) or "").strip()
        if not raw_time:
            continue

        try:
            dt = date_parser.parse(raw_time, dayfirst=True)
        except (ValueError, TypeError, OverflowError):
            continue

        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, tz)

        title = (row.get(col_title) or "").strip() if col_title else ""
        if not title:
            title = "Событие"

        desc = (row.get(col_desc) or "").strip() if col_desc else ""

        notify = default_notify_minutes
        if col_notify and (row.get(col_notify) or "").strip():
            try:
                notify = max(0, min(24 * 60, int(float(str(row[col_notify]).replace(",", ".")))))
            except (ValueError, TypeError):
                notify = default_notify_minutes

        events.append(
            ScheduleEventRow(
                start=dt,
                title=title,
                description=desc,
                notify_minutes_before=notify,
            )
        )

    events.sort(key=lambda e: e.start)
    return events


def iter_upcoming_notification_windows(
    events: list[ScheduleEventRow],
    *,
    now: datetime | None = None,
) -> Iterator[ScheduleEventRow]:
    """События, для которых пора отправить напоминание: notify_at <= now < start."""
    now = now or timezone.now()
    for ev in events:
        notify_at = ev.start - timedelta(minutes=ev.notify_minutes_before)
        if notify_at <= now < ev.start:
            yield ev


def event_dedupe_key(hackathon_id: int, ev: ScheduleEventRow) -> str:
    stamp = ev.start.isoformat()
    title = ev.title[:80]
    return f"{hackathon_id}|{stamp}|{title}"


def pick_current_and_next_events(
    events: list[ScheduleEventRow],
    *,
    now: datetime | None = None,
) -> tuple[ScheduleEventRow | None, ScheduleEventRow | None]:
    """
    Текущее — последнее событие с start <= now; следующее — первое с start > now.
    Без колонки «конец» в CSV это самый устойчивый вариант для «сейчас / дальше».
    """
    now = now or timezone.now()
    if not events:
        return None, None
    past_or_now = [e for e in events if e.start <= now]
    future = [e for e in events if e.start > now]
    current = past_or_now[-1] if past_or_now else None
    upcoming = future[0] if future else None
    return current, upcoming
