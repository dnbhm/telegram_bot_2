import sys
import os
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message

print("=" * 60)
print("🚀 ЗАПУСК МИНИМАЛЬНОЙ ВЕРСИИ")
print("=" * 60)
sys.stdout.flush()

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

print(f"BOT_TOKEN: {'✅' if BOT_TOKEN else '❌'}")
print(f"ADMIN_IDS: {ADMIN_IDS}")
sys.stdout.flush()

if not BOT_TOKEN:
    print("❌ Нет токена!")
    sys.exit(1)

# Создаем бота с таймаутом
bot = Bot(token=BOT_TOKEN, request_timeout=120)
print("✅ Бот создан с таймаутом 120 сек")

dp = Dispatcher(storage=MemoryStorage())

@dp.message(Command("start"))
async def start(message: Message):
    try:
        await message.answer("Бот работает! 🎉")
    except Exception as e:
        print(f"❌ Ошибка при ответе: {e}")
        sys.stdout.flush()

@dp.message(Command("test"))
async def test(message: Message):
    try:
        await message.answer("Тест успешен! ✅")
    except Exception as e:
        print(f"❌ Ошибка при ответе: {e}")
        sys.stdout.flush()

async def main():
    print("🔄 Запуск polling...")
    sys.stdout.flush()
    try:
        await dp.start_polling(bot)
    except Exception as e:
        print(f"❌ Ошибка при запуске: {e}")
        sys.stdout.flush()
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("👋 Бот остановлен пользователем")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        sys.stdout.flush()
        sys.exit(1)