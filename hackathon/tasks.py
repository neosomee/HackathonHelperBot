from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from .models import HackathonScheduleSubscription, ScheduleNotificationLog
from .schedule_sheet import (
    event_dedupe_key,
    fetch_sheet_csv,
    iter_upcoming_notification_windows,
    parse_schedule_csv,
)
from bot.notifications import send_telegram_message

logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def process_hackathon_schedule_notifications(self):
    """
    Основная задача:
    - читает Google Sheet
    - ищет события
    - отправляет уведомления
    """

    now = timezone.now()
    logger.info("[CELERY] Notification check started at %s", now)

    qs = (
        HackathonScheduleSubscription.objects
        .filter(is_active=True)
        .select_related("user", "hackathon")
        .order_by("id")
    )

    total_sent = 0

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
                "[SCHEDULE ERROR] hackathon=%s user=%s error=%s",
                hackathon.id,
                user.id,
                exc,
            )
            continue

        for ev in iter_upcoming_notification_windows(events, now=now):
            key = event_dedupe_key(hackathon.id, ev)

            # 🔒 защита от дублей
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

            try:
                success = send_telegram_message(
                    chat_id=int(user.telegram_id),
                    text=text,
                    parse_mode="HTML",
                )
            except Exception as exc:
                logger.error(
                    "[TELEGRAM ERROR] hackathon=%s user=%s error=%s",
                    hackathon.id,
                    user.id,
                    exc,
                )
                continue

            if success:
                try:
                    with transaction.atomic():
                        ScheduleNotificationLog.objects.create(
                            user=user,
                            hackathon=hackathon,
                            dedupe_key=key,
                        )
                    total_sent += 1

                    logger.info(
                        "[NOTIFICATION SENT] hackathon=%s user=%s event=%s",
                        hackathon.id,
                        user.id,
                        ev.title,
                    )

                except Exception as exc:
                    logger.error(
                        "[DB ERROR] Failed to log notification: %s",
                        exc,
                    )

    logger.info("[CELERY] Notification check finished. Sent=%s", total_sent)