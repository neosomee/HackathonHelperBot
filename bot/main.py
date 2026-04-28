import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import MenuButtonWebApp, WebAppInfo

from bot.config import get_config
from bot.services.api import BackendAPI

from bot.handlers import menu, organizer, registration, start
from bot.handlers.team_applications import router as team_applications_router


async def main():
    config = get_config()

    session = AiohttpSession(proxy=config.proxy_url)

    bot = Bot(
        token=config.token,
        session=session,
    )

    dp = Dispatcher(storage=MemoryStorage())

    # --- API ---
    api = BackendAPI(config.backend_api_url)
    await api.init()

    dp["api"] = api
    dp["config"] = config

    # --- Routers ---
    dp.include_router(start.router)
    dp.include_router(registration.router)
    dp.include_router(menu.router)
    dp.include_router(organizer.router)  # оставляем
    dp.include_router(team_applications_router)

    # --- Mini App ---
    if config.mini_app_url.startswith("https://"):
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="🚀 Меню",
                web_app=WebAppInfo(url=config.mini_app_url),
            )
        )
    else:
        print("⚠️ Mini App отключен (нужен HTTPS)")

    try:
        await dp.start_polling(bot)
    finally:
        # --- shutdown ---
        await api.close()
        await session.close()


if __name__ == "__main__":
    asyncio.run(main())