import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import MenuButtonWebApp, WebAppInfo

from bot.config import get_config
from bot.handlers import menu, registration, start
from bot.services.api import BackendAPI

from bot.handlers.team_applications import router as team_applications_router

async def main():
    config = get_config()

    session = AiohttpSession(proxy=config.proxy_url)

    bot = Bot(
        token=config.token,
        session=session,
    )

    dispatcher = Dispatcher(storage=MemoryStorage())

    api = BackendAPI(config.backend_api_url)
    dispatcher["api"] = api
    dispatcher["config"] = config

    dispatcher.include_router(start.router)
    dispatcher.include_router(registration.router)
    dispatcher.include_router(menu.router)
    dispatcher.include_router(team_applications_router)

    if config.mini_app_url.startswith("https://"):
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="🚀 Меню",
                web_app=WebAppInfo(url=config.mini_app_url)
            )
        )
    else:
        print("⚠️ Mini App отключен (нужен HTTPS)")

    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())