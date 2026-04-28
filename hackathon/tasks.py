from __future__ import annotations

import logging

from celery import shared_task
from django.utils import timezone

from .models import HackathonScheduleSubscription, ScheduleNotificationLog
from .schedule_sheet import (
    event_dedupe_key,
    fetch_sheet_csv,
    iter_upcoming_notification_windows,
    parse_schedule_csv,
)
from bot.notifications import send_telegram_message  # <-- единый источник отправки

logger = logging.getLogger(__name__)


@shared_task(bind=True, ignore_result=True)
def process_hackathon_schedule_notifications(self):
    """
    Периодическая задача:
    - читает Google Sheet (CSV)
    - ищет события, которые скоро начнутся
    - отправляет уведомления подписчикам
    """

    qs = (
        HackathonScheduleSubscription.objects.filter(is_active=True)
        .select_related("user", "hackathon")
        .order_by("id")
    )

    now = timezone.now()

    for sub in qs.iterator(chunk_size=50):
        hackathon = sub.hackathon
        user = sub.user
        url = (hackathon.schedule_sheet_url or "").strip()

        if not url:
            continue

        try:
            csv_text = fetch_sheet_csv(url)
            events = parse_schedule_csv(csv_text)
        except Exception as exc:
            logger.warning(
                "Schedule fetch/parse failed hackathon=%s user=%s: %s",
                hackathon.id,
                user.id,
                exc,
            )
            continue

        for ev in iter_upcoming_notification_windows(events, now=now):
            key = event_dedupe_key(hackathon.id, ev)

            # защита от дублей
            if ScheduleNotificationLog.objects.filter(
                user=user,
                dedupe_key=key,
            ).exists():
                continue

            delta = ev.start - now
            minutes_left = max(0, int(delta.total_seconds() // 60))

            text = (
                f"🔔 <b>{hackathon.name}</b>\n\n"
                f"⏰ Через ~{minutes_left} мин\n"
                f"📌 {ev.title}\n"
                f"🕒 {ev.start.strftime('%d.%m.%Y %H:%M')}"
            )

            if ev.description:
                text += f"\n\n{ev.description[:500]}"

            success = send_telegram_message(
                chat_id=int(user.telegram_id),
                text=text,
                parse_mode="HTML",
            )

            if success:
                ScheduleNotificationLog.objects.create(
                    user=user,
                    hackathon=hackathon,
                    dedupe_key=key,
                )