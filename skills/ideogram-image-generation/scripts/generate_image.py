#!/usr/bin/env python3
"""Generate an image with the local Ideogram 4 FP8 setup."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REPO_ID = "ideogram-ai/ideogram-4-fp8"
DEFAULT_MODEL_DIR = ROOT / "model" / "ideogram-4-fp8"
DEFAULT_HF_HOME = ROOT / "model" / ".hf-cache"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--width", type=int, default=1024)
    parser.add_argument("--height", type=int, default=1024)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--device", default=None, help="cuda, mps, or cpu. Defaults to best available.")
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--repo-id", default=DEFAULT_REPO_ID)
    parser.add_argument("--hf-home", type=Path, default=DEFAULT_HF_HOME)
    parser.add_argument(
        "--sampler-preset",
        default="V4_DEFAULT_20",
        help="One of the presets exposed by ideogram4.sampler_configs.PRESETS.",
    )
    parser.add_argument(
        "--magic-prompt",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Expand the plain prompt with Ideogram/OpenRouter magic prompting.",
    )
    parser.add_argument(
        "--magic-prompt-key",
        default=os.environ.get("MAGIC_PROMPT_API_KEY") or os.environ.get("IDEOGRAM_API_KEY"),
    )
    parser.add_argument("--warn-on-caption-issues", action="store_true")
    parser.add_argument("--hive-text-key", default=os.environ.get("HIVE_TEXT_MODERATION_KEY"))
    parser.add_argument("--hive-visual-key", default=os.environ.get("HIVE_VISUAL_MODERATION_KEY"))
    return parser.parse_args()


def default_device(torch_module) -> str:
    if torch_module.cuda.is_available():
        return "cuda"
    if torch_module.backends.mps.is_available():
        return "mps"
    return "cpu"


def validate_size(width: int, height: int) -> None:
    for label, value in {"width": width, "height": height}.items():
        if value < 256 or value > 2048 or value % 16 != 0:
            raise SystemExit(f"{label} must be a multiple of 16 between 256 and 2048; got {value}.")
    ratio = max(width / height, height / width)
    if ratio > 6:
        raise SystemExit(f"aspect ratio must be at most 6:1; got {width}:{height}.")


def print_flags(label: str, flags: list[tuple[str, float]]) -> None:
    print(f"{label}:", file=sys.stderr)
    for name, score in sorted(flags, key=lambda item: -item[1]):
        print(f"  {name}: {score:.3f}", file=sys.stderr)


def patch_local_hf_download(model_dir: Path) -> str:
    """Let ideogram4's direct hf_hub_download calls read from a local snapshot."""
    if not model_dir.exists():
        return DEFAULT_REPO_ID

    from ideogram4 import pipeline_ideogram4

    original_hf_hub_download = pipeline_ideogram4.hf_hub_download
    local_root = model_dir.resolve()

    def local_hf_hub_download(repo_id: str, filename: str, *args, **kwargs) -> str:
        if Path(repo_id).resolve() == local_root:
            candidate = local_root / filename
            if candidate.exists():
                return str(candidate)
            raise FileNotFoundError(
                f"Missing {candidate}. Run scripts/download_model.py until the model snapshot is complete."
            )
        return original_hf_hub_download(repo_id=repo_id, filename=filename, *args, **kwargs)

    pipeline_ideogram4.hf_hub_download = local_hf_hub_download
    return str(local_root)


def main() -> None:
    args = parse_args()
    os.environ.setdefault("HF_HOME", str(args.hf_home.resolve()))
    validate_size(args.width, args.height)

    import torch
    from ideogram4 import (
        DEFAULT_MAGIC_PROMPT,
        MAGIC_PROMPTS,
        PRESETS,
        Ideogram4Pipeline,
        Ideogram4PipelineConfig,
        aspect_ratio_from_size,
        moderate_image,
        moderate_prompt,
    )

    weights_repo = patch_local_hf_download(args.model_dir) if args.model_dir else args.repo_id

    if args.sampler_preset not in PRESETS:
        available = ", ".join(sorted(PRESETS))
        raise SystemExit(f"Unknown sampler preset {args.sampler_preset!r}. Available: {available}")

    if args.hive_text_key:
        flags = moderate_prompt(args.prompt, args.hive_text_key)
        if flags:
            print_flags("Prompt rejected by Hive text moderation", flags)
            raise SystemExit(2)
    else:
        print("WARNING: no Hive text moderation key configured; prompt screening is disabled.", file=sys.stderr)

    prompt = args.prompt
    if args.magic_prompt:
        if not args.magic_prompt_key:
            raise SystemExit(
                "Magic prompt is enabled but no API key was found. "
                "Set IDEOGRAM_API_KEY or MAGIC_PROMPT_API_KEY, or pass --no-magic-prompt."
            )
        aspect_ratio = aspect_ratio_from_size(args.width, args.height)
        magic = MAGIC_PROMPTS[DEFAULT_MAGIC_PROMPT](api_key=args.magic_prompt_key)
        print(f"Expanding prompt with {DEFAULT_MAGIC_PROMPT} for {aspect_ratio}...", file=sys.stderr)
        prompt = magic.expand(args.prompt, aspect_ratio=aspect_ratio)
        print(f"Expanded caption:\n{prompt}", file=sys.stderr)

    device = args.device or default_device(torch)
    preset = PRESETS[args.sampler_preset]

    pipe = Ideogram4Pipeline.from_pretrained(
        config=Ideogram4PipelineConfig(weights_repo=weights_repo),
        device=device,
        dtype=torch.bfloat16,
    )
    images = pipe(
        prompt,
        height=args.height,
        width=args.width,
        num_steps=preset.num_steps,
        guidance_schedule=preset.guidance_schedule,
        mu=preset.mu,
        std=preset.std,
        seed=args.seed,
        raise_on_caption_issues=not args.warn_on_caption_issues,
    )

    if args.hive_visual_key:
        flags = moderate_image(images[0], args.hive_visual_key)
        if flags:
            print_flags("Generated image rejected by Hive visual moderation", flags)
            raise SystemExit(2)
    else:
        print("WARNING: no Hive visual moderation key configured; output screening is disabled.", file=sys.stderr)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    images[0].save(args.output)
    print(f"Saved {args.output}")


if __name__ == "__main__":
    main()
