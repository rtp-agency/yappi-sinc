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
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, FSInputFile
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

# ============== КОНФИГУРАЦИЯ ==============
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
COMFY_URL = os.getenv("COMFY_URL", "http://127.0.0.1:18188")
INPUT_DIR = os.getenv("INPUT_DIR", "/workspace/ComfyUI/input")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "/workspace/ComfyUI/output")

# Создаём директории
os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Whitelist файл
WHITELIST_FILE = "whitelist.txt"

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

# ============== РАЗРЕШЕНИЯ ==============
RESOLUTIONS = {
    "640x640": (640, 640),
    "720x1280": (720, 1280),
    "1280x720": (1280, 720),
    "512x512": (512, 512),
    "768x768": (768, 768),
}

# ============== ИНИЦИАЛИЗАЦИЯ ==============
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())
is_busy = False
current_user = None
current_prompt_id = None  # Для отмены воркфлоу

# ============== КЛАВИАТУРЫ ==============
def get_workflow_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📸 Фото в видео (i2v)")],
            [KeyboardButton(text="🎬 Видео в видео (v2v)")]
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

def get_cancel_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отменить")]],
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
        # Отправляем запрос на отмену в ComfyUI
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{COMFY_URL}/interrupt") as resp:
                if resp.status == 200:
                    await message.answer(
                        "🛑 Воркфлоу остановлен!\n\n"
                        "Система освобождена, можете начать новую генерацию."
                    )
                    
                    # Очищаем состояние
                    cleanup_input_dir()
                    is_busy = False
                    current_user = None
                    current_prompt_id = None
                else:
                    await message.answer("⚠️ Не удалось остановить воркфлоу")
    except Exception as e:
        await message.answer(f"❌ Ошибка при остановке: {str(e)}")
        # На всякий случай освобождаем систему
        is_busy = False
        current_user = None
        current_prompt_id = None

# ============== /start ==============
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    global is_busy, current_user
    
    # Проверка доступа
    if not check_access(message.from_user.id):
        await message.answer(
            "❌ У вас нет доступа к этому боту.\n\n"
            f"Ваш ID: {message.from_user.id}\n"
            "Отправьте этот ID администратору для получения доступа."
        )
        return
    
    if is_busy:
        await message.answer(
            f"⏳ Система занята обработкой запроса пользователя {current_user}.\n"
            "Пожалуйста, подождите..."
        )
        return
    
    await state.clear()
    await message.answer(
        "👋 Привет! Выберите тип воркфлоу:",
        reply_markup=get_workflow_keyboard()
    )
    await state.set_state(GenerationStates.choosing_workflow)

# ============== ОТМЕНА ==============
@dp.message(F.text == "❌ Отменить")
async def cancel_handler(message: types.Message, state: FSMContext):
    global is_busy, current_user
    
    if not check_access(message.from_user.id):
        return
    
    current_state = await state.get_state()
    if current_state is None:
        return
    
    is_busy = False
    current_user = None
    cleanup_input_dir()
    
    await state.clear()
    await message.answer("❌ Операция отменена. /start для начала", reply_markup=ReplyKeyboardRemove())

# ============== ВЫБОР ВОРКФЛОУ ==============
@dp.message(GenerationStates.choosing_workflow)
async def choose_workflow(message: types.Message, state: FSMContext):
    if not check_access(message.from_user.id):
        return
    
    text = message.text
    if text == "📸 Фото в видео (i2v)":
        workflow_type = "i2v"
        media_type = "photo"
    elif text == "🎬 Видео в видео (v2v)":
        workflow_type = "v2v"
        media_type = "video"
    else:
        await message.answer("Выберите воркфлоу из меню:", reply_markup=get_workflow_keyboard())
        return
    
    await state.update_data(workflow_type=workflow_type, media_type=media_type)
    await message.answer("📐 Выберите разрешение:", reply_markup=get_resolution_keyboard())
    await state.set_state(GenerationStates.choosing_resolution)

# ============== ВЫБОР РАЗРЕШЕНИЯ ==============
@dp.message(GenerationStates.choosing_resolution)
async def choose_resolution(message: types.Message, state: FSMContext):
    if not check_access(message.from_user.id):
        return
    
    resolution_text = message.text
    if resolution_text not in RESOLUTIONS:
        await message.answer("Выберите разрешение из меню:", reply_markup=get_resolution_keyboard())
        return
    
    width, height = RESOLUTIONS[resolution_text]
    await state.update_data(width=width, height=height)
    
    data = await state.get_data()
    media_type = data["media_type"]
    
    prompt_text = "📸 Отправьте фото" if media_type == "photo" else "🎬 Отправьте видео"
    await message.answer(f"{prompt_text}\n\nРазрешение: {width}x{height}", reply_markup=get_cancel_keyboard())
    await state.set_state(GenerationStates.waiting_media)

# ============== ПОЛУЧЕНИЕ ФОТО ==============
@dp.message(GenerationStates.waiting_media, F.photo)
async def handle_photo(message: types.Message, state: FSMContext):
    global is_busy, current_user
    
    if not check_access(message.from_user.id):
        return
    
    if is_busy:
        await message.answer("⏳ Система занята")
        return
    
    data = await state.get_data()
    if data.get("media_type") != "photo":
        await message.answer("Ожидается фото")
        return
    
    is_busy = True
    current_user = message.from_user.id
    
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    media_filename = f"input_{uuid.uuid4().hex}.jpg"
    media_path = os.path.join(INPUT_DIR, media_filename)
    await bot.download_file(file.file_path, media_path)
    
    await state.update_data(media_filename=media_filename)
    await message.answer("✅ Фото получено!\n\n🎵 Отправьте аудио", reply_markup=get_cancel_keyboard())
    await state.set_state(GenerationStates.waiting_audio)

# ============== ПОЛУЧЕНИЕ ВИДЕО ==============
@dp.message(GenerationStates.waiting_media, F.video)
async def handle_video(message: types.Message, state: FSMContext):
    global is_busy, current_user
    
    if not check_access(message.from_user.id):
        return
    
    if is_busy:
        await message.answer("⏳ Система занята")
        return
    
    data = await state.get_data()
    if data.get("media_type") != "video":
        await message.answer("Ожидается видео")
        return
    
    is_busy = True
    current_user = message.from_user.id
    
    video = message.video
    file = await bot.get_file(video.file_id)
    video_filename = f"input_{uuid.uuid4().hex}.mp4"
    video_path = os.path.join(INPUT_DIR, video_filename)
    await bot.download_file(file.file_path, video_path)
    
    await state.update_data(media_filename=video_filename)
    await message.answer("✅ Видео получено!\n\n🎵 Отправьте аудио", reply_markup=get_cancel_keyboard())
    await state.set_state(GenerationStates.waiting_audio)

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
    
    file = await bot.get_file(audio_file.file_id)
    audio_filename = f"audio_{uuid.uuid4().hex}.{ext}"
    audio_path = os.path.join(INPUT_DIR, audio_filename)
    await bot.download_file(file.file_path, audio_path)
    
    await state.update_data(audio_filename=audio_filename)
    await message.answer(
        "✅ Аудио получено!\n\n✍️ Отправьте промпт\n(Например: 'a man talking')",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(GenerationStates.waiting_prompt)

# ============== ПОЛУЧЕНИЕ ПРОМПТА ==============
@dp.message(GenerationStates.waiting_prompt, F.text)
async def handle_prompt(message: types.Message, state: FSMContext):
    if not check_access(message.from_user.id):
        return
    
    if message.text == "❌ Отменить":
        return
    
    prompt = message.text
    await state.update_data(prompt=prompt)
    await message.answer("🚀 Запускаю генерацию...", reply_markup=ReplyKeyboardRemove())
    
    data = await state.get_data()
    await run_comfyui(message, state, data)

# ============== ОБРАБОТКА ==============
async def run_comfyui(message: types.Message, state: FSMContext, data: dict):
    global is_busy, current_user, current_prompt_id
    
    try:
        workflow = load_workflow(data["workflow_type"])
        
        # Модифицируем воркфлоу в зависимости от типа
        if data["workflow_type"] == "i2v":
            # i2v воркфлоу
            workflow["284"]["inputs"]["image"] = data["media_filename"]
            workflow["125"]["inputs"]["audio"] = data["audio_filename"]
            workflow["245"]["inputs"]["value"] = data["width"]
            workflow["246"]["inputs"]["value"] = data["height"]
            workflow["312"]["inputs"]["text"] = data["prompt"]
        else:
            # v2v воркфлоу (wanvideo_InfiniteTalk_videoToVideo.json)
            # Node 228: VHS_LoadVideo - входное видео
            if "228" in workflow:
                workflow["228"]["inputs"]["video"] = data["media_filename"]
            
            # Node 125: LoadAudio - входное аудио  
            if "125" in workflow:
                workflow["125"]["inputs"]["audio"] = data["audio_filename"]
            
            # Node 245: Width (INTConstant)
            if "245" in workflow:
                workflow["245"]["inputs"]["value"] = data["width"]
            
            # Node 246: Height (INTConstant)
            if "246" in workflow:
                workflow["246"]["inputs"]["value"] = data["height"]
            
            # Node 241: WanVideoTextEncodeCached - промпт
            if "241" in workflow:
                workflow["241"]["inputs"]["positive_prompt"] = data["prompt"]
        
        client_id = str(uuid.uuid4())
        prompt_data = {"prompt": workflow, "client_id": client_id}
        
        async with aiohttp.ClientSession() as session:
            # Отправляем в ComfyUI
            async with session.post(f"{COMFY_URL}/prompt", json=prompt_data) as resp:
                if resp.status != 200:
                    raise Exception(f"ComfyUI error: {await resp.text()}")
                result = await resp.json()
                prompt_id = result["prompt_id"]
                
                # Сохраняем prompt_id для возможности отмены
                current_prompt_id = prompt_id
            
            await message.answer("⏳ Обработка...\n\nДля отмены используйте /cancel")
            
            # Ждём результат
            output_files = await wait_for_completion(session, prompt_id)
            if not output_files:
                raise Exception("Не удалось получить файлы")
            
            # Находим видео
            video_file = None
            # Сначала ищем по "классическим" видео-расширениям,
            # при этом стараемся избежать файлов с суффиксом "-audio"
            # (например, WanVideo2_1_InfiniteTalk_00005-audio.mp4).
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
                # Фолбэк: берём первый файл из списка, даже если расширение неизвестно,
                # чтобы не терять результат.
                video_file = output_files[0]
            
            if not video_file:
                raise Exception("Видео не найдено")
            
            video_path = os.path.join(OUTPUT_DIR, video_file)
            
            # Отправляем результат
            if os.path.exists(video_path):
                video_input = FSInputFile(video_path)
                await message.answer_video(
                    video_input,
                    caption=f"✅ Готово!\n\n{data['prompt']}\n{data['width']}x{data['height']}"
                )
            else:
                await message.answer("❌ Файл не найден")
        
        await message.answer("✨ Завершено! /start для нового")
    
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}\n\n/start для повтора")
    
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