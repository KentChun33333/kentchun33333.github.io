#!/usr/bin/env python3
import os
import sys
import time
from huggingface_hub import hf_hub_download

os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"

TARGET_DIR = "/Users/kentchiu/ComfyUI-Shared/models"
REPO_ID = "Comfy-Org/MiniMax-H3"

FILES_TO_DOWNLOAD = [
    ("loras/minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors", "4-step Turbo LoRA (1.82 GB)"),
    ("vae/minimax_h3_video_vae_fp16.safetensors", "Video VAE FP16 (4.85 GB)"),
    ("diffusion_models/minimax_h3_fl2va_pruned_int8_convrot.safetensors", "FL2VA DiT Diffusion INT8 (19.53 GB)")
]

def main():
    print("=== Starting MiniMax H3 Video Model Downloads with HF_TRANSFER ===", flush=True)
    total_start = time.time()
    
    for filename, desc in FILES_TO_DOWNLOAD:
        full_dest = os.path.join(TARGET_DIR, filename)
        if os.path.exists(full_dest) and os.path.getsize(full_dest) > 1024 * 1024:
            print(f"[SKIP] {filename} already exists ({os.path.getsize(full_dest) / (1024*1024):.1f} MB)", flush=True)
            continue
            
        print(f"\n[DOWNLOADING] {desc} -> {filename}...", flush=True)
        t0 = time.time()
        try:
            path = hf_hub_download(
                repo_id=REPO_ID,
                filename=filename,
                local_dir=TARGET_DIR
            )
            elapsed = time.time() - t0
            size_mb = os.path.getsize(path) / (1024 * 1024)
            speed = size_mb / elapsed if elapsed > 0 else 0
            print(f"[DONE] {filename} downloaded in {elapsed:.1f}s ({speed:.2f} MB/s, total {size_mb:.1f} MB)", flush=True)
        except Exception as e:
            print(f"[ERROR] Failed to download {filename}: {e}", flush=True)
            sys.exit(1)

    total_time = time.time() - total_start
    print(f"\n=== All MiniMax H3 video models successfully downloaded in {total_time/60:.1f} minutes! ===", flush=True)

if __name__ == "__main__":
    main()
