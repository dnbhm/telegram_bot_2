import asyncio
import json
import logging
import os
import sys
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
from aiogram.client.session.aiohttp import AiohttpSession

# ===================== ПРИНУДИТЕЛЬНЫЙ ВЫВОД =====================
print("=" * 60, flush=True)
print("🚀 ЗАПУСК БОТА", flush=True)
print("=" * 60, flush=True)
print(f"Текущая директория: {os.getcwd()}", flush=True)
print(f"Файлы: {os.listdir('.')}", flush=True)
sys.stdout.flush()

# Загружаем переменные из .env
load_dotenv()
print("✅ .env загружен", flush=True)
sys.stdout.flush()

# ===================== НАСТРОЙКА ПУТИ К ДАННЫМ =====================
DATA_DIR = "/data"

if not os.path.exists(DATA_DIR):
    DATA_DIR = "data"
    os.makedirs(DATA_DIR, exist_ok=True)
    print(f"📁 Создана локальная папка: {DATA_DIR}", flush=True)
else:
    print(f"📁 Используется папка: {DATA_DIR}", flush=True)

DATA_FILE = os.path.join(DATA_DIR, "data.json")
print(f"📄 Файл данных: {DATA_FILE}", flush=True)
sys.stdout.flush()

# ===================== КОНФИГУРАЦИЯ =====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
VIDEO_NOTE_ID = os.getenv("VIDEO_NOTE_ID")

if not BOT_TOKEN:
    print("❌ BOT_TOKEN не найден!", flush=True)
    sys.exit(1)

print(f"✅ Бот инициализирован. Админов: {len(ADMIN_IDS)}", flush=True)

CACHE_TTL = 30
SAVE_INTERVAL = 10

# Тексты для рассылок
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

# ===================== СОЗДАНИЕ БОТА =====================
print("🔌 Инициализация бота...", flush=True)

PROXY_URL = None

if PROXY_URL:
    print(f"🔌 Пробую подключиться через прокси: {PROXY_URL.split('@')[-1] if '@' in PROXY_URL else PROXY_URL}",
          flush=True)
    try:
        session = AiohttpSession(proxy=PROXY_URL, timeout=30)
        bot = Bot(token=BOT_TOKEN, session=session)
        print("✅ Бот создан с прокси", flush=True)
    except Exception as e:
        print(f"❌ Ошибка создания бота с прокси: {e}", flush=True)
        print("🔄 Запускаю без прокси...", flush=True)
        bot = Bot(token=BOT_TOKEN)
else:
    bot = Bot(token=BOT_TOKEN)
    print("✅ Бот создан без прокси", flush=True)

dp = Dispatcher(storage=MemoryStorage())

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

# ===================== ВОПРОСЫ ПО УРОКАМ =====================
LESSON_QUESTIONS = {
    (1, 0): (
        "Что для тебя стало самым полезным открытием в интерфейсе CapCut?\n\n"
        "А) Узнал(а) про скрытые вкладки и фишки, о которых даже не догадывался(ась)\n"
        "Б) Сочетания клавиш — теперь буду работать в разы быстрее!\n"
        "В) Наконец-то разобрался(ась), какая вкладка за что отвечает — всё встало на свои места\n"
        "Г) Даже для опытного пользователя нашлось пару новых приёмов"
    ),
    (1, 1): (
        "Какой инсайт про организацию файлов ты забираешь с собой?\n\n"
        "А) Понял(а), что система в папках = система в голове, иду наводить порядок\n"
        "Б) Осознал(а), что мне не хватает отдельного диска для монтажа\n"
        "В) Узнал(а) про разницу SSD и HDD теперь понимаю, что покупать"
    ),
    (1, 2): (
        "Пригодилась ли тебе подборка полезных сервисов?\n\n"
        "А) Да, сохранил(а) себе несколько классных ресурсов\n"
        "Б) Многое уже знал(а), но пару новых штук открыл(а) для себя\n"
        "В) Пока не изучал(а) глубоко, но сохранил(а) информацию в закладки"
    ),
    (2, 0): (
        "Что нового или самого ценного ты узнал(а) про законы монтажа?\n\n"
        "А) Впервые услышал(а) про кинематографические правила, теперь буду смотреть на монтаж совсем иначе\n"
        "Б) Многое было знакомо, но систематизировал(а) знания в голове\n"
        "В) Особенно зашла мысль про то, как работают эти законы именно в роликах\n"
        "Г) Пока сложновато, буду пересматривать и осмыслять"
    ),
    (2, 1): (
        "Какой приём построения видео ты точно попробуешь в своих работах?\n\n"
        "А) Научусь правильно делать хуки, чтобы цеплять зрителя с первых секунд\n"
        "Б) Вдохновился(ась) разборами примеров, теперь вижу, почему видео залетают\n"
        "В) Возьму на вооружение структуру с интро/влогов\n"
        "Г) Понял(а), что эти законы работают для любого контента, даже для вертикального"
    ),
    (2, 2): (
        "Что было самым полезным в работе с речью?\n\n"
        "А) Понял(а) ошибки в монтаже речи, теперь буду делать чище\n"
        "Б) Узнал(а) новые приёмы, как убирать паузы и запинки\n"
        "В) Было круто просто помонтировать вместе с тобой, чувствовал(а) поддержку"
    ),
    (3, 0): (
        "Что из истории кино и классических приёмов ты уже видишь в современных роликах или хочешь применить сама?\n\n"
        "А) теперь я везде замечаю эти приёмы, мир уже не будет прежним\n"
        "Б) Понял(а), как переносить «фишки» из кино в свои работы\n"
        "В) Было интересно погрузиться в историю, но как применить на практике, пока обдумываю\n"
        "Г) Не ожидал(а), что киноязык настолько важен для монтажёра, теперь буду смотреть на контент глубже"
    ),
    (3, 1): (
        "Какой подход к работе со сценарием или идеей ты забираешь с собой?\n\n"
        "А) Теперь понимаю, как анализировать сценарий до того, как начать монтаж\n"
        "Б) Узнал(а) про разные типы хуков, буду цеплять зрителя\n"
        "В) Вдохновился(ась) генерацией идей, появилось несколько задумок"
    ),
    (3, 2): (
        "Что самое ценное вынесла из урока про звук?\n\n"
        "А) Теперь знаю, как спасти даже плохо записанный звук\n"
        "Б) Понял(а) законы баланса, где должна быть музыка, а где голос\n"
        "В) Открыл(а) для себя мир саунд-эффектов\n"
        "Г) Осознал(а), что звук играет большую роль"
    ),
    (3, 3): (
        "Что нового узнал(а) про цветокоррекцию и создание своих пресетов?\n\n"
        "А) Наконец-то понял(а) разницу между коррекцией и цветом, а также как делать «дорогую» картинку\n"
        "Б) Увидел(а), как работать в DaVinci\n"
        "В) Фишка с созданием своих LUT класс, буду сохранять свой стиль\n"
        "Г) Понял(а), что цвет сильно влияет на настроение видео"
    ),
    (3, 4): (
        "Что нового открыл(а) для себя в DaVinci Resolve?\n\n"
        "А) Перестал(а) бояться профессионального софта, теперь понимаю логику работы\n"
        "Б) Увидел(а), как делать цветокоррекцию на уровне, который раньше казался недосягаемым\n"
        "В) Понял(а), как создавать свои LUT в DaVinci\n"
        "Г) Осознал(а), что CapCut и DaVinci можно комбинировать под разные задачи"
    ),
    (4, 0): (
        "Что для тебя стало главным открытием про креативность в монтаже?\n\n"
        "А) Понял(а), что креативность – это навык, который можно и нужно развивать\n"
        "Б) Узнал(а) про методики пересборки идей\n"
        "В) Задумался(ась) о своей насмотренности, оказывается, я мало смотрю/анализирую\n"
        "Г) Вдохновился(ась) искать везде вокруг идеи для монтажа"
    ),
    (5, 0): (
        "Что нового узнал(а) про психологию восприятия вертикального контента?\n\n"
        "А) Понял(а), почему один вертикальный контент залетает, а другой пролистывают через 2 секунды\n"
        "Б) Узнал(а) про особенности хуков именно в вертикальном формате\n"
        "В) Осознал(а), что психология зрителя в вертикальном формате сильно отличается от горизонтального формата\n"
        "Г) Теперь понимаю, как форматы влияют на восприятие"
    ),
    (5, 1): (
        "Что нового открыл(а) для себя в работе с ключами?\n\n"
        "А) Понял(а) логику работы с ключами, теперь смогу делать сложные вещи просто\n"
        "Б) Узнал(а), как настраивать пресеты ключей, чтобы ускорить работу\n"
        "В) Увидел(а) примеры применения — ключи могут гораздо больше, чем я думал(а)"
    ),
    (5, 2): (
        "Как изменилось твоё понимание Compound Clip после урока?\n\n"
        "А) Понял(а), что это проект в проекте очень удобно для сложных работ\n"
        "Б) Теперь знаю, как использовать Compound Clip для анимаций\n"
        "В) Осознал(а), что без этого инструмента монтаж был бы гораздо сложнее\n"
        "Г) Сохранил(а) в голове, буду активно применять"
    ),
    (5, 3): (
        "Какой приём с масками запомнился больше всего?\n\n"
        "А) Увидел(а) все виды масок, теперь знаю, какую и когда использовать\n"
        "Б) Трендовые приёмы вдохновили, хочу повторить в своих работах\n"
        "В) Понял(а), что маски — это не просто «вырезать», а мощный творческий инструмент"
    ),
    (6, 0): (
        "Что из разбора анимационных роликов оказалось самым полезным?\n\n"
        "А) Понял(а), как анализировать анимационный монтаж теперь вижу, что работает, а что нет\n"
        "Б) Увидел(а) на примерах, почему одни ролики залетают, а другие нет\n"
        "В) Осознал(а), что анимационный монтаж — это всегда про идею, а не про кучу эффектов\n"
        "Г) Вдохновился(ась) разборами — захотелось сразу пробовать"
    ),
    (6, 1): (
        "Что нового открыл(а) для себя, глядя на таймлайн сложного анимационного ролика?\n\n"
        "А) Увидел(а), как устроен профессиональный таймлайн — слои, структура, логика\n"
        "Б) Понял(а), как собираются сложные анимации в один цельный ролик\n"
        "В) Разбор показал, что за крутой анимацией стоит огромная работа\n"
        "Г) Сохранил(а) структуру в голове теперь есть ориентир для своих проектов"
    ),
    (6, 2): (
        "Что нового узнал(а) про работу с субтитрами?\n\n"
        "А) Понял(а), почему субтитры важно делать в самом начале монтажа\n"
        "Б) Узнал(а), как правильно размещать субтитры, чтобы они не мешали, а помогали\n"
        "В) Осознал(а), что субтитры — это мощный инструмент удержания внимания\n"
        "Г) Раньше делал(а) субтитры хаотично, теперь буду подходить осознанно"
    ),
    (6, 3): (
        "Какой инструмент или приём в создании анимации показался самым важным?\n\n"
        "А) Compound Clip — наконец-то понял(а), как организовывать сложные анимации\n"
        "Б) Motion Blur — оживляет картинку и делает анимацию профессиональной\n"
        "В) Ключи и маски — теперь могу делать сложные вещи без танцев с бубном\n"
        "Г) Весь процесс от идеи до реализации наконец-то собрал(а) пазл в голове"
    ),
    (6, 4): (
        "Что полезного вынес(ла) из обзора эффектов?\n\n"
        "А) Увидел(а), какие эффекты существуют и для чего каждый нужен\n"
        "Б) Понял(а), как применять эффекты, чтобы не перегружать ролик\n"
        "В) Сохранил(а) пару эффектов в шпаргалку — буду использовать\n"
        "Г) Осознал(а), что эффекты должны работать на идею, а не просто быть"
    ),
    (6, 5): (
        "Что из урока по музыке и звукам пригодится в работе?\n\n"
        "А) Понял(а), как искать музыку под разные типы анимации\n"
        "Б) Узнал(а), как настраивать громкость, чтобы звуки не перебивали друг друга\n"
        "В) Осознал(а), что звук в анимации не фон, а часть истории\n"
        "Г) Научился(ась) использовать дополнительные звуки, чтобы оживить анимацию"
    ),
    (7, 0): (
        "Что в интерфейсе After Effects оказалось самым неожиданным или сложным для понимания?\n\n"
        "А) Понял(а) структуру программы теперь не теряюсь в панелях\n"
        "Б) Увидел(а), что AE не такой страшный, как казалось\n"
        "В) Запомнил(а) расположение основных инструментов\n"
        "Г) Пока только поверхностно, но базу ухватил(а)"
    ),
    (7, 1): (
        "Какие плагины или пресеты захотелось сразу скачать и попробовать?\n\n"
        "А) Узнал(а) про полезные плагины уже ищу, где скачать\n"
        "Б) Понял(а), как использовать готовые проекты, чтобы ускорить работу\n"
        "В) Сохранил(а) список ресурсов, где брать пресеты\n"
        "Г) Пока изучаю, но понял(а), что плагины реально экономят время"
    ),
    (7, 2): (
        "Понял(а) ли, зачем нужен Null object и где его применять?\n\n"
        "А) Да, это как контрольный объект для управления слоями — очень удобно!\n"
        "Б) Увидел(а), как с ним делать сложную анимацию проще\n"
        "В) Наконец-то разобрался(ась), что это и как работает\n"
        "Г) Пока не до конца, но буду пробовать на практике"
    ),
    (7, 3): (
        "Что нового увидел(а) на таймлайне сложного ролика?\n\n"
        "А) Понял(а), как устроены сложные проекты в AE\n"
        "Б) Увидел(а) логику организации слоёв и анимаций\n"
        "В) Вдохновился(ась) масштабом работы\n"
        "Г) Сохранил(а) структуру как пример для своих проектов"
    ),
    (8, 0): (
        "Что из основ операторского мастерства показалось самым ценным?\n\n"
        "А) Погружение в теорию, теперь понимаю, почему операторские решения работают\n"
        "Б) Узнал(а) про Лагдо Сергея Михайловича – сохраню, изучу отдельно\n"
        "В) Понял(а), как кинематографические приёмы переносить в съёмки"
    ),
    (8, 1): (
        "Какой приём работы с композицией или ракурсами хочешь попробовать в ближайшее время?\n\n"
        "А) Научусь грамотно сочетать планы, чтобы видео смотрелось профессиональнее\n"
        "Б) Узнал(а) про ракурсы, теперь кадры будут интереснее\n"
        "В) Понял(а) правила композиции\n"
        "Г) Сохранил(а) в голове основные схемы, буду применять"
    ),
    (8, 2): (
        "Какие технические настройки возьмёшь на вооружение?\n\n"
        "А) Разобрался(ась) с настройками телефона, теперь буду снимать в максимуме качества\n"
        "Б) Узнал(а) про полезные приложения для съёмки\n"
        "В) Понял(а), как выставлять камеру"
    ),
    (8, 3): (
        "Что нового про работу со светом запомнилось больше всего?\n\n"
        "А) Понял(а), как использовать естественный свет, когда нет никакого оборудования\n"
        "Б) Узнал(а) про подручные средства, которые можно использовать\n"
        "В) Теперь понимаю, какой свет купить, чтобы не выкидывать деньги впустую"
    ),
    (8, 4): (
        "Какой лайфхак по записи звука запомнился и пригодится?\n\n"
        "А) Как бороться с эхо и шумами\n"
        "Б) Какую петличку/микрофон выбрать\n"
        "В) Как записывать чистый звук в сложных условиях"
    ),
    (9, 0): (
        "Какой новый способ поиска клиентов для себя открыл(а)?\n\n"
        "А) Узнал(а) про сервисы и площадки, о которых раньше не думал(а)\n"
        "Б) Понял(а), что не только чаты с вакансиями существуют\n"
        "В) Понял(а), что важно развивать личный бренд\n"
        "Г) Осознал(а), что искать клиентов, это тоже работа и к ней нужно подходить системно"
    ),
    (9, 1): (
        "Что важного про коммерческое предложение и общение с клиентом запомнилось?\n\n"
        "А) Понял(а), когда лучше называть цену, а когда подождать\n"
        "Б) Узнал(а), как составлять бриф, чтобы сразу понять задачу клиента\n"
        "В) Разобрался(ась) в структуре КП"
    ),
    (9, 2): (
        "Какой навык ведения переговоров будешь прокачивать в первую очередь?\n\n"
        "А) Научусь вести деловую переписку уверенно и профессионально\n"
        "Б) Понял(а), как составлять ТЗ, чтобы потом не переделывать 100 раз\n"
        "В) Узнал(а) про психологию общения с клиентом"
    ),
    (9, 3): (
        "Что самое ценное вынесла из урока про ценообразование и этапы работы?\n\n"
        "А) Понял(а) стратегию, когда и как называть цену, чтобы не спугнуть клиента\n"
        "Б) Узнал(а) про декомпозицию дохода, теперь понимаю, сколько и каких клиентов нужно для желаемого заработка\n"
        "В) Осознал(а), как выбирать клиентов не только по интересу, но и по доход\n"
        "Г) Разобрался(ась) с этапами правок и сдачи"
    ),
    (9, 4): (
        "Как изменится твоё портфолио после этого урока?\n\n"
        "А) Сделаю отдельные подборки под разных клиентов, а не всё подряд\n"
        "Б) Узнал(а), что писать в описании работ, чтобы цеплять заказчиков\n"
        "В) Пересмотрю оформление, чтобы понимать, как подать себя дороже\n"
        "Г) Пойму, каких работ мне не хватает в портфолио, и добавлю их"
    ),
    (10, 0): (
        "Что из аргументов про личный бренд для монтажёра зашло больше всего?\n\n"
        "А) Понял(а), что личный бренд = социальная значимость и устойчивость\n"
        "Б) Осознал(а), что это выделяет среди толпы монтажёров с такими же навыками\n"
        "В) Увидел(а) связь между личным брендом и доверием клиентов\n"
        "Г) Раньше не задумывалась, теперь буду развивать"
    ),
    (10, 1): (
        "Какой элемент упаковки соцсетей будешь менять в первую очередь?\n\n"
        "А) Шапку профиля, сделаю понятнее и продающее\n"
        "Б) Аватарку и визуал, чтобы выглядело профессионально\n"
        "В) Хайлайтс и навигацию, чтобы клиенту было легко ориентироваться"
    ),
    (10, 2): (
        "Какую стратегию контента для себя выбрала или хочешь попробовать?\n\n"
        "А) Быть монтажёром, который иногда показывает жизнь\n"
        "Б) Быть блогером, который умеет монтировать\n"
        "В) Чисто экспертный контент только про монтаж и работу\n"
        "Г) Пока не определился(ась), но поняла, что выбор стратегии очень важно"
    ),
    (10, 3): (
        "Что понял(а) про построение стратегии для своего блога?\n\n"
        "А) Понял(а), что стратегия нужна, чтобы не постить хаотично\n"
        "Б) Составил(а) примерный план, о чём буду рассказывать\n"
        "В) Осознал(а), что регулярность важнее, чем один гениальный пост\n"
        "Г) Буду отталкиваться от целей, кого хочу привлечь и зачем"
    ),
    (11, 0): (
        "Какая нейросеть из показанных вызвала самый большой интерес и почему?\n\n"
        "А) Для генерации картинок — хочу попробовать создавать уникальные визуалы\n"
        "Б) Для монтажа — увидел(а), как AI ускоряет рутинные задачи\n"
        "В) Удивил(а) разнообразие инструментов даже не знал(а), что столько существует\n"
        "Г) Сохранил(а) список, буду внедрять понемногу в работу"
    ),
    (11, 1): (
        "Что впечатлило в процессе создания AI-ролика от идеи до результата?\n\n"
        "А) Увидел(а) полный цикл — как из идеи рождается готовое видео\n"
        "Б) Понял(а), как комбинировать нейросети на разных этапах\n"
        "В) Вдохновился(ась) результатом — это реально выглядит круто\n"
        "Г) Теперь понимаю, что AI-ролики — это доступно, а не только для профессионалов"
    ),
}


def extract_options(question_text: str) -> List[str]:
    lines = question_text.split('\n')
    options = []
    for line in lines:
        line = line.strip()
        if line and line[0] in ('А', 'Б', 'В', 'Г', 'Д') and line[1:].startswith(')'):
            options.append(line[0])
    return options


QUESTION_OPTIONS: Dict[Tuple[int, int], List[str]] = {}
for key, text in LESSON_QUESTIONS.items():
    QUESTION_OPTIONS[key] = extract_options(text)


# ===================== КЛАСС ДЛЯ УПРАВЛЕНИЯ ДАННЫМИ =====================
class DataManager:
    def __init__(self):
        self.data = None
        self.last_load = 0
        self.last_save = 0
        self.dirty = False
        self.lock = asyncio.Lock()
        self.save_task = None

    async def load(self):
        async with self.lock:
            # Создаем папку data, если ее нет
            os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

            if os.path.exists(DATA_FILE):
                try:
                    async with aiofiles.open(DATA_FILE, 'r', encoding='utf-8') as f:
                        content = await f.read()
                        self.data = json.loads(content)
                except Exception as e:
                    logging.error(f"Ошибка загрузки данных: {e}")
                    self.data = self._get_default_data()
            else:
                self.data = self._get_default_data()
                # Создаем файл при первом запуске
                await self.save(force=True)

            self._ensure_structure()
            self.last_load = time.time()
            return self.data

    def _get_default_data(self):
        return {
            "users": {},
            "lesson_stats": {},
            "module_stats": {}
        }

    def _ensure_structure(self):
        if "module_stats" not in self.data:
            self.data["module_stats"] = {}

        for user_id, user_data in self.data["users"].items():
            if "admin_message_id" not in user_data:
                user_data["admin_message_id"] = None
            if "current_module" not in user_data:
                user_data["current_module"] = None
            if "current_lesson" not in user_data:
                user_data["current_lesson"] = None
            if "module_progress" not in user_data:
                user_data["module_progress"] = {}
            if "answers" not in user_data:
                user_data["answers"] = {}
            if "feedback" not in user_data:
                user_data["feedback"] = {}
            if "video_sent" not in user_data:
                user_data["video_sent"] = False
            if "weekly_goals" not in user_data:
                user_data["weekly_goals"] = []
            if "is_admin" not in user_data:
                user_data["is_admin"] = False

    async def get(self):
        if self.data is None or (time.time() - self.last_load) > CACHE_TTL:
            await self.load()
        return self.data

    async def save(self, force=False):
        if not self.dirty and not force:
            return
        async with self.lock:
            try:
                # Создаем папку data, если ее нет
                os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

                async with aiofiles.open(DATA_FILE, 'w', encoding='utf-8') as f:
                    await f.write(json.dumps(self.data, ensure_ascii=False, indent=2))
                self.last_save = time.time()
                self.dirty = False
                logging.info(f"Данные сохранены. Пользователей: {len(self.data['users'])}")
            except Exception as e:
                logging.error(f"Ошибка сохранения данных: {e}")

    async def mark_dirty(self):
        self.dirty = True

    async def auto_save_loop(self):
        while True:
            await asyncio.sleep(SAVE_INTERVAL)
            try:
                await self.save()
            except Exception as e:
                logging.error(f"Ошибка в цикле автосохранения: {e}")

    def get_real_users(self):
        """Возвращает только не-админов"""
        if not self.data:
            return {}
        return {uid: data for uid, data in self.data["users"].items() if not data.get("is_admin", False)}


data_manager = DataManager()


# ===================== FSM =====================
class WeeklyPlanState(StatesGroup):
    waiting = State()


class WeeklyReviewState(StatesGroup):
    waiting = State()


# ===================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====================
def init_user(user_id: int, first_name: str = "", username: str = ""):
    user_id_str = str(user_id)
    now = int(time.time())

    # Если пользователь админ - не сохраняем его в статистику
    if user_id in ADMIN_IDS:
        # Но сохраняем как админа, чтобы не показывать в статистике
        if user_id_str not in data_manager.data["users"]:
            data_manager.data["users"][user_id_str] = {
                "first_name": first_name,
                "username": username,
                "first_seen": now,
                "last_active": now,
                "is_admin": True
            }
        else:
            data_manager.data["users"][user_id_str]["last_active"] = now
            data_manager.data["users"][user_id_str]["is_admin"] = True
        return

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
        "weekly_goals": [],
        "is_admin": False
    }

    if user_id_str not in data_manager.data["users"]:
        data_manager.data["users"][user_id_str] = default_user
    else:
        existing = data_manager.data["users"][user_id_str]
        # Если пользователь уже есть и это админ - пропускаем
        if existing.get("is_admin", False):
            return
        for key, value in default_user.items():
            if key not in existing:
                existing[key] = value
        existing["first_name"] = first_name
        existing["username"] = username
        existing["last_active"] = now


def update_lesson_stats(module_id: int, lesson_idx: int, old_answer: Optional[str], new_answer: str):
    lesson_key = f"module{module_id}_lesson{lesson_idx}"
    if lesson_key not in data_manager.data["lesson_stats"]:
        data_manager.data["lesson_stats"][lesson_key] = {"А": 0, "Б": 0, "В": 0, "Г": 0}
    if old_answer and old_answer in data_manager.data["lesson_stats"][lesson_key]:
        data_manager.data["lesson_stats"][lesson_key][old_answer] -= 1
    data_manager.data["lesson_stats"][lesson_key][new_answer] = data_manager.data["lesson_stats"][lesson_key].get(
        new_answer, 0) + 1

    module_key = f"module{module_id}"
    if module_key not in data_manager.data["module_stats"]:
        data_manager.data["module_stats"][module_key] = {
            "total_answers": 0,
            "answers_by_letter": {"А": 0, "Б": 0, "В": 0, "Г": 0},
            "users_completed": []
        }
    data_manager.data["module_stats"][module_key]["total_answers"] += 1
    data_manager.data["module_stats"][module_key]["answers_by_letter"][new_answer] = \
        data_manager.data["module_stats"][module_key]["answers_by_letter"].get(new_answer, 0) + 1


def mark_lesson_done(user_id: int, module_id: int, lesson_idx: int):
    user_id_str = str(user_id)
    module_str = str(module_id)

    # Если пользователь админ - не отмечаем прогресс
    if user_id in ADMIN_IDS:
        return

    if module_str not in data_manager.data["users"][user_id_str]["module_progress"]:
        data_manager.data["users"][user_id_str]["module_progress"][module_str] = [False] * len(
            MODULES[module_id]["lessons"])

    progress = data_manager.data["users"][user_id_str]["module_progress"][module_str]
    if lesson_idx < len(progress):
        progress[lesson_idx] = True
        if all(progress):
            module_key = f"module{module_id}"
            if module_key not in data_manager.data["module_stats"]:
                data_manager.data["module_stats"][module_key] = {
                    "total_answers": 0,
                    "answers_by_letter": {"А": 0, "Б": 0, "В": 0, "Г": 0},
                    "users_completed": []
                }
            if user_id_str not in data_manager.data["module_stats"][module_key]["users_completed"]:
                data_manager.data["module_stats"][module_key]["users_completed"].append(user_id_str)


def is_module_completed(user_id: int, module_id: int) -> bool:
    user_id_str = str(user_id)
    module_str = str(module_id)

    # Админы не проходят модули
    if user_id in ADMIN_IDS:
        return False

    if module_str not in data_manager.data["users"][user_id_str]["module_progress"]:
        return False
    progress = data_manager.data["users"][user_id_str]["module_progress"][module_str]
    return all(progress)


def get_user_progress(user_id: int) -> Dict[str, Any]:
    user_id_str = str(user_id)
    if user_id_str not in data_manager.data["users"]:
        return {}

    # Если пользователь админ - показываем только его прогресс, но не добавляем в статистику
    if user_id in ADMIN_IDS:
        return {
            "overall_percent": 0,
            "answered": 0,
            "total": TOTAL_LESSONS,
            "modules": {}
        }

    answers = data_manager.data["users"][user_id_str]["answers"]
    answered_lessons = len(answers)
    overall_percent = (answered_lessons / TOTAL_LESSONS * 100) if TOTAL_LESSONS else 0

    modules_progress = {}
    for mod_id, mod_info in MODULES.items():
        total_in_mod = len(mod_info["lessons"])
        answered_in_mod = sum(1 for key in answers if key.startswith(f"module{mod_id}_"))
        percent_in_mod = (answered_in_mod / total_in_mod * 100) if total_in_mod else 0
        modules_progress[mod_id] = {
            "name": mod_info["name"],
            "total": total_in_mod,
            "answered": answered_in_mod,
            "percent": percent_in_mod,
            "completed": answered_in_mod == total_in_mod
        }

    return {
        "overall_percent": overall_percent,
        "answered": answered_lessons,
        "total": TOTAL_LESSONS,
        "modules": modules_progress
    }


def get_lesson_display(module_id: int, lesson_idx: int) -> str:
    module = MODULES.get(module_id)
    if not module:
        return f"Модуль {module_id}, урок {lesson_idx + 1}"
    lesson_name = module["lessons"][lesson_idx] if lesson_idx < len(module["lessons"]) else f"Урок {lesson_idx + 1}"
    return f"Модуль {module_id}. {module['name']} – {lesson_idx + 1}) {lesson_name}"


# ===================== ФУНКЦИИ ДЛЯ СООБЩЕНИЙ =====================
async def safe_edit_message(chat_id: int, message_id: int, text: str,
                            reply_markup: Optional[InlineKeyboardMarkup] = None) -> bool:
    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=reply_markup
        )
        return True
    except TelegramBadRequest:
        return False
    except Exception:
        return False


async def get_main_message_id(user_id: int) -> Optional[int]:
    user_id_str = str(user_id)
    if user_id_str in data_manager.data["users"]:
        return data_manager.data["users"][user_id_str].get("main_message_id")
    return None


async def set_main_message_id(user_id: int, message_id: int):
    user_id_str = str(user_id)
    if user_id_str in data_manager.data["users"]:
        data_manager.data["users"][user_id_str]["main_message_id"] = message_id
        await data_manager.mark_dirty()


async def edit_main_message(user_id: int, text: str, reply_markup: Optional[InlineKeyboardMarkup] = None):
    message_id = await get_main_message_id(user_id)
    if message_id:
        success = await safe_edit_message(user_id, message_id, text, reply_markup)
        if success:
            return
    sent = await bot.send_message(chat_id=user_id, text=text, reply_markup=reply_markup)
    await set_main_message_id(user_id, sent.message_id)


async def get_admin_message_id(admin_id: int) -> Optional[int]:
    admin_id_str = str(admin_id)
    if admin_id_str in data_manager.data["users"]:
        return data_manager.data["users"][admin_id_str].get("admin_message_id")
    return None


async def set_admin_message_id(admin_id: int, message_id: int):
    admin_id_str = str(admin_id)
    if admin_id_str not in data_manager.data["users"]:
        init_user(admin_id)
    data_manager.data["users"][admin_id_str]["admin_message_id"] = message_id
    await data_manager.mark_dirty()


async def edit_admin_message(admin_id: int, text: str, reply_markup: Optional[InlineKeyboardMarkup] = None):
    message_id = await get_admin_message_id(admin_id)
    if message_id:
        success = await safe_edit_message(admin_id, message_id, text, reply_markup)
        if success:
            return
    sent = await bot.send_message(chat_id=admin_id, text=text, reply_markup=reply_markup)
    await set_admin_message_id(admin_id, sent.message_id)


async def notify_admins(text: str, delete_after: int = 60):
    for admin_id in ADMIN_IDS:
        try:
            msg = await bot.send_message(admin_id, text)
            if delete_after > 0:
                asyncio.create_task(delete_message_after(msg.chat.id, msg.message_id, delete_after))
        except Exception:
            pass


async def delete_message_after(chat_id: int, message_id: int, delay: int = 5):
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id, message_id)
    except Exception:
        pass


# ===================== МЕНЮ ПОЛЬЗОВАТЕЛЯ =====================
async def show_main_menu(user_id: int):
    builder = InlineKeyboardBuilder()
    for module_id, module_info in MODULES.items():
        builder.button(text=f"📚 Модуль {module_id}. {module_info['name']}", callback_data=f"module:{module_id}")
    builder.button(text="📊 Мой прогресс", callback_data="my_progress")
    builder.button(text="💬 Мои фидбеки", callback_data="my_feedbacks")
    builder.button(text="🎯 Мои цели", callback_data="my_goals:0")
    builder.adjust(1)

    await edit_main_message(
        user_id,
        "🌟 Приветииик! Время рефлексии 📝\n\n"
        "Расскажи, какой модуль ты сегодня проходила?\n"
        "Выбери ниже и мы вместе разберём урок, оценим прогресс и творческую энергию 🏆",
        builder.as_markup()
    )


async def show_my_progress(user_id: int):
    progress = get_user_progress(user_id)
    if not progress or progress['answered'] == 0:
        text = "📭 У вас пока нет прогресса. Начните с любого модуля!"
    else:
        lines = [f"📊 Общий прогресс: {progress['overall_percent']:.1f}%"]
        lines.append(f"📌 Пройдено уроков: {progress['answered']} из {progress['total']}\n")
        for mod_id, mod_data in progress["modules"].items():
            emoji = "✅" if mod_data["completed"] else "📖"
            lines.append(f"{emoji} Модуль {mod_id}. {mod_data['name']}")
            lines.append(f"   {mod_data['answered']}/{mod_data['total']} ({mod_data['percent']:.1f}%)")
        text = "\n".join(lines)

    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад в меню", callback_data="back_to_modules")
    await edit_main_message(user_id, text, builder.as_markup())


async def show_my_feedbacks(user_id: int):
    user_id_str = str(user_id)
    user_data = data_manager.data["users"].get(user_id_str, {})
    feedbacks = user_data.get("feedback", {})
    if not feedbacks:
        text = "📭 У вас пока нет сохранённых фидбеков."
    else:
        lines = ["💬 Ваши фидбеки по модулям:\n"]
        for mod_str, fb_list in feedbacks.items():
            mod_id = int(mod_str)
            mod_name = MODULES.get(mod_id, {}).get("name", f"Модуль {mod_id}")
            lines.append(f"📌 {mod_name}:")
            for fb in fb_list[-5:]:
                lines.append(f"   • {fb}")
            lines.append("")
        text = "\n".join(lines)

    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад в меню", callback_data="back_to_modules")
    await edit_main_message(user_id, text, builder.as_markup())


async def show_my_goals(user_id: int, page: int = 0):
    user_id_str = str(user_id)
    goals = data_manager.data["users"].get(user_id_str, {}).get("weekly_goals", [])
    if not goals:
        text = "📭 У вас пока нет записей о целях и итогах недели."
    else:
        goals_sorted = sorted(goals, key=lambda x: x["date"], reverse=True)
        per_page = 5
        total_pages = (len(goals_sorted) + per_page - 1) // per_page
        start = page * per_page
        end = start + per_page
        current = goals_sorted[start:end]

        lines = [f"🎯 Мои цели и итоги (стр. {page + 1}/{total_pages})\n"]
        for g in current:
            date_str = datetime.fromtimestamp(g["date"]).strftime("%d.%m.%Y %H:%M")
            type_str = "📝 План" if g["type"] == "plan" else "🏁 Итог"
            lines.append(f"{type_str} от {date_str}:")
            lines.append(f"{g['text']}\n")

        text = "\n".join(lines)

    builder = InlineKeyboardBuilder()
    if goals:
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"my_goals:{page - 1}"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"my_goals:{page + 1}"))
        if nav_buttons:
            builder.row(*nav_buttons)
    builder.row(InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_modules"))
    await edit_main_message(user_id, text, builder.as_markup())


async def show_module_lessons(user_id: int, module_id: int):
    module = MODULES[module_id]
    builder = InlineKeyboardBuilder()
    user_id_str = str(user_id)
    progress = data_manager.data["users"][user_id_str]["module_progress"].get(str(module_id), [])

    for idx, lesson in enumerate(module["lessons"]):
        done = idx < len(progress) and progress[idx]
        emoji = "✅" if done else "📝"
        lesson_text = f"{emoji} {idx + 1}) {lesson}"
        builder.button(text=lesson_text, callback_data=f"lesson:{module_id}:{idx}")

    builder.button(text="🔙 Назад в меню", callback_data="back_to_modules")
    builder.adjust(1)

    await edit_main_message(
        user_id,
        f"📚 Модуль {module_id}. {module['name']}\n\nВыбери урок:",
        builder.as_markup()
    )


async def show_lesson_question(user_id: int, module_id: int, lesson_idx: int):
    question_text = LESSON_QUESTIONS.get((module_id, lesson_idx))
    if not question_text:
        question_text = "Вопрос не найден."
        options = []
    else:
        options = QUESTION_OPTIONS.get((module_id, lesson_idx), [])

    builder = InlineKeyboardBuilder()
    for letter in options:
        builder.button(text=letter, callback_data=f"answer:{module_id}:{lesson_idx}:{letter}")
    builder.adjust(4)

    lesson_name = MODULES[module_id]["lessons"][lesson_idx]

    await edit_main_message(
        user_id,
        f"📖 {lesson_name}\n\n{question_text}",
        builder.as_markup()
    )


async def show_module_completion(user_id: int, module_id: int):
    module_name = MODULES[module_id]["name"]
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, напишу", callback_data=f"feedback_yes:{module_id}")
    builder.button(text="❌ Нет, всё рассказал(а)", callback_data=f"feedback_no:{module_id}")
    builder.adjust(2)

    await edit_main_message(
        user_id,
        f"🎉 Ты прошла весь модуль «{module_name}»! 💫\n\n"
        "Остались какие-то мысли, инсайты или впечатления, которыми хочешь поделиться?\n"
        "Может быть, общее ощущение от модуля или что-то, что не влезло в вопросы к урокам?",
        builder.as_markup()
    )


# ===================== АДМИНСКАЯ ПАНЕЛЬ =====================
async def show_admin_panel(admin_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Список пользователей", callback_data="admin:users:0")
    builder.button(text="📊 Статистика по модулям", callback_data="admin:module_stats")
    builder.button(text="💬 Все фидбеки", callback_data="admin:feedbacks:0")
    builder.button(text="📈 Общая статистика", callback_data="admin:overview")
    builder.button(text="📝 Ответы на /daily", callback_data="admin:daily_answers:0")
    builder.button(text="📨 Рассылка", callback_data="admin:mailing")
    builder.adjust(1)

    await edit_admin_message(
        admin_id,
        "🔧 Админ-панель\n\nВыберите раздел:",
        builder.as_markup()
    )


async def show_mailing_menu(admin_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="📝 Начало недели", callback_data="admin:mailing:plan")
    builder.button(text="📊 Конец недели", callback_data="admin:mailing:review")
    builder.button(text="🔙 Назад", callback_data="admin:back")
    builder.adjust(2)

    await edit_admin_message(
        admin_id,
        "📨 Выберите тип рассылки:",
        builder.as_markup()
    )


async def send_weekly_plan_manual(admin_id: int, status_msg: Message):
    # Получаем только реальных пользователей (не админов)
    users = list(data_manager.get_real_users().keys())
    sent = 0
    failed = 0

    for idx, user_id_str in enumerate(users):
        user_id = int(user_id_str)
        try:
            await dp.storage.set_state(chat=user_id, user=user_id, state=WeeklyPlanState)
            await bot.send_message(user_id, WEEKLY_PLAN_TEXT)
            sent += 1
            logging.info(f"Ручная рассылка (план) пользователю {user_id}")
        except Exception as e:
            failed += 1
            logging.error(f"Ошибка ручной рассылки (план) {user_id}: {e}")

        if idx < len(users) - 1:
            await asyncio.sleep(0.5)

    await status_msg.edit_text(
        f"✅ Рассылка «Начало недели» завершена!\n"
        f"📤 Отправлено: {sent}\n"
        f"❌ Ошибок: {failed}"
    )


async def send_weekly_review_manual(admin_id: int, status_msg: Message):
    # Получаем только реальных пользователей (не админов)
    users = list(data_manager.get_real_users().keys())
    sent = 0
    failed = 0

    for idx, user_id_str in enumerate(users):
        user_id = int(user_id_str)
        try:
            await dp.storage.set_state(chat=user_id, user=user_id, state=WeeklyReviewState)
            await bot.send_message(user_id, WEEKLY_REVIEW_TEXT)
            sent += 1
            logging.info(f"Ручная рассылка (итог) пользователю {user_id}")
        except Exception as e:
            failed += 1
            logging.error(f"Ошибка ручной рассылки (итог) {user_id}: {e}")

        if idx < len(users) - 1:
            await asyncio.sleep(0.5)

    await status_msg.edit_text(
        f"✅ Рассылка «Конец недели» завершена!\n"
        f"📤 Отправлено: {sent}\n"
        f"❌ Ошибок: {failed}"
    )


async def show_users_list(admin_id: int, page: int = 0):
    # Получаем только реальных пользователей (не админов)
    all_users = data_manager.data["users"].items()
    users = [(uid, data) for uid, data in all_users if not data.get("is_admin", False)]
    users.sort(key=lambda x: x[1].get("last_active", 0), reverse=True)

    if not users:
        builder = InlineKeyboardBuilder()
        builder.button(text="🔙 Назад в админку", callback_data="admin:back")
        await edit_admin_message(admin_id, "📭 Нет пользователей", builder.as_markup())
        return

    per_page = 5
    total_pages = (len(users) + per_page - 1) // per_page
    start = page * per_page
    end = start + per_page
    current_users = users[start:end]

    lines = [f"📋 Пользователи (страница {page + 1}/{total_pages})\n"]

    for user_id_str, user_data in current_users:
        name = user_data.get("first_name", "?")
        username = user_data.get("username", "")
        last_active = user_data.get("last_active", 0)
        last_active_str = datetime.fromtimestamp(last_active).strftime("%d.%m.%Y %H:%M")

        answers = len(user_data.get("answers", {}))
        progress = (answers / TOTAL_LESSONS * 100) if TOTAL_LESSONS else 0

        lines.append(f"👤 {name} @{username}")
        lines.append(f"🆔 {user_id_str}")
        lines.append(f"⏱ Последняя активность: {last_active_str}")
        lines.append(f"📊 Прогресс: {progress:.1f}% ({answers}/{TOTAL_LESSONS})")
        lines.append("")

    builder = InlineKeyboardBuilder()

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"admin:users:{page - 1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"admin:users:{page + 1}"))
    if nav_buttons:
        builder.row(*nav_buttons)

    for user_id_str, user_data in current_users:
        name = user_data.get("first_name", "?")
        short_name = name[:15] if len(name) > 15 else name
        builder.row(InlineKeyboardButton(
            text=f"👤 Подробнее: {short_name}",
            callback_data=f"admin:user:{user_id_str}"
        ))

    builder.row(InlineKeyboardButton(text="🔙 Назад в админку", callback_data="admin:back"))

    await edit_admin_message(admin_id, "\n".join(lines), builder.as_markup())


async def show_user_detail(admin_id: int, target_user_id: str):
    if target_user_id not in data_manager.data["users"]:
        await edit_admin_message(admin_id, "❌ Пользователь не найден")
        return

    u = data_manager.data["users"][target_user_id]

    # Если это админ - не показываем
    if u.get("is_admin", False):
        await edit_admin_message(admin_id, "❌ Это админ, данные скрыты")
        return

    first_seen = datetime.fromtimestamp(u.get("first_seen", 0)).strftime("%d.%m.%Y %H:%M")
    last_active = datetime.fromtimestamp(u.get("last_active", 0)).strftime("%d.%m.%Y %H:%M")

    progress = get_user_progress(int(target_user_id))

    text = [
        f"👤 Информация о пользователе\n",
        f"Имя: {u.get('first_name', '?')}",
        f"Username: @{u.get('username', '')}",
        f"ID: {target_user_id}",
        f"Первый вход: {first_seen}",
        f"Последняя активность: {last_active}",
        f"Текущий модуль: {u.get('current_module', 'Не начато')}",
        f"\n📊 Прогресс: {progress['overall_percent']:.1f}% ({progress['answered']}/{progress['total']})",
        f"\n📚 Модули:"
    ]

    for mod_id, mod_data in progress["modules"].items():
        emoji = "✅" if mod_data["completed"] else "📖"
        text.append(f"{emoji} Модуль {mod_id}. {mod_data['name']}: {mod_data['percent']:.1f}%")

    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 К списку", callback_data="admin:users:0")
    builder.button(text="🏠 В админку", callback_data="admin:back")
    builder.button(text="📝 Ответы", callback_data=f"admin:user_answers:{target_user_id}:0")
    builder.button(text="🎯 Цели", callback_data=f"admin:user_goals:{target_user_id}:0")
    builder.adjust(2)

    await edit_admin_message(admin_id, "\n".join(text), builder.as_markup())


async def show_user_answers(admin_id: int, target_user_id: str, page: int = 0):
    user_data = data_manager.data["users"].get(target_user_id)
    if not user_data or user_data.get("is_admin", False):
        await edit_admin_message(admin_id, "❌ Пользователь не найден или это админ")
        return

    answers = user_data.get("answers", {})
    if not answers:
        text = "📭 У пользователя нет ответов"
    else:
        sorted_keys = sorted(answers.keys())
        per_page = 10
        total_pages = (len(sorted_keys) + per_page - 1) // per_page
        start = page * per_page
        end = start + per_page
        current_keys = sorted_keys[start:end]

        lines = [f"📝 Ответы пользователя {target_user_id} (стр. {page + 1}/{total_pages})\n"]
        for key in current_keys:
            parts = key.split('_')
            if len(parts) == 2:
                mod = parts[0].replace('module', '')
                les = parts[1].replace('lesson', '')
                try:
                    display = get_lesson_display(int(mod), int(les))
                    lines.append(f"• {display} – {answers[key]}")
                except:
                    lines.append(f"• {key} – {answers[key]}")
            else:
                lines.append(f"• {key} – {answers[key]}")
        text = "\n".join(lines)

    builder = InlineKeyboardBuilder()
    if answers:
        nav_buttons = []
        if page > 0:
            nav_buttons.append(
                InlineKeyboardButton(text="⬅️", callback_data=f"admin:user_answers:{target_user_id}:{page - 1}"))
        if page < total_pages - 1:
            nav_buttons.append(
                InlineKeyboardButton(text="➡️", callback_data=f"admin:user_answers:{target_user_id}:{page + 1}"))
        if nav_buttons:
            builder.row(*nav_buttons)
    builder.row(InlineKeyboardButton(text="🔙 К пользователю", callback_data=f"admin:user:{target_user_id}"))

    await edit_admin_message(admin_id, text, builder.as_markup())


async def show_user_goals(admin_id: int, target_user_id: str, page: int = 0):
    user_data = data_manager.data["users"].get(target_user_id)
    if not user_data or user_data.get("is_admin", False):
        await edit_admin_message(admin_id, "❌ Пользователь не найден или это админ")
        return

    goals = user_data.get("weekly_goals", [])
    if not goals:
        text = "📭 У пользователя нет записей о целях"
    else:
        goals_sorted = sorted(goals, key=lambda x: x["date"], reverse=True)
        per_page = 5
        total_pages = (len(goals_sorted) + per_page - 1) // per_page
        start = page * per_page
        end = start + per_page
        current = goals_sorted[start:end]

        lines = [f"🎯 Цели и итоги пользователя {target_user_id} (стр. {page + 1}/{total_pages})\n"]
        for g in current:
            date_str = datetime.fromtimestamp(g["date"]).strftime("%d.%m.%Y %H:%M")
            type_str = "📝 План" if g["type"] == "plan" else "🏁 Итог"
            lines.append(f"{type_str} от {date_str}:")
            lines.append(f"{g['text']}\n")
        text = "\n".join(lines)

    builder = InlineKeyboardBuilder()
    if goals:
        nav_buttons = []
        if page > 0:
            nav_buttons.append(
                InlineKeyboardButton(text="⬅️", callback_data=f"admin:user_goals:{target_user_id}:{page - 1}"))
        if page < total_pages - 1:
            nav_buttons.append(
                InlineKeyboardButton(text="➡️", callback_data=f"admin:user_goals:{target_user_id}:{page + 1}"))
        if nav_buttons:
            builder.row(*nav_buttons)
    builder.row(InlineKeyboardButton(text="🔙 К пользователю", callback_data=f"admin:user:{target_user_id}"))

    await edit_admin_message(admin_id, text, builder.as_markup())


async def show_module_stats(admin_id: int):
    lesson_stats = data_manager.data.get("lesson_stats", {})
    if not lesson_stats:
        await edit_admin_message(admin_id, "📊 Статистика по урокам пока отсутствует.")
        return

    modules_text = []
    for module_id, module_info in MODULES.items():
        module_lines = [f"📚 Модуль {module_id}. {module_info['name']}"]
        for lesson_idx, lesson_name in enumerate(module_info["lessons"]):
            key = f"module{module_id}_lesson{lesson_idx}"
            stats = lesson_stats.get(key, {"А": 0, "Б": 0, "В": 0, "Г": 0})
            total = sum(stats.values())
            if total == 0:
                continue
            module_lines.append(f"  {lesson_idx + 1}. {lesson_name[:30]}...")
            options = QUESTION_OPTIONS.get((module_id, lesson_idx), [])
            parts = []
            for letter in options:
                parts.append(f"{letter}:{stats.get(letter, 0)}")
            if parts:
                module_lines.append(f"     {' '.join(parts)} (всего {total})")
        if len(module_lines) > 1:
            modules_text.extend(module_lines)
            modules_text.append("")

    if not modules_text:
        await edit_admin_message(admin_id, "📊 Статистика по урокам пока отсутствует.")
        return

    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад в админку", callback_data="admin:back")
    await edit_admin_message(admin_id, "\n".join(modules_text), builder.as_markup())


async def show_feedbacks(admin_id: int, page: int = 0):
    all_feedbacks = []
    for user_id_str, user_data in data_manager.data["users"].items():
        # Пропускаем админов
        if user_data.get("is_admin", False):
            continue
        feedbacks = user_data.get("feedback", {})
        for mod_str, fb_list in feedbacks.items():
            mod_id = int(mod_str)
            mod_name = MODULES.get(mod_id, {}).get("name", f"Модуль {mod_id}")
            name = user_data.get("first_name", "?")
            username = user_data.get("username", "")
            for fb in fb_list:
                all_feedbacks.append({
                    "user_id": user_id_str,
                    "name": name,
                    "username": username,
                    "module": mod_name,
                    "module_id": mod_id,
                    "text": fb,
                    "time": user_data.get("last_active", 0)
                })

    all_feedbacks.sort(key=lambda x: x["time"], reverse=True)

    if not all_feedbacks:
        builder = InlineKeyboardBuilder()
        builder.button(text="🔙 Назад в админку", callback_data="admin:back")
        await edit_admin_message(admin_id, "📭 Нет фидбеков", builder.as_markup())
        return

    per_page = 3
    total_pages = (len(all_feedbacks) + per_page - 1) // per_page
    start = page * per_page
    end = start + per_page
    current = all_feedbacks[start:end]

    lines = [f"💬 Все фидбеки (страница {page + 1}/{total_pages})\n"]
    for fb in current:
        lines.append(f"👤 {fb['name']} (@{fb['username']})")
        lines.append(f"🆔 {fb['user_id']}")
        lines.append(f"📌 {fb['module']}")
        lines.append(f"💭 {fb['text']}\n")

    builder = InlineKeyboardBuilder()
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"admin:feedbacks:{page - 1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"admin:feedbacks:{page + 1}"))
    if nav_buttons:
        builder.row(*nav_buttons)
    builder.row(InlineKeyboardButton(text="🔙 Назад в админку", callback_data="admin:back"))

    await edit_admin_message(admin_id, "\n".join(lines), builder.as_markup())


async def show_overview(admin_id: int):
    # Получаем только реальных пользователей (не админов)
    real_users = [u for u in data_manager.data["users"].values() if not u.get("is_admin", False)]

    total_users = len(real_users)
    active_users = sum(1 for u in real_users if u.get("last_active", 0) > time.time() - 86400)
    total_answers = sum(len(u.get("answers", {})) for u in real_users)
    total_feedbacks = sum(len(fb) for u in real_users for fb in u.get("feedback", {}).values())

    module_stats = {}
    for user in real_users:
        for mod_str, prog in user.get("module_progress", {}).items():
            if all(prog):
                module_stats[mod_str] = module_stats.get(mod_str, 0) + 1

    text = [
        "📈 Общая статистика\n",
        f"👥 Всего пользователей: {total_users}",
        f"✅ Активных за сутки: {active_users}",
        f"📝 Всего ответов на уроки: {total_answers}",
        f"💬 Всего фидбеков: {total_feedbacks}\n",
        "📊 Прохождение модулей:"
    ]

    for module_id, module_info in MODULES.items():
        completed = module_stats.get(str(module_id), 0)
        percent = (completed / total_users * 100) if total_users else 0
        text.append(f"• Модуль {module_id}: {completed} чел. ({percent:.1f}%)")

    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Обновить", callback_data="admin:overview")
    builder.button(text="🔙 Назад", callback_data="admin:back")
    builder.adjust(2)

    await edit_admin_message(admin_id, "\n".join(text), builder.as_markup())


async def show_all_daily_answers(admin_id: int, page: int = 0):
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад в админку", callback_data="admin:back")
    await edit_admin_message(admin_id, "📭 Нет ответов на /daily", builder.as_markup())


# ===================== КОМАНДЫ ДЛЯ АДМИНОВ =====================

@dp.message(Command("test_plan"))
async def cmd_test_plan(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ У вас нет прав для использования этой команды")
        return

    await state.clear()
    await message.answer(WEEKLY_PLAN_TEXT)
    await message.answer("✅ Тестовое сообщение (план) отправлено вам.")


@dp.message(Command("test_review"))
async def cmd_test_review(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ У вас нет прав для использования этой команды")
        return

    await state.clear()
    await message.answer(WEEKLY_REVIEW_TEXT)
    await message.answer("✅ Тестовое сообщение (итог) отправлено вам.")


@dp.message(Command("send_plan"))
async def cmd_send_plan(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ У вас нет прав для использования этой команды")
        return

    await state.clear()
    status_msg = await message.answer("🔄 Начинаю массовую рассылку (план)...")

    # Получаем только реальных пользователей (не админов)
    users = list(data_manager.get_real_users().keys())
    sent = 0
    failed = 0

    for idx, user_id_str in enumerate(users):
        user_id = int(user_id_str)
        try:
            await dp.storage.set_state(chat=user_id, user=user_id, state=WeeklyPlanState)
            await bot.send_message(user_id, WEEKLY_PLAN_TEXT)
            sent += 1
        except Exception as e:
            failed += 1
            logging.error(f"Ошибка рассылки (план) {user_id}: {e}")

        if idx < len(users) - 1:
            await asyncio.sleep(0.5)

    await status_msg.edit_text(
        f"✅ Рассылка «Начало недели» завершена!\n"
        f"📤 Отправлено: {sent}\n"
        f"❌ Ошибок: {failed}"
    )


@dp.message(Command("send_review"))
async def cmd_send_review(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ У вас нет прав для использования этой команды")
        return

    await state.clear()
    status_msg = await message.answer("🔄 Начинаю массовую рассылку (итог)...")

    # Получаем только реальных пользователей (не админов)
    users = list(data_manager.get_real_users().keys())
    sent = 0
    failed = 0

    for idx, user_id_str in enumerate(users):
        user_id = int(user_id_str)
        try:
            await dp.storage.set_state(chat=user_id, user=user_id, state=WeeklyReviewState)
            await bot.send_message(user_id, WEEKLY_REVIEW_TEXT)
            sent += 1
        except Exception as e:
            failed += 1
            logging.error(f"Ошибка рассылки (итог) {user_id}: {e}")

        if idx < len(users) - 1:
            await asyncio.sleep(0.5)

    await status_msg.edit_text(
        f"✅ Рассылка «Конец недели» завершена!\n"
        f"📤 Отправлено: {sent}\n"
        f"❌ Ошибок: {failed}"
    )


# ===================== ХЭНДЛЕРЫ КОМАНД =====================
# ===================== ХЭНДЛЕРЫ КОМАНД =====================
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = message.from_user
    await data_manager.get()
    init_user(user.id, user.first_name, user.username)
    user_data = data_manager.data["users"][str(user.id)]

    print(f"📩 Пользователь {user.id} (@{user.username}) запустил бота", flush=True)
    print(f"📹 video_sent: {user_data.get('video_sent', False)}", flush=True)

    if not user_data.get("video_sent", False):
        print(f"🎬 Отправка кружка пользователю {user.id}...", flush=True)

        try:
            # Сначала пробуем отправить по file_id (если есть)
            if VIDEO_NOTE_FILE_ID:
                print(f"📤 Отправка по file_id: {VIDEO_NOTE_FILE_ID[:20]}...", flush=True)
                await bot.send_video_note(
                    chat_id=user.id,
                    video_note=VIDEO_NOTE_FILE_ID
                )
                user_data["video_sent"] = True
                await data_manager.mark_dirty()
                print(f"✅ Кружок отправлен пользователю {user.id} по file_id", flush=True)
                await asyncio.sleep(0.5)
            else:
                # Если file_id нет - пробуем файл
                video_note_path = "video_notes/welcome_2.mp4"
                print(f"📤 Отправка из файла: {video_note_path}", flush=True)

                if os.path.exists(video_note_path):
                    print(f"✅ Файл найден, размер: {os.path.getsize(video_note_path)} байт", flush=True)
                    video_note = FSInputFile(video_note_path)
                    await bot.send_video_note(chat_id=user.id, video_note=video_note)
                    user_data["video_sent"] = True
                    await data_manager.mark_dirty()
                    print(f"✅ Кружок отправлен пользователю {user.id} из файла", flush=True)
                    await asyncio.sleep(0.5)
                else:
                    print(f"❌ Файл {video_note_path} не найден!", flush=True)
                    await message.answer("🎬 *Видео не найдено, но урок доступен по кнопке ниже!*",
                                         parse_mode="Markdown")
        except Exception as e:
            print(f"❌ Ошибка отправки кружка пользователю {user.id}: {e}", flush=True)
            logging.error(f"Ошибка отправки кружка: {e}")
            await message.answer("❌ *Ошибка при отправке видео. Попробуйте позже.*", parse_mode="Markdown")
    else:
        print(f"⏭️ Пропуск отправки кружка (уже отправлен) для {user.id}", flush=True)

    await show_main_menu(user.id)


@dp.message(Command("stats"))
async def cmd_stats(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ У вас нет прав")
        return

    await state.clear()
    await data_manager.get()

    # Сохраняем админа как админа (не показываем в статистике)
    user_id_str = str(message.from_user.id)
    if user_id_str not in data_manager.data["users"]:
        data_manager.data["users"][user_id_str] = {
            "first_name": message.from_user.first_name,
            "username": message.from_user.username,
            "first_seen": int(time.time()),
            "last_active": int(time.time()),
            "is_admin": True
        }
        await data_manager.mark_dirty()

    await show_admin_panel(message.from_user.id)


# ===================== ПОЛЬЗОВАТЕЛЬСКИЕ CALLBACK =====================
@dp.callback_query(F.data == "back_to_modules")
async def back_to_modules(callback: CallbackQuery):
    user = callback.from_user
    init_user(user.id, user.first_name, user.username)
    await data_manager.mark_dirty()
    await callback.answer()
    await show_main_menu(user.id)


@dp.callback_query(F.data == "my_progress")
async def my_progress(callback: CallbackQuery):
    user = callback.from_user
    init_user(user.id, user.first_name, user.username)
    await data_manager.mark_dirty()
    await callback.answer()
    await show_my_progress(user.id)


@dp.callback_query(F.data == "my_feedbacks")
async def my_feedbacks(callback: CallbackQuery):
    user = callback.from_user
    init_user(user.id, user.first_name, user.username)
    await data_manager.mark_dirty()
    await callback.answer()
    await show_my_feedbacks(user.id)


@dp.callback_query(F.data.startswith("my_goals:"))
async def my_goals(callback: CallbackQuery):
    user = callback.from_user
    init_user(user.id, user.first_name, user.username)
    await data_manager.mark_dirty()
    await callback.answer()
    page = int(callback.data.split(":")[1])
    await show_my_goals(user.id, page)


@dp.callback_query(F.data.startswith("module:"))
async def process_module(callback: CallbackQuery):
    user = callback.from_user
    init_user(user.id, user.first_name, user.username)
    await data_manager.mark_dirty()
    await callback.answer()

    module_id = int(callback.data.split(":")[1])
    data_manager.data["users"][str(user.id)]["current_module"] = module_id
    await data_manager.mark_dirty()
    await show_module_lessons(user.id, module_id)


@dp.callback_query(F.data.startswith("lesson:"))
async def process_lesson(callback: CallbackQuery):
    user = callback.from_user
    init_user(user.id, user.first_name, user.username)
    await data_manager.mark_dirty()
    await callback.answer()

    _, module_id_str, lesson_idx_str = callback.data.split(":")
    module_id = int(module_id_str)
    lesson_idx = int(lesson_idx_str)

    data_manager.data["users"][str(user.id)]["current_module"] = module_id
    data_manager.data["users"][str(user.id)]["current_lesson"] = lesson_idx
    await data_manager.mark_dirty()
    await show_lesson_question(user.id, module_id, lesson_idx)


@dp.callback_query(F.data.startswith("answer:"))
async def process_answer(callback: CallbackQuery):
    await callback.answer()
    _, module_id_str, lesson_idx_str, letter = callback.data.split(":")
    module_id = int(module_id_str)
    lesson_idx = int(lesson_idx_str)
    user_id = callback.from_user.id

    user = callback.from_user
    init_user(user_id, user.first_name, user.username)

    answer_key = f"module{module_id}_lesson{lesson_idx}"
    old_answer = data_manager.data["users"][str(user_id)]["answers"].get(answer_key)

    update_lesson_stats(module_id, lesson_idx, old_answer, letter)
    data_manager.data["users"][str(user_id)]["answers"][answer_key] = letter
    mark_lesson_done(user_id, module_id, lesson_idx)
    await data_manager.mark_dirty()

    if is_module_completed(user_id, module_id):
        await show_module_completion(user_id, module_id)
    else:
        await show_module_lessons(user_id, module_id)


# ===================== ОБРАБОТЧИК ФИДБЕКА (БЕЗ FSM) =====================

# Словарь для хранения временных данных фидбека
feedback_temp = {}


@dp.callback_query(F.data.startswith("feedback_yes:"))
async def feedback_yes(callback: CallbackQuery):
    user = callback.from_user
    init_user(user.id, user.first_name, user.username)
    await data_manager.mark_dirty()
    await callback.answer()

    module_id = int(callback.data.split(":")[1])

    # Сохраняем модуль для фидбека во временный словарь
    feedback_temp[user.id] = module_id

    await edit_main_message(
        user.id,
        "📝 Напиши свой фидбек по модулю в ответ на это сообщение:",
        reply_markup=None
    )


@dp.callback_query(F.data.startswith("feedback_no:"))
async def feedback_no(callback: CallbackQuery):
    user = callback.from_user
    init_user(user.id, user.first_name, user.username)
    await data_manager.mark_dirty()
    await callback.answer()
    await show_main_menu(user.id)


@dp.message(F.text)
async def process_feedback(message: Message):
    user_id = message.from_user.id

    # Проверяем, есть ли пользователь в временном словаре
    if user_id not in feedback_temp:
        return

    module_id = feedback_temp[user_id]
    user = message.from_user
    init_user(user_id, user.first_name, user.username)
    await data_manager.mark_dirty()

    # Удаляем из временного словаря
    del feedback_temp[user_id]

    module_str = str(module_id)
    if module_str not in data_manager.data["users"][str(user_id)]["feedback"]:
        data_manager.data["users"][str(user_id)]["feedback"][module_str] = []

    data_manager.data["users"][str(user_id)]["feedback"][module_str].append(message.text)
    await data_manager.mark_dirty()

    user_info = f"{message.from_user.first_name} (@{message.from_user.username})"
    module_name = MODULES[module_id]['name']
    admin_text = (
        f"💬 Новый фидбек!\n\n"
        f"👤 {user_info}\n"
        f"🆔 {user_id}\n"
        f"📌 Модуль {module_id}. {module_name}\n\n"
        f"💭 {message.text}"
    )
    await notify_admins(admin_text, delete_after=60)

    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except Exception:
        pass

    thank_message = await message.answer("✨ Спасибо за ответ! 🤍")
    asyncio.create_task(delete_message_after(thank_message.chat.id, thank_message.message_id, 3))

    await show_main_menu(user_id)


# ===================== ОБРАБОТЧИКИ ОТВЕТОВ НА НЕДЕЛЬНЫЕ ВОПРОСЫ =====================
@dp.message(WeeklyPlanState)
async def process_weekly_plan(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = message.from_user
    init_user(user_id, user.first_name, user.username)

    goal_entry = {
        "date": int(time.time()),
        "type": "plan",
        "text": message.text
    }
    data_manager.data["users"][str(user_id)]["weekly_goals"].append(goal_entry)
    await data_manager.mark_dirty()

    user_info = f"{message.from_user.first_name} (@{message.from_user.username})"
    admin_text = f"📝 Новый план на неделю от {user_info} (ID {user_id}):\n\n{message.text}"
    await notify_admins(admin_text, delete_after=60)

    thank = await message.answer("✨ Спасибо! Твои цели записаны. Удачи на неделе! 🤍")
    asyncio.create_task(delete_message_after(message.chat.id, message.message_id, 2))
    asyncio.create_task(delete_message_after(thank.chat.id, thank.message_id, 2))

    await state.clear()


@dp.message(WeeklyReviewState)
async def process_weekly_review(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = message.from_user
    init_user(user_id, user.first_name, user.username)

    goal_entry = {
        "date": int(time.time()),
        "type": "review",
        "text": message.text
    }
    data_manager.data["users"][str(user_id)]["weekly_goals"].append(goal_entry)
    await data_manager.mark_dirty()

    user_info = f"{message.from_user.first_name} (@{message.from_user.username})"
    admin_text = f"🏁 Новый итог недели от {user_info} (ID {user_id}):\n\n{message.text}"
    await notify_admins(admin_text, delete_after=60)

    thank = await message.answer("✨ Спасибо! Твои итоги сохранены. Отличной недели! 🤍")
    asyncio.create_task(delete_message_after(message.chat.id, message.message_id, 2))
    asyncio.create_task(delete_message_after(thank.chat.id, thank.message_id, 2))

    await state.clear()


# ===================== АДМИНСКИЕ CALLBACK =====================
@dp.callback_query(F.data.startswith("admin:"))
async def admin_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    if callback.from_user.id not in ADMIN_IDS:
        return

    user = callback.from_user
    init_user(user.id, user.first_name, user.username)
    await data_manager.mark_dirty()

    parts = callback.data.split(":")
    action = parts[1]

    if action == "back":
        await show_admin_panel(callback.from_user.id)
    elif action == "mailing":
        await show_mailing_menu(callback.from_user.id)
    elif action == "mailing:plan":
        status_msg = await bot.send_message(callback.from_user.id, "🔄 Начинаю рассылку «Начало недели»...")
        await send_weekly_plan_manual(callback.from_user.id, status_msg)
    elif action == "mailing:review":
        status_msg = await bot.send_message(callback.from_user.id, "🔄 Начинаю рассылку «Конец недели»...")
        await send_weekly_review_manual(callback.from_user.id, status_msg)
    elif action == "users":
        page = int(parts[2]) if len(parts) > 2 else 0
        await show_users_list(callback.from_user.id, page)
    elif action == "user":
        target_id = parts[2]
        await show_user_detail(callback.from_user.id, target_id)
    elif action == "user_answers":
        target_id = parts[2]
        page = int(parts[3])
        await show_user_answers(callback.from_user.id, target_id, page)
    elif action == "user_goals":
        target_id = parts[2]
        page = int(parts[3])
        await show_user_goals(callback.from_user.id, target_id, page)
    elif action == "module_stats":
        await show_module_stats(callback.from_user.id)
    elif action == "feedbacks":
        page = int(parts[2]) if len(parts) > 2 else 0
        await show_feedbacks(callback.from_user.id, page)
    elif action == "overview":
        await show_overview(callback.from_user.id)
    elif action == "daily_answers":
        page = int(parts[2]) if len(parts) > 2 else 0
        await show_all_daily_answers(callback.from_user.id, page)


# ===================== ЗАПУСК =====================
async def on_startup():
    print(f"📂 Загрузка данных из: {DATA_FILE}", flush=True)
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
    logging.getLogger(__name__).setLevel(logging.INFO)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    print("🔄 Запуск polling...", flush=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("👋 Бот остановлен пользователем", flush=True)
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}", flush=True)
        sys.exit(1)