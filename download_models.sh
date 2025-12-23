#!/bin/bash

# Базовая директория моделей
BASE="/workspace/ComfyUI/models"

# Удобная функция
get() {
    local url="$1"
    local folder="$2"
    local file=$(basename "$url")

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
