import sys
import os
import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

import aiofiles
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    CallbackQuery,
    FSInputFile,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest

print("=" * 60, flush=True)
print("🚀 ЗАПУСК ПОЛНОЙ ВЕРСИИ БОТА", flush=True)
print("=" * 60, flush=True)

load_dotenv()

# ===================== КОНФИГУРАЦИЯ =====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
VIDEO_NOTE_ID = os.getenv("VIDEO_NOTE_ID")

if not BOT_TOKEN:
    print("❌ BOT_TOKEN не найден!", flush=True)
    sys.exit(1)

print(f"✅ Бот инициализирован. Админов: {len(ADMIN_IDS)}", flush=True)

# НАСТРОЙКИ
CACHE_TTL = 30
SAVE_INTERVAL = 10
DATA_FILE = "data/data.json"

# Создаем папку data
os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
print("✅ Папка data создана", flush=True)

# Создаем бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
print("✅ Бот и Dispatcher созданы", flush=True)

# ===================== ТЕКСТЫ РАССЫЛОК =====================
WEEKLY_PLAN_TEXT = (
    "Приветииик🤍 Начинается новая неделя, новые возможности, а это значит, "
    "что самое время поставить задачи и цели, чтобы держать фокус ⭐️\n\n"
    "Ответь на несколько вопросов:\n\n"
    "1️⃣ Какие у тебя цели на эту неделю?\n"
    "2️⃣ Что ты хочешь изучить, в чём разобраться или какой навык прокачать?\n"
    "3️⃣ Как ты себя порадуешь за выполнение плана?\n\n"
    "Запиши их здесь, чтобы сделать эту неделю максимально продуктивной и интересной 🪩"
)

WEEKLY_REVIEW_TEXT = (
    "Привееет💫 Конец недели, а это значит, что пора подводить итоги, "
    "какой путь ты прошёл за эти дни 📝\n\n"
    "Ответь на несколько вопросов:\n\n"
    "1️⃣ Что из запланированного получилось?\n"
    "2️⃣ За что ты себя можешь похвалить?\n"
    "3️⃣ А может быть, случилось что-то неожиданное, чего ты не планировал(а), "
    "но оно того стоило?\n\n"
    "Запиши свои победы и мысли✨\n\n"
    "Ты молодец уже только потому, что не останавливаешься, горжусь тобой🤍\n"
    "Отдыхай и набирайся сил, скоро тебя ждёт новая неделя⭐️"
)

# ===================== СТРУКТУРА МОДУЛЕЙ =====================
MODULES = {
    1: {
        "name": "Папка монтажёра",
        "lessons": [
            "Интерфейс CapCut",
            "Рабочее пространство: папки, файлы и организация",
            "Дополнительные программы и сервисы для монтажа"
        ]
    },
    2: {
        "name": "Горизонтальный монтаж",
        "lessons": [
            "Фундамент горизонтального монтажа",
            "Структура успешного YouTube-видео",
            "Работа с речью"
        ]
    },
    3: {
        "name": "Киноязык монтажа",
        "lessons": [
            "Что такое киноязык и зачем он нужен монтажеру?",
            "Анализ идеи и сценария",
            "Работа со звуком",
            "Цветокоррекция",
            "Цветокоррекция в DaVinci Resolve"
        ]
    },
    4: {
        "name": "Навыки креативности",
        "lessons": [
            "Креативность и насмотренность монтажера"
        ]
    },
    5: {
        "name": "Вертикальный монтаж",
        "lessons": [
            "Психология вертикального контента",
            "Ключи: логика использования, примеры",
            "Compound Clip: для чего он нужен и как его использовать",
            "Маска: обзор всех видов + туториалы по применению самых трендовых приемов"
        ]
    },
    6: {
        "name": "Анимационный монтаж",
        "lessons": [
            "Анимационный монтаж: вводная лекция",
            "Анимационный монтаж: разбор таймлайна",
            "Субтитры",
            "Создаем анимацию",
            "Обзор эффектов",
            "Музыка и дополнительные звуки"
        ]
    },
    7: {
        "name": "After Effects",
        "lessons": [
            "Обзор интерфейса",
            "Плагины, пресеты, проекты",
            "Null object",
            "Обзор таймлайна"
        ]
    },
    8: {
        "name": "Съемка видео",
        "lessons": [
            "Основы операторской работы",
            "Композиция, планы и ракурсы",
            "Технические характеристики для качественной съемки",
            "Работа со светом",
            "Запись звука и голоса"
        ]
    },
    9: {
        "name": "Клиенты и портфолио",
        "lessons": [
            "Где искать клиентов",
            "Коммерческое предложение и брифинг клиента",
            "Общение с клиентом и работа с ТЗ",
            "Правки, сдача и ценообразование",
            "Портфолио, которое продает за тебя"
        ]
    },
    10: {
        "name": "Личный бренд",
        "lessons": [
            "Зачем монтажеру личный бренд?",
            "Как упаковать свои соц.сети",
            "Какой контент публиковать?",
            "Построение стратегии"
        ]
    },
    11: {
        "name": "Нейросети в монтаже",
        "lessons": [
            "Нейросети в монтаже",
            "Создание AI-роликов с нуля"
        ]
    }
}

TOTAL_LESSONS = sum(len(m["lessons"]) for m in MODULES.values())
print(f"✅ Загружено {len(MODULES)} модулей, {TOTAL_LESSONS} уроков", flush=True)


# ===================== FSM =====================
class FeedbackState(StatesGroup):
    waiting = State()


class WeeklyPlanState(StatesGroup):
    waiting = State()


class WeeklyReviewState(StatesGroup):
    waiting = State()


# ===================== КЛАСС ДЛЯ УПРАВЛЕНИЯ ДАННЫМИ =====================
class DataManager:
    def __init__(self):
        self.data = None
        self.dirty = False
        self.lock = asyncio.Lock()

    async def load(self):
        async with self.lock:
            os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

            if os.path.exists(DATA_FILE):
                try:
                    async with aiofiles.open(DATA_FILE, 'r', encoding='utf-8') as f:
                        content = await f.read()
                        self.data = json.loads(content)
                except Exception as e:
                    print(f"❌ Ошибка загрузки данных: {e}", flush=True)
                    self.data = {"users": {}, "lesson_stats": {}, "module_stats": {}}
            else:
                self.data = {"users": {}, "lesson_stats": {}, "module_stats": {}}
                await self.save(force=True)

            self._ensure_structure()
            return self.data

    def _ensure_structure(self):
        if "module_stats" not in self.data:
            self.data["module_stats"] = {}

        for user_id, user_data in self.data["users"].items():
            for key in ["admin_message_id", "current_module", "current_lesson",
                        "module_progress", "answers", "feedback", "video_sent", "weekly_goals"]:
                if key not in user_data:
                    user_data[key] = {} if key in ["module_progress", "answers", "feedback",
                                                   "weekly_goals"] else False if key == "video_sent" else None

    async def save(self, force=False):
        if not self.dirty and not force:
            return
        async with self.lock:
            try:
                os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
                async with aiofiles.open(DATA_FILE, 'w', encoding='utf-8') as f:
                    await f.write(json.dumps(self.data, ensure_ascii=False, indent=2))
                self.dirty = False
                print(f"✅ Данные сохранены. Пользователей: {len(self.data['users'])}", flush=True)
            except Exception as e:
                print(f"❌ Ошибка сохранения данных: {e}", flush=True)

    async def mark_dirty(self):
        self.dirty = True

    async def auto_save_loop(self):
        while True:
            await asyncio.sleep(SAVE_INTERVAL)
            try:
                await self.save()
            except Exception as e:
                print(f"❌ Ошибка в цикле автосохранения: {e}", flush=True)


data_manager = DataManager()


# ===================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====================
def init_user(user_id: int, first_name: str = "", username: str = ""):
    user_id_str = str(user_id)
    now = int(time.time())

    default_user = {
        "first_name": first_name,
        "username": username,
        "first_seen": now,
        "last_active": now,
        "current_module": None,
        "current_lesson": None,
        "module_progress": {},
        "answers": {},
        "feedback": {},
        "main_message_id": None,
        "admin_message_id": None,
        "video_sent": False,
        "weekly_goals": []
    }

    if user_id_str not in data_manager.data["users"]:
        data_manager.data["users"][user_id_str] = default_user
    else:
        existing = data_manager.data["users"][user_id_str]
        for key, value in default_user.items():
            if key not in existing:
                existing[key] = value
        existing["first_name"] = first_name
        existing["username"] = username
        existing["last_active"] = now


# ===================== КОМАНДЫ =====================
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = message.from_user
    await data_manager.get()
    init_user(user.id, user.first_name, user.username)
    user_data = data_manager.data["users"][str(user.id)]

    # Отправка кружка
    if not user_data.get("video_sent", False):
        try:
            video_note_path = "video_notes/welcome_2.mp4"
            if os.path.exists(video_note_path):
                video_note = FSInputFile(video_note_path)
                await bot.send_video_note(chat_id=user.id, video_note=video_note)
                user_data["video_sent"] = True
                await data_manager.mark_dirty()
                await asyncio.sleep(0.5)
            else:
                print(f"⚠️ Файл {video_note_path} не найден", flush=True)
        except Exception as e:
            print(f"❌ Ошибка отправки кружка: {e}", flush=True)

    await show_main_menu(user.id)


# ===================== ЗАПУСК =====================
async def on_startup():
    print("📂 Загрузка данных...", flush=True)
    await data_manager.load()
    print(f"✅ Данные загружены. Пользователей: {len(data_manager.data['users'])}", flush=True)
    print("🔄 Запуск автосохранения...", flush=True)
    asyncio.create_task(data_manager.auto_save_loop())
    print("🚀 Бот запущен!", flush=True)


async def on_shutdown():
    print("💾 Сохранение данных...", flush=True)
    await data_manager.save(force=True)
    print("✅ Данные сохранены. Бот остановлен.", flush=True)


async def main():
    logging.basicConfig(
        level=logging.WARNING,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    print("🔄 Запуск polling...", flush=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())