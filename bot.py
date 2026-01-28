import os
import asyncio
import aiohttp
import json
import uuid
import glob
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from dotenv import load_dotenv
from aiohttp import web, MultipartReader

# Загружаем переменные из .env
load_dotenv()

# ============== КОНФИГУРАЦИЯ ==============
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
COMFY_URL = os.getenv("COMFY_URL", "http://127.0.0.1:18188")
INPUT_DIR = os.getenv("INPUT_DIR", "/workspace/ComfyUI/input")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "/workspace/ComfyUI/output")

# Telegram Bot API Local Server (для файлов >20MB)
TELEGRAM_API_SERVER = os.getenv("TELEGRAM_API_SERVER", "https://api.telegram.org")

# ВАЖНО ДЛЯ VAST.AI:
# В Docker Options добавь: -p 8765:8765
# Это откроет порт и создаст переменную окружения VAST_TCP_PORT_8765

# Глобальные переменные (не используются, только для совместимости)
EXTERNAL_IP = "127.0.0.1"
VAST_EXTERNAL_PORT = 8765

# Создаём директории
os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Файлы данных
WHITELIST_FILE = "whitelist.txt"
USER_SETTINGS_FILE = "user_settings.json"

# ============== ЯЗЫКОВЫЕ ПАКЕТЫ ==============
LANGUAGES = {
    "en": {
        "start_welcome": "👋 Welcome! Choose workflow:",
        "choose_resolution": "📐 Choose resolution:",
        "send_photo": "🖼️ Send a photo",
        "send_video": "🎬 Send a video",
        "send_audio": "🎵 Send audio",
        "send_prompt": "✍️ Send prompt\n(Example: 'a man talking')",
        "cancel": "❌ Cancel",
        "cancelled": "❌ Cancelled. /start for new request",
        "photo_received": "✅ Photo received!\n\n🎵 Send audio",
        "video_received": "✅ Video received!\n\n🎵 Send audio",
        "audio_received": "✅ Audio received!\n\n✍️ Send prompt\n(Example: 'a man talking')",
        "starting_generation": "🚀 Starting generation...",
        "processing": "⏳ Processing...\n\nUse /cancel to stop",
        "done": "✅ Done!\n\n",
        "completed": "✨ Completed! /start for new",
        "error": "❌ Error: {}\n\n/start to retry",
        "system_busy": "⏳ System is busy",
        "expected_photo": "Expected photo",
        "expected_video": "Expected video",
        "choose_from_menu": "Choose from menu",
        "choose_from_options": "Choose from provided options",
        "file_too_large": "📤 File too large ({:.1f} MB)\nUpload via: http://127.0.0.1:{}/upload\nFilename must start with '{}'",
        "video_ready_download": "✅ Video ready!\n\n📊 Size: {:.1f} MB\n📥 Download:\n{}",
        "no_access": "❌ You don't have access to this bot",
        "admin_only": "❌ This command is for admin only",
        "user_added": "✅ User {} added to whitelist",
        "user_removed": "✅ User {} removed from whitelist",
        "user_not_found": "❌ User {} not found in whitelist",
        "cannot_remove_admin": "❌ Cannot remove administrator",
        "whitelist_empty": "📝 Whitelist is empty",
        "whitelist_title": "📝 Whitelist ({} users):\n\n{}",
        "your_id": "🆔 Your ID: {}",
        "invalid_user_id": "❌ Invalid user ID format",
        "usage_add": "Usage: /add USER_ID\nExample: /add 123456789",
        "usage_remove": "Usage: /remove USER_ID\nExample: /remove 123456789",
        "no_active_workflow": "ℹ️ No active workflow to cancel",
        "can_cancel_own_only": "❌ You can only cancel your own workflow",
        "workflow_cancelled": "✅ Workflow cancelled",
        "cancel_failed": "❌ Failed to cancel workflow",
        "i2v_workflow": "📸 Photo to video (i2v)",
        "v2v_workflow": "🎬 Video to video (v2v)",
        "settings": "⚙️ Settings",
        "settings_menu": "⚙️ Settings\n\nCurrent language: {}\nDenoise strength: {:.2f}",
        "change_language": "🌐 Change language",
        "change_denoise": "🎚️ Denoise strength",
        "back": "◀️ Back",
        "language_changed": "✅ Language changed to English",
        "denoise_current": "🎚️ Current denoise strength: {:.2f}\n\nSend new value (0.10 - 1.00)\nExample: 0.55",
        "denoise_updated": "✅ Denoise strength updated: {:.2f}",
        "denoise_invalid": "❌ Invalid value. Send a number between 0.10 and 1.00\nExample: 0.55",
        "choose_language": "🌐 Choose language:",
        "file_not_found": "❌ File not found"
    },
    "ru": {
        "start_welcome": "👋 Привет! Выбери воркфлоу:",
        "choose_resolution": "📐 Выбери разрешение:",
        "send_photo": "🖼️ Отправь фото",
        "send_video": "🎬 Отправь видео",
        "send_audio": "🎵 Отправьте аудио",
        "send_prompt": "✍️ Отправьте промпт\n(Например: 'a man talking')",
        "cancel": "❌ Отменить",
        "cancelled": "❌ Отменено. /start для нового запроса",
        "photo_received": "✅ Фото получено!\n\n🎵 Отправьте аудио",
        "video_received": "✅ Видео получено!\n\n🎵 Отправьте аудио",
        "audio_received": "✅ Аудио получено!\n\n✍️ Отправьте промпт\n(Например: 'a man talking')",
        "starting_generation": "🚀 Запускаю генерацию...",
        "processing": "⏳ Обработка...\n\nДля отмены используйте /cancel",
        "done": "✅ Готово!\n\n",
        "completed": "✨ Завершено! /start для нового",
        "error": "❌ Ошибка: {}\n\n/start для повтора",
        "system_busy": "⏳ Система занята",
        "expected_photo": "Ожидается фото",
        "expected_video": "Ожидается видео",
        "choose_from_menu": "Выбери из меню",
        "choose_from_options": "Выбери из предложенных",
        "file_too_large": "📤 Файл слишком большой ({:.1f} MB)\nЗагрузи через: http://127.0.0.1:{}/upload\nИмя файла должно начинаться с '{}'",
        "video_ready_download": "✅ Видео готово!\n\n📊 Размер: {:.1f} MB\n📥 Скачай по ссылке:\n{}",
        "no_access": "❌ У вас нет доступа к боту",
        "admin_only": "❌ Эта команда доступна только администратору",
        "user_added": "✅ Пользователь {} добавлен в whitelist",
        "user_removed": "✅ Пользователь {} удалён из whitelist",
        "user_not_found": "❌ Пользователь {} не найден в whitelist",
        "cannot_remove_admin": "❌ Нельзя удалить администратора",
        "whitelist_empty": "📝 Whitelist пуст",
        "whitelist_title": "📝 Whitelist ({} пользователей):\n\n{}",
        "your_id": "🆔 Ваш ID: {}",
        "invalid_user_id": "❌ Неверный формат ID пользователя",
        "usage_add": "Использование: /add USER_ID\nПример: /add 123456789",
        "usage_remove": "Использование: /remove USER_ID\nПример: /remove 123456789",
        "no_active_workflow": "ℹ️ Нет активного воркфлоу для отмены",
        "can_cancel_own_only": "❌ Вы можете отменить только свой воркфлоу",
        "workflow_cancelled": "✅ Воркфлоу отменён",
        "cancel_failed": "❌ Не удалось отменить воркфлоу",
        "i2v_workflow": "📸 Фото в видео (i2v)",
        "v2v_workflow": "🎬 Видео в видео (v2v)",
        "settings": "⚙️ Настройки",
        "settings_menu": "⚙️ Настройки\n\nТекущий язык: {}\nDenoise strength: {:.2f}",
        "change_language": "🌐 Сменить язык",
        "change_denoise": "🎚️ Denoise strength",
        "back": "◀️ Назад",
        "language_changed": "✅ Язык изменен на Русский",
        "denoise_current": "🎚️ Текущий denoise strength: {:.2f}\n\nОтправь новое значение (0.10 - 1.00)\nПример: 0.55",
        "denoise_updated": "✅ Denoise strength обновлён: {:.2f}",
        "denoise_invalid": "❌ Неверное значение. Отправь число от 0.10 до 1.00\nПример: 0.55",
        "choose_language": "🌐 Выбери язык:",
        "file_not_found": "❌ Файл не найден"
    }
}

# ============== ПОЛЬЗОВАТЕЛЬСКИЕ НАСТРОЙКИ ==============
def load_user_settings():
    """Загружает настройки пользователей"""
    if not os.path.exists(USER_SETTINGS_FILE):
        return {}
    try:
        with open(USER_SETTINGS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_user_settings(settings):
    """Сохраняет настройки пользователей"""
    with open(USER_SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)

def get_user_setting(user_id, key, default=None):
    """Получает настройку пользователя"""
    settings = load_user_settings()
    user_str = str(user_id)
    if user_str not in settings:
        settings[user_str] = {}
    return settings[user_str].get(key, default)

def set_user_setting(user_id, key, value):
    """Устанавливает настройку пользователя"""
    settings = load_user_settings()
    user_str = str(user_id)
    if user_str not in settings:
        settings[user_str] = {}
    settings[user_str][key] = value
    save_user_settings(settings)

def get_user_language(user_id):
    """Получает язык пользователя"""
    return get_user_setting(user_id, "language", "en")

def get_text(user_id, key, *args):
    """Получает текст на языке пользователя"""
    lang = get_user_language(user_id)
    text = LANGUAGES[lang].get(key, LANGUAGES["en"].get(key, key))
    if args:
        return text.format(*args)
    return text

def get_user_denoise(user_id):
    """Получает denoise strength пользователя"""
    return get_user_setting(user_id, "denoise_strength", 0.55)

# ============== ЗАГРУЗКА БОЛЬШИХ ФАЙЛОВ ==============
# ============== WHITELIST ==============
def load_whitelist():
    """Загружает whitelist из файла"""
    if not os.path.exists(WHITELIST_FILE):
        # Создаём файл с админом
        with open(WHITELIST_FILE, "w") as f:
            f.write(f"{ADMIN_ID}\n")
        return {ADMIN_ID}
    
    with open(WHITELIST_FILE, "r") as f:
        return {int(line.strip()) for line in f if line.strip().isdigit()}

def save_whitelist(whitelist):
    """Сохраняет whitelist в файл"""
    with open(WHITELIST_FILE, "w") as f:
        for user_id in sorted(whitelist):
            f.write(f"{user_id}\n")

whitelist = load_whitelist()

# ============== FSM STATES ==============
class GenerationStates(StatesGroup):
    choosing_workflow = State()
    choosing_resolution = State()
    waiting_media = State()
    waiting_audio = State()
    waiting_prompt = State()

class SettingsStates(StatesGroup):
    main_menu = State()
    changing_denoise = State()

# ============== РАЗРЕШЕНИЯ ==============
RESOLUTIONS = {
    "640x640": (640, 640),
    "720x1280": (720, 1280),
    "1280x720": (1280, 720),
    "512x512": (512, 512),
    "768x768": (768, 768),
}

# ============== ИНИЦИАЛИЗАЦИЯ ==============
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer

# Если указан локальный Bot API Server - используем его
if TELEGRAM_API_SERVER != "https://api.telegram.org":
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(TELEGRAM_API_SERVER)
    )
    bot = Bot(token=TOKEN, session=session)
    print(f"🔧 Using Local Bot API Server: {TELEGRAM_API_SERVER}")
else:
    bot = Bot(token=TOKEN)
    print(f"🔧 Using Official Bot API: https://api.telegram.org")

dp = Dispatcher(storage=MemoryStorage())
is_busy = False
current_user = None
current_prompt_id = None  # Для отмены воркфлоу

# ============== КЛАВИАТУРЫ ==============
def get_workflow_keyboard(user_id):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=get_text(user_id, "i2v_workflow"))],
            [KeyboardButton(text=get_text(user_id, "v2v_workflow"))],
            [KeyboardButton(text=get_text(user_id, "settings"))]
        ],
        resize_keyboard=True
    )

def get_resolution_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="640x640"), KeyboardButton(text="720x1280")],
            [KeyboardButton(text="1280x720"), KeyboardButton(text="512x512")],
            [KeyboardButton(text="768x768")]
        ],
        resize_keyboard=True
    )

def get_cancel_keyboard(user_id):
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=get_text(user_id, "cancel"))]],
        resize_keyboard=True
    )

def get_settings_keyboard(user_id):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=get_text(user_id, "change_language"))],
            [KeyboardButton(text=get_text(user_id, "change_denoise"))],
            [KeyboardButton(text=get_text(user_id, "back"))]
        ],
        resize_keyboard=True
    )

def get_language_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🇬🇧 English"), KeyboardButton(text="🇷🇺 Русский")]
        ],
        resize_keyboard=True
    )

# ============== ПРОВЕРКА ДОСТУПА ==============
def check_access(user_id):
    """Проверяет доступ пользователя"""
    return user_id in whitelist

def is_admin(user_id):
    """Проверяет является ли пользователь админом"""
    return user_id == ADMIN_ID

# ============== ОЧИСТКА INPUT ==============
def cleanup_input_dir():
    """Очищает папку input от всех файлов"""
    try:
        patterns = ['*.jpg', '*.jpeg', '*.png', '*.mp4', '*.avi', '*.mov', '*.mp3', '*.wav', '*.ogg']
        for pattern in patterns:
            for file in glob.glob(os.path.join(INPUT_DIR, pattern)):
                try:
                    os.remove(file)
                except:
                    pass
    except Exception as e:
        print(f"Ошибка очистки input: {e}")

# ============== ЗАГРУЗКА ВОРКФЛОУ ==============
def load_workflow(workflow_type):
    """Загружает воркфлоу из JSON файла"""
    if workflow_type == "i2v":
        workflow_path = "InfiniteTalk_i2v.json"
    else:  # v2v
        workflow_path = "wanvideo_InfiniteTalk_videoToVideo.json"
    
    with open(workflow_path, "r", encoding="utf-8") as f:
        return json.load(f)

# ============== ADMIN КОМАНДЫ ==============
@dp.message(Command("add"))
async def cmd_add_user(message: types.Message):
    """Добавить пользователя в whitelist (только админ)"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Эта команда доступна только администратору")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            await message.answer("Использование: /add USER_ID\nПример: /add 123456789")
            return
        
        user_id = int(parts[1])
        whitelist.add(user_id)
        save_whitelist(whitelist)
        await message.answer(f"✅ Пользователь {user_id} добавлен в whitelist")
    except ValueError:
        await message.answer("❌ Неверный формат ID пользователя")

@dp.message(Command("remove"))
async def cmd_remove_user(message: types.Message):
    """Удалить пользователя из whitelist (только админ)"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Эта команда доступна только администратору")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            await message.answer("Использование: /remove USER_ID\nПример: /remove 123456789")
            return
        
        user_id = int(parts[1])
        if user_id == ADMIN_ID:
            await message.answer("❌ Нельзя удалить администратора")
            return
        
        if user_id in whitelist:
            whitelist.remove(user_id)
            save_whitelist(whitelist)
            await message.answer(f"✅ Пользователь {user_id} удалён из whitelist")
        else:
            await message.answer(f"❌ Пользователь {user_id} не найден в whitelist")
    except ValueError:
        await message.answer("❌ Неверный формат ID пользователя")

@dp.message(Command("list"))
async def cmd_list_users(message: types.Message):
    """Показать список пользователей whitelist (только админ)"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Эта команда доступна только администратору")
        return
    
    if not whitelist:
        await message.answer("📝 Whitelist пуст")
        return
    
    users_list = "\n".join([f"• {uid} {'(Админ)' if uid == ADMIN_ID else ''}" for uid in sorted(whitelist)])
    await message.answer(f"📝 Whitelist ({len(whitelist)} пользователей):\n\n{users_list}")

@dp.message(Command("myid"))
async def cmd_my_id(message: types.Message):
    """Показать свой ID"""
    await message.answer(f"🆔 Ваш ID: {message.from_user.id}")

@dp.message(Command("cancel"))
async def cmd_cancel_workflow(message: types.Message):
    """Отменить текущий запущенный воркфлоу"""
    global is_busy, current_user, current_prompt_id
    
    # Проверка доступа
    if not check_access(message.from_user.id):
        return
    
    # Проверяем есть ли активный воркфлоу
    if not is_busy or current_prompt_id is None:
        await message.answer("ℹ️ Нет активного воркфлоу для отмены")
        return
    
    # Только создатель воркфлоу или админ может отменить
    if message.from_user.id != current_user and not is_admin(message.from_user.id):
        await message.answer("❌ Вы можете отменить только свой воркфлоу")
        return
    
    try:
        async with aiohttp.ClientSession() as session:
            cancel_data = {"delete": [current_prompt_id]}
            async with session.post(f"{COMFY_URL}/queue", json=cancel_data) as resp:
                if resp.status == 200:
                    await message.answer("✅ Воркфлоу отменён")
                    is_busy = False
                    current_user = None
                    current_prompt_id = None
                    cleanup_input_dir()
                else:
                    await message.answer("❌ Не удалось отменить воркфлоу")
    except Exception as e:
        await message.answer(f"❌ Ошибка отмены: {str(e)}")

# ============== СТАРТ ==============
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    global is_busy
    
    if not check_access(message.from_user.id):
        await message.answer(get_text(message.from_user.id, "no_access"))
        return
    
    if is_busy and message.from_user.id != current_user:
        await message.answer(get_text(message.from_user.id, "system_busy"))
        return
    
    await state.clear()
    is_busy = False
    cleanup_input_dir()
    
    await message.answer(
        get_text(message.from_user.id, "start_welcome"),
        reply_markup=get_workflow_keyboard(message.from_user.id)
    )
    await state.set_state(GenerationStates.choosing_workflow)

# ============== ВЫБОР ВОРКФЛОУ ==============
@dp.message(GenerationStates.choosing_workflow, F.text)
async def choose_workflow(message: types.Message, state: FSMContext):
    if not check_access(message.from_user.id):
        return
    
    text = message.text
    
    # Проверка на настройки
    if text == get_text(message.from_user.id, "settings"):
        lang_name = "English" if get_user_language(message.from_user.id) == "en" else "Русский"
        denoise = get_user_denoise(message.from_user.id)
        await message.answer(
            get_text(message.from_user.id, "settings_menu", lang_name, denoise),
            reply_markup=get_settings_keyboard(message.from_user.id)
        )
        await state.set_state(SettingsStates.main_menu)
        return
    
    if "i2v" in text.lower():
        workflow_type = "i2v"
        media_type = "photo"
    elif "v2v" in text.lower():
        workflow_type = "v2v"
        media_type = "video"
    else:
        await message.answer(get_text(message.from_user.id, "choose_from_menu"))
        return
    
    await state.update_data(workflow_type=workflow_type, media_type=media_type)
    await message.answer(get_text(message.from_user.id, "choose_resolution"), reply_markup=get_resolution_keyboard())
    await state.set_state(GenerationStates.choosing_resolution)

# ============== МЕНЮ НАСТРОЕК ==============
@dp.message(SettingsStates.main_menu, F.text)
async def settings_menu_handler(message: types.Message, state: FSMContext):
    if not check_access(message.from_user.id):
        return
    
    text = message.text
    user_id = message.from_user.id
    
    # Проверка на смену языка (флаги могут прийти в любом состоянии настроек)
    if text in ["🇬🇧 English", "🇷🇺 Русский"]:
        if text == "🇬🇧 English":
            set_user_setting(user_id, "language", "en")
        else:
            set_user_setting(user_id, "language", "ru")
        
        lang_name = "English" if get_user_language(user_id) == "en" else "Русский"
        denoise = get_user_denoise(user_id)
        
        await message.answer(get_text(user_id, "language_changed"))
        await message.answer(
            get_text(user_id, "settings_menu", lang_name, denoise),
            reply_markup=get_settings_keyboard(user_id)
        )
        return
    
    if text == get_text(user_id, "back"):
        await message.answer(
            get_text(user_id, "start_welcome"),
            reply_markup=get_workflow_keyboard(user_id)
        )
        await state.set_state(GenerationStates.choosing_workflow)
        return
    
    if text == get_text(user_id, "change_language"):
        await message.answer(
            get_text(user_id, "choose_language"),
            reply_markup=get_language_keyboard()
        )
        return
    
    if text == get_text(user_id, "change_denoise"):
        denoise = get_user_denoise(user_id)
        await message.answer(
            get_text(user_id, "denoise_current", denoise),
            reply_markup=get_cancel_keyboard(user_id)
        )
        await state.set_state(SettingsStates.changing_denoise)
        return

@dp.message(SettingsStates.changing_denoise, F.text)
async def change_denoise_handler(message: types.Message, state: FSMContext):
    if not check_access(message.from_user.id):
        return
    
    user_id = message.from_user.id
    
    if message.text == get_text(user_id, "cancel"):
        lang_name = "English" if get_user_language(user_id) == "en" else "Русский"
        denoise = get_user_denoise(user_id)
        await message.answer(
            get_text(user_id, "settings_menu", lang_name, denoise),
            reply_markup=get_settings_keyboard(user_id)
        )
        await state.set_state(SettingsStates.main_menu)
        return
    
    try:
        value = float(message.text.replace(",", "."))
        if 0.10 <= value <= 1.00:
            set_user_setting(user_id, "denoise_strength", value)
            await message.answer(get_text(user_id, "denoise_updated", value))
            
            lang_name = "English" if get_user_language(user_id) == "en" else "Русский"
            await message.answer(
                get_text(user_id, "settings_menu", lang_name, value),
                reply_markup=get_settings_keyboard(user_id)
            )
            await state.set_state(SettingsStates.main_menu)
        else:
            await message.answer(get_text(user_id, "denoise_invalid"))
    except ValueError:
        await message.answer(get_text(user_id, "denoise_invalid"))

# ============== ВЫБОР РАЗРЕШЕНИЯ ==============
@dp.message(GenerationStates.choosing_resolution, F.text)
async def choose_resolution(message: types.Message, state: FSMContext):
    if not check_access(message.from_user.id):
        return
    
    resolution = message.text
    if resolution not in RESOLUTIONS:
        await message.answer(get_text(message.from_user.id, "choose_from_options"))
        return
    
    width, height = RESOLUTIONS[resolution]
    await state.update_data(width=width, height=height)
    
    data = await state.get_data()
    media_prompt = get_text(message.from_user.id, "send_photo") if data["media_type"] == "photo" else get_text(message.from_user.id, "send_video")
    
    await message.answer(media_prompt, reply_markup=get_cancel_keyboard(message.from_user.id))
    await state.set_state(GenerationStates.waiting_media)

# ============== ОТМЕНА ==============
# Cancel handler removed - handled in individual state handlers instead

# ============== ПОЛУЧЕНИЕ ФОТО ==============
@dp.message(GenerationStates.waiting_media, F.photo)
async def handle_photo(message: types.Message, state: FSMContext):
    global is_busy, current_user
    
    if not check_access(message.from_user.id):
        return
    
    if is_busy:
        await message.answer(get_text(message.from_user.id, "system_busy"))
        return
    
    data = await state.get_data()
    if data.get("media_type") != "photo":
        await message.answer(get_text(message.from_user.id, "expected_photo"))
        return
    
    is_busy = True
    current_user = message.from_user.id
    
    photo = message.photo[-1]
    
    # Скачиваем фото через Local Bot API
    try:
        file_info = await bot.get_file(photo.file_id)
        photo_filename = f"input_{uuid.uuid4().hex}.jpg"
        photo_path = os.path.join(INPUT_DIR, photo_filename)
        
        # Если Local Bot API - копируем напрямую
        if TELEGRAM_API_SERVER != "https://api.telegram.org":
            import shutil
            shutil.copy2(file_info.file_path, photo_path)
            print(f"[PHOTO] Copied from local API: {file_info.file_path} -> {photo_path}")
        else:
            await bot.download_file(file_info.file_path, photo_path)
        
        await state.update_data(media_filename=photo_filename)
        await message.answer(get_text(message.from_user.id, "photo_received"), reply_markup=get_cancel_keyboard(message.from_user.id))
        await state.set_state(GenerationStates.waiting_audio)
        
    except Exception as e:
        await message.answer(f"❌ Error downloading photo: {str(e)}\n\nTry again or use /start")
        is_busy = False
        current_user = None

# ============== ПОЛУЧЕНИЕ ВИДЕО ==============
@dp.message(GenerationStates.waiting_media, F.video)
async def handle_video(message: types.Message, state: FSMContext):
    global is_busy, current_user
    
    if not check_access(message.from_user.id):
        return
    
    if is_busy:
        await message.answer(get_text(message.from_user.id, "system_busy"))
        return
    
    data = await state.get_data()
    if data.get("media_type") != "video":
        await message.answer(get_text(message.from_user.id, "expected_video"))
        return
    
    is_busy = True
    current_user = message.from_user.id
    
    video = message.video
    
    # Скачиваем файл через Local Bot API
    try:
        await message.answer(f"📥 Downloading video ({video.file_size / (1024*1024):.1f} MB)...")
        
        file_info = await bot.get_file(video.file_id)
        video_filename = f"input_{uuid.uuid4().hex}.mp4"
        video_path = os.path.join(INPUT_DIR, video_filename)
        
        # Если Local Bot API - file_path это абсолютный путь к файлу
        if TELEGRAM_API_SERVER != "https://api.telegram.org":
            # Копируем файл напрямую
            import shutil
            shutil.copy2(file_info.file_path, video_path)
            print(f"[VIDEO] Copied from local API: {file_info.file_path} -> {video_path}")
        else:
            # Скачиваем через HTTP
            await bot.download_file(file_info.file_path, video_path)
        
        await state.update_data(media_filename=video_filename)
        await message.answer(get_text(message.from_user.id, "video_received"), reply_markup=get_cancel_keyboard(message.from_user.id))
        await state.set_state(GenerationStates.waiting_audio)
        
    except Exception as e:
        await message.answer(f"❌ Error downloading video: {str(e)}\n\nTry again or use /start")
        is_busy = False
        current_user = None

# ============== ПОЛУЧЕНИЕ АУДИО ==============
@dp.message(GenerationStates.waiting_audio, F.audio | F.voice)
async def handle_audio(message: types.Message, state: FSMContext):
    if not check_access(message.from_user.id):
        return
    
    if message.audio:
        audio_file = message.audio
        ext = "mp3"
    else:
        audio_file = message.voice
        ext = "ogg"
    
    # Скачиваем аудио через Local Bot API
    try:
        file_info = await bot.get_file(audio_file.file_id)
        audio_filename = f"audio_{uuid.uuid4().hex}.{ext}"
        audio_path = os.path.join(INPUT_DIR, audio_filename)
        
        # Если Local Bot API - копируем напрямую
        if TELEGRAM_API_SERVER != "https://api.telegram.org":
            import shutil
            shutil.copy2(file_info.file_path, audio_path)
            print(f"[AUDIO] Copied from local API: {file_info.file_path} -> {audio_path}")
        else:
            await bot.download_file(file_info.file_path, audio_path)
        
        await state.update_data(audio_filename=audio_filename)
        await message.answer(
            get_text(message.from_user.id, "audio_received"),
            reply_markup=get_cancel_keyboard(message.from_user.id)
        )
        
        print(f"[AUDIO] About to set state to waiting_prompt...")
        await state.set_state(GenerationStates.waiting_prompt)
        
        # Проверяем что состояние действительно установилось
        current_state = await state.get_state()
        print(f"[AUDIO] State after setting: {current_state}")
        print(f"[AUDIO] Expected: {GenerationStates.waiting_prompt}")
        print(f"[AUDIO] Match: {current_state == GenerationStates.waiting_prompt}")
        
    except Exception as e:
        await message.answer(f"❌ Error downloading audio: {str(e)}\n\nTry again or use /start")

# ============== ПОЛУЧЕНИЕ ПРОМПТА ==============
@dp.message(GenerationStates.waiting_prompt, F.text)
async def handle_prompt(message: types.Message, state: FSMContext):
    print("="*60)
    print("[PROMPT] HANDLER CALLED!!!")
    print(f"[PROMPT] Text: '{message.text}'")
    print(f"[PROMPT] User: {message.from_user.id}")
    print("="*60)
    
    if not check_access(message.from_user.id):
        print("[PROMPT] Access denied!")
        return
    
    print("[PROMPT] Access OK")
    
    if message.text in [get_text(message.from_user.id, "cancel"), "❌ Отменить", "❌ Cancel"]:
        print("[PROMPT] Cancel detected, returning")
        return
    
    print("[PROMPT] Not a cancel, proceeding...")
    
    prompt = message.text
    await state.update_data(prompt=prompt)
    print(f"[PROMPT] State updated with prompt: {prompt}")
    
    await message.answer(get_text(message.from_user.id, "starting_generation"), reply_markup=ReplyKeyboardRemove())
    print("[PROMPT] Sent 'starting generation' message")
    
    data = await state.get_data()
    print(f"[PROMPT] Got state data: {data}")
    
    print("[PROMPT] Calling run_comfyui...")
    await run_comfyui(message, state, data)
    print("[PROMPT] run_comfyui finished")

# ============== ОБРАБОТКА ==============
async def run_comfyui(message: types.Message, state: FSMContext, data: dict):
    global is_busy, current_user, current_prompt_id
    user_id = message.from_user.id
    
    print(f"[COMFY] Starting render for user {user_id}")
    print(f"[COMFY] Data: {data}")
    
    try:
        workflow = load_workflow(data["workflow_type"])
        print(f"[COMFY] Loaded workflow: {data['workflow_type']}")
        
        # Получаем denoise_strength пользователя
        denoise_strength = get_user_denoise(user_id)
        print(f"[COMFY] Denoise strength: {denoise_strength}")
        
        # Модифицируем воркфлоу в зависимости от типа
        if data["workflow_type"] == "i2v":
            # i2v воркфлоу
            workflow["284"]["inputs"]["image"] = data["media_filename"]
            workflow["125"]["inputs"]["audio"] = data["audio_filename"]
            workflow["245"]["inputs"]["value"] = data["width"]
            workflow["246"]["inputs"]["value"] = data["height"]
            workflow["312"]["inputs"]["text"] = data["prompt"]
            print(f"[COMFY] Configured i2v workflow")
        else:
            # v2v воркфлоу (wanvideo_InfiniteTalk_videoToVideo.json)
            # Node 228: VHS_LoadVideo - входное видео
            if "228" in workflow:
                workflow["228"]["inputs"]["video"] = data["media_filename"]
                print(f"[COMFY] Set video: {data['media_filename']}")
            
            # Node 125: LoadAudio - входное аудио  
            if "125" in workflow:
                workflow["125"]["inputs"]["audio"] = data["audio_filename"]
                print(f"[COMFY] Set audio: {data['audio_filename']}")
            
            # Node 245: Width (INTConstant)
            if "245" in workflow:
                workflow["245"]["inputs"]["value"] = data["width"]
                print(f"[COMFY] Set width: {data['width']}")
            
            # Node 246: Height (INTConstant)
            if "246" in workflow:
                workflow["246"]["inputs"]["value"] = data["height"]
                print(f"[COMFY] Set height: {data['height']}")
            
            # Node 241: WanVideoTextEncodeCached - промпт
            if "241" in workflow:
                workflow["241"]["inputs"]["positive_prompt"] = data["prompt"]
                print(f"[COMFY] Set prompt: {data['prompt']}")
            
            # Node 128: WanVideoSampler - denoise_strength
            if "128" in workflow:
                workflow["128"]["inputs"]["denoise_strength"] = denoise_strength
                print(f"[COMFY] Set denoise: {denoise_strength}")
        
        client_id = str(uuid.uuid4())
        prompt_data = {"prompt": workflow, "client_id": client_id}
        
        print(f"[COMFY] Sending to ComfyUI at {COMFY_URL}/prompt")
        
        async with aiohttp.ClientSession() as session:
            # Отправляем в ComfyUI
            async with session.post(f"{COMFY_URL}/prompt", json=prompt_data) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    print(f"[COMFY] ERROR: Status {resp.status}, Response: {error_text}")
                    raise Exception(f"ComfyUI error: {error_text}")
                result = await resp.json()
                prompt_id = result["prompt_id"]
                
                print(f"[COMFY] Got prompt_id: {prompt_id}")
                
                # Сохраняем prompt_id для возможности отмены
                current_prompt_id = prompt_id
            
            await message.answer(get_text(user_id, "processing"))
            print(f"[COMFY] Waiting for completion...")
            
            # Ждём результат
            output_files = await wait_for_completion(session, prompt_id)
            if not output_files:
                raise Exception("Не удалось получить файлы")
            
            print(f"[COMFY] Got output files: {output_files}")
            
            # Находим видео
            video_file = None
            preferred_exts = ('.mp4', '.avi', '.mov', '.webm')
            safe_candidates = []
            ext_candidates = []
            for filename in output_files:
                lower_name = filename.lower()
                if lower_name.endswith(preferred_exts):
                    ext_candidates.append(filename)
                    if "-audio" not in lower_name and "audio" not in lower_name:
                        safe_candidates.append(filename)

            if safe_candidates:
                video_file = safe_candidates[0]
            elif ext_candidates:
                video_file = ext_candidates[0]
            else:
                video_file = output_files[0]
            
            if not video_file:
                raise Exception("Видео не найдено")
            
            video_path = os.path.join(OUTPUT_DIR, video_file)
            
            if not os.path.exists(video_path):
                raise Exception(get_text(user_id, "file_not_found"))
            
            # Проверяем размер файла
            file_size = os.path.getsize(video_path)
            
            # Telegram Bot API принимает файлы только до 50MB для отправки
            if file_size <= 50 * 1024 * 1024:
                # Отправляем напрямую через Telegram
                await bot.send_video(
                    message.chat.id,
                    video=types.FSInputFile(video_path),
                    caption=get_text(user_id, "done") + f"{data['prompt']}\n{data['width']}x{data['height']}"
                )
            else:
                # Файл слишком большой - даем ссылку на скачивание
                download_url = f"http://{EXTERNAL_IP}:{VAST_EXTERNAL_PORT}/download/{video_file}"
                await message.answer(
                    get_text(user_id, "video_ready_download", file_size / (1024*1024), download_url)
                )
        
        await message.answer(get_text(user_id, "completed"))
    
    except Exception as e:
        await message.answer(get_text(user_id, "error", str(e)))
    
    finally:
        cleanup_input_dir()
        is_busy = False
        current_user = None
        current_prompt_id = None
        await state.clear()

# ============== ОЖИДАНИЕ ==============
async def wait_for_completion(session, prompt_id, max_wait=7200):
    waited = 0
    while waited < max_wait:
        await asyncio.sleep(5)
        waited += 5
        
        async with session.get(f"{COMFY_URL}/history/{prompt_id}") as resp:
            if resp.status != 200:
                continue
            
            history = await resp.json()
            if prompt_id in history:
                prompt_history = history[prompt_id]
                if "outputs" in prompt_history:
                    outputs = prompt_history["outputs"]
                    files = []
                    for node_id, node_output in outputs.items():
                        # ComfyUI может класть видео как в "videos"/"gifs", так и в "images"
                        if "gifs" in node_output:
                            files.extend([item["filename"] for item in node_output["gifs"]])
                        if "videos" in node_output:
                            files.extend([item["filename"] for item in node_output["videos"]])
                        if "images" in node_output:
                            files.extend([item["filename"] for item in node_output["images"]])
                    if files:
                        return files
    return None

# ============== ЗАПУСК ==============
async def main():
    print("🤖 Бот запущен!")
    print(f"👤 Админ ID: {ADMIN_ID}")
    print(f"📝 Whitelist: {len(whitelist)} пользователей")
    print(f"🌐 ComfyUI: {COMFY_URL}")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())