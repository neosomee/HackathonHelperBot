import os

import aiohttp
from aiogram import F, Router
from aiogram.types import CallbackQuery

router = Router()
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://127.0.0.1:8000")


@router.callback_query(F.data.startswith("team_app:"))
async def handle_team_application_decision(callback: CallbackQuery):
    try:
        _, decision, user_id, team_id = callback.data.split(":")
        payload = {
            "captain_telegram_id": callback.from_user.id,
            "user_telegram_id": int(user_id),
            "team_id": int(team_id),
            "decision": decision,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{BACKEND_API_URL}/api/team/decision/",
                json=payload,
            ) as response:
                data = await response.json()

                if response.status >= 400:
                    error_text = data.get("error") or data.get("errors") or "Ошибка"
                    await callback.answer(error_text, show_alert=True)
                    return

        status_text = "принята" if decision == "accept" else "отклонена"
        await callback.message.edit_text(
            callback.message.text + f"\n\n<b>Решение:</b> заявка {status_text}",
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
        await callback.answer("Готово")
    except Exception:
        await callback.answer("Не удалось обработать заявку", show_alert=True)