#!/bin/bash
# 1. Устанавливаем абсолютный путь к папке проекта
PROJECT_DIR="/workspace/yappi-sinc"
cd "$PROJECT_DIR" || { echo "Ошибка: папка $PROJECT_DIR не найдена"; exit 1; }

# Сначала чиним путь к ComfyUI (КРИТИЧНО для Vast.ai)
if [ ! -f "/workspace/ComfyUI/main.py" ]; then
    echo "[Fix] ComfyUI missing in workspace. Linking..."
    rm -rf /workspace/ComfyUI
    ln -s /opt/workspace-internal/ComfyUI /workspace/ComfyUI
fi

# 2. Создание виртуального окружения прямо в папке проекта
VENV_DIR="$PROJECT_DIR/venv"

if [ ! -d "$VENV_DIR" ]; then
    echo ">>> Creating virtual environment in $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
fi

# 3. Активация и установка зависимостей
echo ">>> Activating virtual environment..."
source "$VENV_DIR/bin/activate"

if [ -f "requirements.txt" ]; then
    echo ">>> Installing dependencies from $PROJECT_DIR/requirements.txt..."
    pip install --upgrade pip
    pip install --no-cache-dir -r requirements.txt
    deactivate
else
    echo ">>> requirements.txt not found in $PROJECT_DIR, skipping."
fi

echo ">>> Dependencies installed successfully. Venv deactivated"

# -------------------------
# Базовая директория моделей
# -------------------------
BASE="/workspace/ComfyUI/models"

get() {
    local url="$1"
    local folder="$2"
    local file
    file=$(basename "$url")

    echo ">>> Downloading: $file"
    wget -nc --show-progress "$url" -O "$folder/$file"
}

echo "==========================================="
echo " DOWNLOADING COMFYUI MODELS"
echo "==========================================="

# -------------------------
# Diffusion models
# -------------------------
echo ">>> Diffusion models..."

get "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Wan2_1-I2V-14B-720P_fp8_e4m3fn.safetensors" \
    "$BASE/diffusion_models"

get "https://huggingface.co/Kijai/MelBandRoFormer_comfy/resolve/main/MelBandRoformer_fp16.safetensors" \
    "$BASE/diffusion_models"

get "https://huggingface.co/Kijai/MelBandRoFormer_comfy/resolve/main/MelBandRoformer_fp32.safetensors" \
    "$BASE/diffusion_models"

get "https://huggingface.co/Kijai/WanVideo_comfy_fp8_scaled/resolve/main/InfiniteTalk/Wan2_1-InfiniteTalk-Single_fp8_e4m3fn_scaled_KJ.safetensors" \
    "$BASE/diffusion_models"

get "https://huggingface.co/Kijai/WanVideo_comfy_fp8_scaled/resolve/0d3d8b15f8f83281e3308e7c9a562d49e30fb2d1/I2V/Wan2_1-I2V-14B-480p_fp8_e5m2_scaled_KJ.safetensors" \
    "$BASE/diffusion_models"

# -------------------------
# VAE 
# -------------------------
echo ">>> VAE models..."

get "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Wan2_1_VAE_bf16.safetensors" \
    "$BASE/vae"

get "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors" \
    "$BASE/vae"

# -------------------------
# Lora models
# -------------------------
echo ">>> Loras..."

get "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Lightx2v/lightx2v_I2V_14B_480p_cfg_step_distill_rank64_bf16.safetensors" \
    "$BASE/loras"

get "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Lightx2v/lightx2v_I2V_14B_480p_cfg_step_distill_rank256_bf16.safetensors" \
    "$BASE/loras"

# -------------------------
# Text encoders
# -------------------------
echo ">>> Text encoders..."

get "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/umt5-xxl-enc-bf16.safetensors" \
    "$BASE/text_encoders"

get "https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/umt5-xxl-enc-fp8_e4m3fn.safetensors" \
    "$BASE/text_encoders"

get "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors" \
    "$BASE/text_encoders"

# -------------------------
# CLIP vision
# -------------------------
echo ">>> CLIP Vision..."

get "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/clip_vision/clip_vision_h.safetensors" \
    "$BASE/clip_vision"

echo ">>> DONE!"

# Настройка путей
COMFY_NODES_DIR="/workspace/ComfyUI/custom_nodes"
mkdir -p "$COMFY_NODES_DIR"
cd "$COMFY_NODES_DIR"

echo "==============================================="
echo "STARTING CUSTOM NODES INSTALLATION TEST"
echo "==============================================="

# Список репозиториев
REPOS=(
    "https://github.com/Kijai/ComfyUI-WanVideoWrapper.git"
    "https://github.com/Kijai/ComfyUI-KJNodes.git"
    "https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git"
    "https://github.com/Kijai/ComfyUI-MelBandRoFormer.git"
    "https://github.com/ltdrdata/ComfyUI-Manager.git"
)

# 1. Клонирование репозиториев
for repo in "${REPOS[@]}"; do
    folder=$(basename "$repo" .git)
    if [ ! -d "$folder" ]; then
        echo ">>> Cloning $folder..."
        git clone "$repo"
    else
        echo ">>> $folder already exists, pulling updates..."
        cd "$folder" && git pull && cd ..
    fi
done

echo "-----------------------------------------------"
echo "INSTALLING DEPENDENCIES"
echo "-----------------------------------------------"

# Обновляем pip перед установкой
pip install --upgrade pip setuptools wheel

# Внутри download_models.sh вместо обычного pip install:
MAIN_PIP="/venv/main/bin/pip"
for folder in /workspace/ComfyUI/custom_nodes/*; do
    if [ -f "$folder/requirements.txt" ]; then
        $MAIN_PIP install --no-cache-dir -r "$folder/requirements.txt" --no-build-isolation
        if [ $? -eq 0 ]; then
            echo " [OK] $folder dependencies installed."
        else
            echo " [ERROR] Failed to install dependencies for $folder"
        fi
    else
        echo ">>> No requirements.txt in $folder, skipping."
    fi
done

echo "==============================================="
echo "INSTALLATION TEST FINISHED"
echo "Restart ComfyUI now to check for red nodes."
echo "==============================================="

# -------------------------
# TELEGRAM BOT API LOCAL SERVER
# -------------------------
echo "==============================================="
echo " STARTING TELEGRAM BOT API SERVER"
echo "==============================================="

# Убиваем старый процесс если есть
pkill -f telegram-bot-api 2>/dev/null || true

# Проверяем наличие бинарника
if [ ! -f "/workspace/yappi-sinc/telegram-bot-api/build/telegram-bot-api" ]; then
    echo "[ERROR] telegram-bot-api binary not found!"
    echo "[INFO] Please build it first"
    exit 1
fi

chmod +x /workspace/yappi-sinc/telegram-bot-api/build/telegram-bot-api
# Запускаем сервер
echo ">>> Starting Telegram Bot API Server on port 8765..."
cd /workspace/yappi-sinc/telegram-bot-api/build
nohup ./telegram-bot-api --api-id=23284006 --api-hash=fa0e6f9ab220d4edc4f71fd022717baa --local -p 8765 > /workspace/telegram-bot-api.log 2>&1 &

# Ждем запуска
sleep 3

# Проверяем что запустился
if curl -s http://127.0.0.1:8765 > /dev/null 2>&1; then
    echo " [OK] Telegram Bot API Server is running on port 8765"
else
    echo " [ERROR] Failed to start Telegram Bot API Server"
fi

echo "==============================================="
echo " STARTING TELEGRAM BOT"
echo "==============================================="

# 2. Запуск бота из виртуального окружения (текущий сеанс)
echo ">>> Starting Telegram Bot..."
cd /workspace/yappi-sinc
./venv/bin/python3 bot.py > bot.log 2>&1 &

# 3. Модификация системного entrypoint.sh для автозапуска при рестарте инстанса
echo ">>> Patching entrypoint.sh for persistent bot autostart..."
ENTRYPOINT="/opt/instance-tools/bin/entrypoint.sh"

# Создаем временный файл с кодом вставки
cat << 'EOF' > /tmp/bot_start.sh
set -e
if [[ -f /workspace/yappi-sinc/bot.py ]]; then
    echo "[entrypoint] starting telegram bot in background"
    cd /workspace/yappi-sinc
    source venv/bin/activate
    nohup python bot.py > bot.log 2>&1 &
fi
EOF

# Вставляем содержимое после первой строки (shebang)
sed -i '2r /tmp/bot_start.sh' "$ENTRYPOINT"
rm /tmp/bot_start.sh

echo "==============================================="
echo " ALL SYSTEMS READY AND PATCHED"
echo "==============================================="