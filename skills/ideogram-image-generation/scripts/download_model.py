#!/usr/bin/env python3
"""Download Ideogram 4 FP8 into the breeze-man local model directory."""

from __future__ import annotations

import argparse
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REPO_ID = "ideogram-ai/ideogram-4-fp8"
DEFAULT_LOCAL_DIR = ROOT / "model" / "ideogram-4-fp8"
DEFAULT_HF_HOME = ROOT / "model" / ".hf-cache"

ALLOW_PATTERNS = [
    "model_index.json",
    "LICENSE.md",
    "README.md",
    "scheduler/*",
    "text_encoder/*",
    "tokenizer/*",
    "transformer/*",
    "unconditional_transformer/*",
    "vae/*",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-id", default=DEFAULT_REPO_ID)
    parser.add_argument("--local-dir", type=Path, default=DEFAULT_LOCAL_DIR)
    parser.add_argument("--hf-home", type=Path, default=DEFAULT_HF_HOME)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    os.environ.setdefault("HF_HOME", str(args.hf_home.resolve()))

    from huggingface_hub import snapshot_download
    from huggingface_hub.errors import GatedRepoError

    args.local_dir.mkdir(parents=True, exist_ok=True)
    args.hf_home.mkdir(parents=True, exist_ok=True)

    try:
        path = snapshot_download(
            repo_id=args.repo_id,
            local_dir=str(args.local_dir.resolve()),
            allow_patterns=ALLOW_PATTERNS,
        )
    except GatedRepoError as exc:
        raise SystemExit(
            "Hugging Face blocked the download because the model is gated. "
            "Accept the license on the model page, then run `hf auth login` "
            "or export `HF_TOKEN`, and retry."
        ) from exc

    print(f"Downloaded {args.repo_id}")
    print(f"Local snapshot: {path}")
    print(f"HF cache: {args.hf_home.resolve()}")


if __name__ == "__main__":
    main()

