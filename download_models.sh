#!/bin/bash

# -------------------------
# Создание виртуального окружения
# -------------------------
VENV_DIR="./venv"

if [ ! -d "$VENV_DIR" ]; then
    echo ">>> Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

echo ">>> Activating virtual environment..."
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

# Установка зависимостей корневого проекта ВНУТРИ окружения
if [ -f "requirements.txt" ]; then
    echo ">>> Installing dependencies from requirements.txt inside venv..."
    pip install --upgrade pip
    pip install -r requirements.txt
else
    echo ">>> requirements.txt not found, skipping pip install."
fi

echo ">>> Deactivating virtual environment..."
deactivate

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

# 2. Установка зависимостей для каждой ноды по отдельности
# Мы используем цикл, чтобы видеть, на какой именно ноде возникнет ошибка
for repo in "${REPOS[@]}"; do
    folder=$(basename "$repo" .git)
    if [ -f "$folder/requirements.txt" ]; then
        echo ">>> Installing requirements for: $folder"
        # Используем --user или прямой pip в зависимости от среды Vast
        pip install --no-cache-dir -r "$folder/requirements.txt"
        
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

# Находим ID процесса ComfyUI и убиваем его
PID=$(pgrep -f "python3 main.py")
if [ ! -z "$PID" ]; then
    echo ">>> Остановка ComfyUI (PID: $PID)..."
    kill $PID
    sleep 2
fi

# Запускаем заново в фоновом режиме, как это делает Vast
echo ">>> Запуск ComfyUI..."
cd /workspace/ComfyUI
nohup python3 main.py --listen 0.0.0.0 --port 8188 > comfy.log 2>&1 &
echo ">>> ComfyUI перезапущен!"
