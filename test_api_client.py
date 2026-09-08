#!/usr/bin/env python3
"""
Example Python client to call the MiniMax H3 Text-to-Video FastAPI service.
Usage:
    python3 test_api_client.py "A futuristic flying car cruising through clouds at sunset"
"""

import sys
import time
import requests

API_URL = "http://127.0.0.1:8000"

def generate_video(prompt: str, width: int = 864, height: int = 480, duration_frames: int = 124, steps: int = 4):
    print(flush=True, f"[1/3] Checking model status at {API_URL}/api/models...")
    models_res = requests.get(f"{API_URL}/api/models").json()
    if not models_res.get("all_ready"):
        print(flush=True, "Notice: Some models are still downloading:")
        for k, v in models_res["models"].items():
            print(flush=True, f"  - {k}: {'Ready' if v['ready'] else 'Downloading...'}")
        print(flush=True, "If all required models are not yet ready, the job will fail or queue.")

    print(flush=True, f"\n[2/3] Submitting generation prompt: \"{prompt}\"")
    payload = {
        "prompt": prompt,
        "width": width,
        "height": height,
        "length": duration_frames,
        "steps": steps
    }
    submit_res = requests.post(f"{API_URL}/api/prompt-to-video", json=payload)
    if submit_res.status_code != 200:
        print(flush=True, f"Error submitting prompt: {submit_res.text}")
        return

    data = submit_res.json()
    prompt_id = data["prompt_id"]
    print(flush=True, f"Job queued successfully! Prompt ID: {prompt_id}")

    print(flush=True, "\n[3/3] Polling generation progress...")
    start_time = time.time()
    while True:
        status_res = requests.get(f"{API_URL}/api/status/{prompt_id}").json()
        status = status_res.get("status")
        elapsed = time.time() - start_time
        print(flush=True, f"[{elapsed:.1f}s] Status: {status}")

        if status == "completed":
            video_url = API_URL + status_res["video_url"]
            print(flush=True, f"\n🎉 Video generation completed!")
            print(flush=True, f"Video URL: {video_url}")
            break
        elif status == "error":
            print(flush=True, f"\n❌ Error during generation: {status_res}")
            break

        time.sleep(5)

if __name__ == "__main__":
    test_prompt = sys.argv[1] if len(sys.argv) > 1 else (
        "Cinematic drone shot of a futuristic Tokyo with neon signs, "
        "flying taxis, rain puddles reflecting glowing billboards, synthwave soundtrack."
    )
    generate_video(test_prompt)
