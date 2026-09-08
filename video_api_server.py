#!/usr/bin/env python3
"""
FastAPI Server for MiniMax H3 Text-to-Video API Workflow
Supports prompt-to-video generation using Qwen3-VL-32B Heretic text encoder + MiniMax H3 DiT + Turbo LoRA.
"""

import os
import json
import random
import urllib.request
import urllib.error
import asyncio
from typing import Optional
from pathlib import Path
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Constants & Paths
COMFYUI_URL = os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188")
SHARED_DIR = Path("/Users/kentchiu/ComfyUI-Shared")
OUTPUT_DIR = SHARED_DIR / "output"
MODELS_DIR = SHARED_DIR / "models"

# Required models
REQUIRED_MODELS = {
    "text_encoder": "text_encoders/H3/qwen3vl_32b_h3_ultra_uncensored_heretic_int8_convrot.safetensors",
    "video_vae": "vae/minimax_h3_video_vae_fp16.safetensors",
    "audio_vae": "vae/minimax_h3_audio_vae_fp32.safetensors",
    "lora": "loras/minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors",
    "diffusion_model": "diffusion_models/minimax_h3_fl2va_pruned_int8_convrot.safetensors",
}

app = FastAPI(
    title="MiniMax H3 Text-to-Video API",
    description="High-performance Text-to-Video API powered by Qwen3-VL-32B Heretic and MiniMax H3",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VideoPromptRequest(BaseModel):
    prompt: str = Field(..., description="Prompt describing the scene, camera movement, and audio")
    width: int = Field(864, description="Video width (multiple of 32, max 1344)")
    height: int = Field(480, description="Video height (multiple of 32, max 768)")
    length: int = Field(124, description="Frame count at 24fps (124 = ~5s, snapped to 17k+5)")
    steps: int = Field(4, description="Sampling steps (4 steps for Turbo LoRA)")
    seed: Optional[int] = Field(None, description="Random seed (defaults to random)")

def check_models_status():
    status = {}
    for key, rel_path in REQUIRED_MODELS.items():
        full_path = MODELS_DIR / rel_path
        exists = full_path.exists()
        size_mb = (full_path.stat().st_size / (1024 * 1024)) if exists else 0
        status[key] = {
            "path": str(rel_path),
            "ready": exists and size_mb > 10,
            "size_mb": round(size_mb, 2)
        }
    return status

def build_workflow_prompt(req: VideoPromptRequest) -> dict:
    seed = req.seed if req.seed is not None else random.randint(1, 1000000000000)
    
    # Snap length to MiniMax H3 17k+5 grid:
    snapped_length = req.length
    while snapped_length % 17 != 5:
        snapped_length += 1

    return {
        "1": {
            "class_type": "UNETLoader",
            "inputs": {
                "unet_name": "minimax_h3_fl2va_pruned_int8_convrot.safetensors",
                "weight_dtype": "default"
            }
        },
        "2": {
            "class_type": "LoraLoaderModelOnly",
            "inputs": {
                "model": ["1", 0],
                "lora_name": "minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors",
                "strength_model": 1.0
            }
        },
        "3": {
            "class_type": "CLIPLoader",
            "inputs": {
                "clip_name": "H3/qwen3vl_32b_h3_ultra_uncensored_heretic_int8_convrot.safetensors",
                "type": "minimax"
            }
        },
        "4": {
            "class_type": "VAELoader",
            "inputs": {
                "vae_name": "minimax_h3_video_vae_fp16.safetensors"
            }
        },
        "5": {
            "class_type": "VAELoader",
            "inputs": {
                "vae_name": "minimax_h3_audio_vae_fp32.safetensors"
            }
        },
        "6": {
            "class_type": "MiniMaxH3ImageToVideo",
            "inputs": {
                "clip": ["3", 0],
                "vae": ["4", 0],
                "prompt": req.prompt,
                "width": int(req.width),
                "height": int(req.height),
                "length": int(snapped_length)
            }
        },
        "7": {
            "class_type": "BasicGuider",
            "inputs": {
                "model": ["2", 0],
                "conditioning": ["6", 0]
            }
        },
        "8": {
            "class_type": "KSamplerSelect",
            "inputs": {
                "sampler_name": "res_multistep"
            }
        },
        "9": {
            "class_type": "BasicScheduler",
            "inputs": {
                "model": ["2", 0],
                "scheduler": "simple",
                "steps": int(req.steps),
                "denoise": 1.0
            }
        },
        "10": {
            "class_type": "RandomNoise",
            "inputs": {
                "noise_seed": int(seed)
            }
        },
        "11": {
            "class_type": "SamplerCustomAdvanced",
            "inputs": {
                "noise": ["10", 0],
                "guider": ["7", 0],
                "sampler": ["8", 0],
                "sigmas": ["9", 0],
                "latent_image": ["6", 1]
            }
        },
        "12": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["11", 0],
                "vae": ["4", 0]
            }
        },
        "13": {
            "class_type": "VAEDecodeAudio",
            "inputs": {
                "samples": ["11", 0],
                "vae": ["5", 0]
            }
        },
        "14": {
            "class_type": "CreateVideo",
            "inputs": {
                "images": ["12", 0],
                "audio": ["13", 0],
                "fps": 24
            }
        },
        "15": {
            "class_type": "SaveVideo",
            "inputs": {
                "video": ["14", 0],
                "filename_prefix": "video/MiniMax_H3",
                "format": "auto",
                "codec": "auto"
            }
        }
    }

@app.get("/api/models")
async def get_models():
    """Return model presence and readiness status."""
    return {
        "status": "ok",
        "models": check_models_status(),
        "all_ready": all(m["ready"] for m in check_models_status().values())
    }

@app.get("/api/queue")
async def get_queue():
    """Return current ComfyUI queue."""
    try:
        req = urllib.request.Request(f"{COMFYUI_URL}/queue")
        with urllib.request.urlopen(req, timeout=5) as res:
            return json.loads(res.read().decode("utf-8"))
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Cannot reach ComfyUI: {e}")

@app.post("/api/prompt-to-video")
async def generate_video(req: VideoPromptRequest):
    """Submit a text-to-video generation job."""
    workflow = build_workflow_prompt(req)
    payload = json.dumps({"prompt": workflow}).encode("utf-8")

    try:
        http_req = urllib.request.Request(
            f"{COMFYUI_URL}/prompt",
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(http_req, timeout=10) as res:
            res_data = json.loads(res.read().decode("utf-8"))
            prompt_id = res_data.get("prompt_id")
            return {
                "status": "queued",
                "prompt_id": prompt_id,
                "number": res_data.get("number"),
                "message": "Generation job enqueued successfully.",
                "poll_url": f"/api/status/{prompt_id}"
            }
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        raise HTTPException(status_code=e.code, detail=f"ComfyUI Error: {err_body}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit to ComfyUI: {e}")

@app.get("/api/status/{prompt_id}")
async def get_status(prompt_id: str):
    """Check status of a prompt job."""
    try:
        # Check history first
        hist_req = urllib.request.Request(f"{COMFYUI_URL}/history/{prompt_id}")
        with urllib.request.urlopen(hist_req, timeout=5) as res:
            history = json.loads(res.read().decode("utf-8"))
            
        if prompt_id in history:
            job_info = history[prompt_id]
            status_info = job_info.get("status", {})
            outputs = job_info.get("outputs", {})
            
            # Check for completed video output
            # ComfyUI records video in 'images' or 'videos'
            video_files = []
            for node_id, node_out in outputs.items():
                for key in ["videos", "gifs", "images"]:
                    for item in node_out.get(key, []):
                        if isinstance(item, dict) and item.get("filename", "").lower().endswith((".mp4", ".webm", ".mov", ".gif")):
                            video_files.append(item)
            
            if video_files:
                v = video_files[0]
                fname = v.get("filename")
                subf = v.get("subfolder", "")
                return {
                    "status": "completed",
                    "prompt_id": prompt_id,
                    "completed": status_info.get("completed", True),
                    "filename": fname,
                    "subfolder": subf,
                    "video_url": f"/api/video/{fname}?subfolder={subf}"
                }
            elif status_info.get("status_str") == "error":
                return {
                    "status": "error",
                    "prompt_id": prompt_id,
                    "messages": status_info.get("messages", [])
                }
            else:
                return {
                    "status": "completed",
                    "prompt_id": prompt_id,
                    "details": "Job completed without video outputs recorded."
                }

        # If not in history, check current queue
        queue_req = urllib.request.Request(f"{COMFYUI_URL}/queue")
        with urllib.request.urlopen(queue_req, timeout=5) as res:
            queue_data = json.loads(res.read().decode("utf-8"))

        running = queue_data.get("queue_running", [])
        pending = queue_data.get("queue_pending", [])

        for item in running:
            if item[1] == prompt_id:
                return {"status": "running", "prompt_id": prompt_id}

        for item in pending:
            if item[1] == prompt_id:
                return {"status": "pending", "prompt_id": prompt_id}

        return {"status": "not_found", "prompt_id": prompt_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch status: {e}")

@app.get("/api/video/{filename}")
async def serve_video(filename: str, subfolder: str = "video"):
    """Serve a generated video MP4 file."""
    if subfolder:
        target_file = OUTPUT_DIR / subfolder / filename
    else:
        target_file = OUTPUT_DIR / filename

    if not target_file.exists():
        # Search anywhere in output dir
        matches = list(OUTPUT_DIR.glob(f"**/{filename}"))
        if matches:
            target_file = matches[0]
        else:
            raise HTTPException(status_code=404, detail="Video file not found")

    return FileResponse(
        path=target_file,
        media_type="video/mp4",
        filename=filename
    )

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    """Serve interactive web dashboard."""
    models_info = check_models_status()
    all_ready = all(m["ready"] for m in models_info.values())
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>MiniMax H3 Text-to-Video Studio</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg: #090a0f;
      --card-bg: rgba(22, 25, 37, 0.85);
      --card-border: rgba(255, 255, 255, 0.08);
      --accent-gradient: linear-gradient(135deg, #6366f1 0%, #ec4899 50%, #f43f5e 100%);
      --accent-glow: rgba(99, 102, 241, 0.35);
      --text-main: #f8fafc;
      --text-sub: #94a3b8;
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: var(--bg);
      color: var(--text-main);
      font-family: 'Outfit', sans-serif;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      background-image: 
        radial-gradient(circle at 15% 15%, rgba(99, 102, 241, 0.15) 0%, transparent 40%),
        radial-gradient(circle at 85% 85%, rgba(236, 72, 153, 0.12) 0%, transparent 40%);
    }}
    header {{
      padding: 1.5rem 2rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 1px solid var(--card-border);
      backdrop-filter: blur(12px);
    }}
    .logo {{
      display: flex;
      align-items: center;
      gap: 0.75rem;
      font-weight: 700;
      font-size: 1.25rem;
      background: var(--accent-gradient);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }}
    .badge {{
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      padding: 0.25rem 0.75rem;
      border-radius: 9999px;
      font-size: 0.75rem;
      font-weight: 500;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--card-border);
    }}
    .badge.ready {{ color: var(--success); border-color: rgba(16, 185, 129, 0.3); }}
    .badge.busy {{ color: var(--warning); border-color: rgba(245, 158, 11, 0.3); }}
    .main-container {{
      max-width: 1280px;
      margin: 2rem auto;
      padding: 0 1.5rem;
      width: 100%;
      display: grid;
      grid-template-columns: 1.1fr 0.9fr;
      gap: 2rem;
      flex: 1;
    }}
    @media (max-width: 960px) {{
      .main-container {{ grid-template-columns: 1fr; }}
    }}
    .panel {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 1.25rem;
      padding: 1.75rem;
      backdrop-filter: blur(16px);
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
    }}
    h2 {{
      font-size: 1.2rem;
      font-weight: 600;
      margin-bottom: 1.25rem;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }}
    label {{
      display: block;
      font-size: 0.85rem;
      font-weight: 500;
      color: var(--text-sub);
      margin-bottom: 0.5rem;
    }}
    textarea, select, input {{
      width: 100%;
      background: rgba(15, 17, 26, 0.7);
      border: 1px solid var(--card-border);
      border-radius: 0.75rem;
      color: var(--text-main);
      padding: 0.85rem 1rem;
      font-family: inherit;
      font-size: 0.95rem;
      transition: all 0.2s;
    }}
    textarea:focus, select:focus, input:focus {{
      outline: none;
      border-color: #6366f1;
      box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2);
    }}
    .grid-2 {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1rem;
      margin-top: 1rem;
    }}
    .btn {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 0.5rem;
      width: 100%;
      padding: 1rem;
      border-radius: 0.85rem;
      font-weight: 600;
      font-size: 1rem;
      cursor: pointer;
      border: none;
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      margin-top: 1.5rem;
    }}
    .btn-primary {{
      background: var(--accent-gradient);
      color: white;
      box-shadow: 0 8px 20px var(--accent-glow);
    }}
    .btn-primary:hover:not(:disabled) {{
      transform: translateY(-2px);
      box-shadow: 0 12px 25px rgba(99, 102, 241, 0.5);
    }}
    .btn-primary:disabled {{
      opacity: 0.6;
      cursor: not-allowed;
      filter: grayscale(0.5);
    }}
    .prompt-presets {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
      margin-top: 0.75rem;
    }}
    .preset-chip {{
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid var(--card-border);
      color: var(--text-sub);
      padding: 0.35rem 0.75rem;
      border-radius: 0.5rem;
      font-size: 0.75rem;
      cursor: pointer;
      transition: all 0.2s;
    }}
    .preset-chip:hover {{
      background: rgba(99, 102, 241, 0.15);
      border-color: #6366f1;
      color: white;
    }}
    .video-preview-wrapper {{
      aspect-ratio: 16/9;
      background: #000;
      border-radius: 1rem;
      overflow: hidden;
      display: flex;
      align-items: center;
      justify-content: center;
      position: relative;
      border: 1px solid var(--card-border);
    }}
    video {{
      width: 100%;
      height: 100%;
      object-fit: cover;
    }}
    .placeholder-state {{
      text-align: center;
      color: var(--text-sub);
      padding: 2rem;
    }}
    .model-status-card {{
      margin-top: 1.5rem;
      padding: 1rem;
      background: rgba(10, 12, 18, 0.6);
      border-radius: 0.75rem;
      border: 1px solid var(--card-border);
      font-size: 0.8rem;
    }}
    .model-row {{
      display: flex;
      justify-content: space-between;
      padding: 0.35rem 0;
      border-bottom: 1px solid rgba(255, 255, 255, 0.03);
    }}
    .model-row:last-child {{ border-bottom: none; }}
    .status-dot {{
      display: inline-block;
      width: 8px;
      height: 8px;
      border-radius: 50%;
      margin-right: 0.4rem;
    }}
    .status-dot.green {{ background: var(--success); box-shadow: 0 0 8px var(--success); }}
    .status-dot.yellow {{ background: var(--warning); box-shadow: 0 0 8px var(--warning); }}
    .pulse {{
      animation: pulse 1.5s infinite;
    }}
    @keyframes pulse {{
      0%, 100% {{ opacity: 1; }}
      50% {{ opacity: 0.4; }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="logo">
      <span>✨ MiniMax H3 Video Studio</span>
    </div>
    <div id="system-badge" class="badge {'ready' if all_ready else 'busy'}">
      <span class="status-dot {'green' if all_ready else 'yellow'}"></span>
      <span>{'All Models Ready' if all_ready else 'Downloading Models...'}</span>
    </div>
  </header>

  <main class="main-container">
    <!-- Left: Controls -->
    <section class="panel">
      <h2>🎬 Video Generation Settings</h2>
      
      <div style="margin-bottom: 1rem;">
        <label for="prompt">Prompt (Visuals + Scene + Audio/Music)</label>
        <textarea id="prompt" rows="5" placeholder="Describe the scene, action, lighting, camera movement, and audio..."></textarea>
        
        <div class="prompt-presets">
          <span class="preset-chip" onclick="applyPreset(0)">Cyberpunk City</span>
          <span class="preset-chip" onclick="applyPreset(1)">Action Rooftop Chase</span>
          <span class="preset-chip" onclick="applyPreset(2)">Vaporwave Aesthetic</span>
          <span class="preset-chip" onclick="applyPreset(3)">Cinematic Nature Drone</span>
        </div>
      </div>

      <div class="grid-2">
        <div>
          <label for="resolution">Resolution</label>
          <select id="resolution">
            <option value="864x480" selected>864 x 480 (Recommended / Fast)</option>
            <option value="960x544">960 x 544 (Balanced)</option>
            <option value="1056x608">1056 x 608 (High Quality)</option>
            <option value="1344x768">1344 x 768 (Native 768p)</option>
          </select>
        </div>
        <div>
          <label for="duration">Duration</label>
          <select id="duration">
            <option value="124" selected>~5.1s (124 frames @ 24fps)</option>
            <option value="175">~7.3s (175 frames @ 24fps)</option>
          </select>
        </div>
      </div>

      <div class="grid-2">
        <div>
          <label for="steps">Sampling Steps</label>
          <input type="number" id="steps" value="4" min="4" max="8">
        </div>
        <div>
          <label for="seed">Seed (-1 for random)</label>
          <input type="number" id="seed" value="-1">
        </div>
      </div>

      <button id="generate-btn" class="btn btn-primary" onclick="startGeneration()">
        🚀 Generate Video with Sound
      </button>

      <!-- Model Status Card -->
      <div class="model-status-card" id="model-status-box">
        <div style="font-weight: 600; margin-bottom: 0.5rem;">Hardware & Model Pipeline Status</div>
        <div id="model-list">Loading model state...</div>
      </div>
    </section>

    <!-- Right: Player & Status -->
    <section class="panel">
      <h2>🎥 Output Preview</h2>
      
      <div class="video-preview-wrapper" id="preview-container">
        <div class="placeholder-state" id="placeholder">
          <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">🎞️</div>
          <div>Your generated video with native stereo soundtrack will play here.</div>
        </div>
        <video id="player" controls style="display: none;"></video>
      </div>

      <div style="margin-top: 1.5rem;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
          <span style="font-size: 0.85rem; color: var(--text-sub);">Status</span>
          <span id="status-text" style="font-size: 0.85rem; font-weight: 600;">Idle</span>
        </div>
        <div id="status-log" style="font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; color: var(--text-sub); background: rgba(0,0,0,0.3); padding: 0.75rem; border-radius: 0.5rem; min-height: 4rem;">
          Ready to generate. Enter prompt and click Generate.
        </div>
      </div>

      <div style="margin-top: 1rem; display: flex; gap: 0.75rem;">
        <a id="download-btn" href="#" download class="btn" style="display: none; background: rgba(255,255,255,0.08); border: 1px solid var(--card-border); color: white; text-decoration: none;">
          📥 Download MP4
        </a>
      </div>
    </section>
  </main>

  <script>
    const PRESETS = [
      "A cinematic drone shot of a futuristic neon-lit metropolis at dusk. Hover cars zoom between shimmering towers with reflective rain-slick surfaces. Dramatic volumetric fog and neon glow. Soundtrack: ambient synthwave music with deep bass pulsations.",
      "Realistic live-action cinematic look, action movie rooftop chase: dusk metropolis, shallow depth of field, anamorphic lens. Protagonist leaps across gaps between skyscrapers. Audio: rushing wind, heavy footsteps, dramatic orchestral trailer crescendo.",
      "Vaporwave aesthetic title sequence: pink and purple pastel sky, retro VHS tracking glitch, Greek marble bust close-up, 80s chrome palm trees. Audio: slow lo-fi hip-hop beat, cassette tape hiss, gentle nostalgic Rhodes piano.",
      "Ultra-realistic 8K drone flight sweeping through a majestic alpine mountain valley at sunrise. Golden sun rays break over snow-capped peaks and mist-covered evergreen pines. Audio: gentle mountain breeze, distant bird calls, inspiring ambient strings."
    ];

    function applyPreset(idx) {{
      document.getElementById('prompt').value = PRESETS[idx];
    }}

    // Initial preset
    applyPreset(0);

    async function checkModelPipeline() {{
      try {{
        const res = await fetch('/api/models');
        const data = await res.json();
        const listEl = document.getElementById('model-list');
        listEl.innerHTML = '';
        
        let allReady = true;
        for (const [k, v] of Object.entries(data.models)) {{
          if (!v.ready) allReady = false;
          const row = document.createElement('div');
          row.className = 'model-row';
          row.innerHTML = `
            <span><span class="status-dot ${{v.ready ? 'green' : 'yellow'}}"></span>${{k}}</span>
            <span style="color: ${{v.ready ? 'var(--success)' : 'var(--warning)'}}">${{v.ready ? v.size_mb + ' MB' : 'Downloading...'}}</span>
          `;
          listEl.appendChild(row);
        }}

        const badge = document.getElementById('system-badge');
        if (allReady) {{
          badge.className = 'badge ready';
          badge.innerHTML = '<span class="status-dot green"></span><span>All Models Ready</span>';
          document.getElementById('generate-btn').disabled = false;
        }} else {{
          badge.className = 'badge busy';
          badge.innerHTML = '<span class="status-dot yellow pulse"></span><span>Models Downloading...</span>';
        }}
      }} catch (err) {{
        console.error('Failed to query models:', err);
      }}
    }}

    setInterval(checkModelPipeline, 5000);
    checkModelPipeline();

    let pollingTimer = null;

    async function startGeneration() {{
      const prompt = document.getElementById('prompt').value.trim();
      if (!prompt) {{
        alert('Please enter a prompt');
        return;
      }}

      const [width, height] = document.getElementById('resolution').value.split('x').map(Number);
      const length = parseInt(document.getElementById('duration').value);
      const steps = parseInt(document.getElementById('steps').value);
      let seed = parseInt(document.getElementById('seed').value);
      if (seed === -1) seed = null;

      const btn = document.getElementById('generate-btn');
      btn.disabled = true;
      btn.innerHTML = '⏳ Submitting to ComfyUI...';

      document.getElementById('status-text').innerText = 'Queueing...';
      document.getElementById('status-log').innerText = 'Submitting workflow graph to ComfyUI backend...';

      try {{
        const res = await fetch('/api/prompt-to-video', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ prompt, width, height, length, steps, seed }})
        }});

        if (!res.ok) {{
          const err = await res.json();
          throw new Error(err.detail || 'Submission failed');
        }}

        const data = await res.json();
        const promptId = data.prompt_id;
        document.getElementById('status-text').innerText = 'Queued';
        document.getElementById('status-log').innerText = `Job ID: ${{promptId}}\\nPosition enqueued. Sampling will start shortly...`;

        btn.innerHTML = '⚙️ Generating Video...';
        pollJob(promptId);
      }} catch (err) {{
        alert('Error: ' + err.message);
        btn.disabled = false;
        btn.innerHTML = '🚀 Generate Video with Sound';
        document.getElementById('status-text').innerText = 'Error';
        document.getElementById('status-log').innerText = 'Failed: ' + err.message;
      }}
    }}

    function pollJob(promptId) {{
      if (pollingTimer) clearInterval(pollingTimer);

      pollingTimer = setInterval(async () => {{
        try {{
          const res = await fetch(`/api/status/${{promptId}}`);
          const data = await res.json();

          if (data.status === 'running') {{
            document.getElementById('status-text').innerText = 'Generating';
            document.getElementById('status-log').innerText = `Job ${{promptId}}: Model executing diffusion steps and decoding video/audio frames...`;
          }} else if (data.status === 'completed') {{
            clearInterval(pollingTimer);
            document.getElementById('status-text').innerText = 'Completed!';
            document.getElementById('status-log').innerText = `Generated video: ${{data.filename}}\\nReady to play!`;

            const player = document.getElementById('player');
            const placeholder = document.getElementById('placeholder');
            const downloadBtn = document.getElementById('download-btn');

            player.src = data.video_url;
            player.style.display = 'block';
            placeholder.style.display = 'none';
            player.play();

            downloadBtn.href = data.video_url;
            downloadBtn.style.display = 'inline-flex';

            const btn = document.getElementById('generate-btn');
            btn.disabled = false;
            btn.innerHTML = '🚀 Generate Another Video';
          }} else if (data.status === 'error') {{
            clearInterval(pollingTimer);
            document.getElementById('status-text').innerText = 'Error';
            document.getElementById('status-log').innerText = 'Generation error: ' + JSON.stringify(data.messages);
            const btn = document.getElementById('generate-btn');
            btn.disabled = false;
            btn.innerHTML = '🚀 Try Again';
          }}
        }} catch (err) {{
          console.error('Polling error:', err);
        }}
      }}, 3000);
    }}
  </script>
</body>
</html>
"""
    return HTMLResponse(content=html)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
