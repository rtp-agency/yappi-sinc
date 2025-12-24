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

# Установка зависимостей корневого проекта
if [ -f "requirements.txt" ]; then
    echo ">>> Installing dependencies from requirements.txt..."
    pip install --upgrade pip
    pip install -r requirements.txt
    deactivate
else
    echo ">>> requirements.txt not found, skipping pip install."
fi

# -------------------------
# Путь к custom_nodes
# -------------------------
CUSTOM="/workspace/ComfyUI/custom_nodes"

mkdir -p "$CUSTOM"

clone_and_install() {
    local repo_url="$1"
    local target_dir="$CUSTOM/$(basename "$repo_url" .git)"

    echo "==========================================="
    echo ">>> Installing custom node: $repo_url"
    echo "==========================================="

    if [ ! -d "$target_dir" ]; then
        git clone "$repo_url" "$target_dir"
    else
        echo ">>> Repo already exists, pulling updates..."
        git -C "$target_dir" pull
    fi

    # Install requirements if exist
    if [ -f "$target_dir/requirements.txt" ]; then
        echo ">>> Installing node dependencies..."
        pip install -r "$target_dir/requirements.txt"
    else
        echo ">>> No requirements.txt found for this node."
    fi
}

# -------------------------
# Установка кастомных нод
# -------------------------

clone_and_install "https://github.com/kijai/ComfyUI-WanVideoWrapper.git"
clone_and_install "https://github.com/kijai/ComfyUI-KJNodes.git"
clone_and_install "https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git"
clone_and_install "https://github.com/kijai/ComfyUI-MelBandRoFormer.git"

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

get "https://huggingface.co/city96/Wan2.1-I2V-14B-480P-gguf/resolve/main/wan2.1-i2v-14b-480p-Q8_0.gguf" \
    "$BASE/diffusion_models"

get "https://huggingface.co/Kijai/WanVideo_comfy_GGUF/resolve/main/InfiniteTalk/Wan2_1-InfiniteTalk_Single_Q8.gguf" \
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
