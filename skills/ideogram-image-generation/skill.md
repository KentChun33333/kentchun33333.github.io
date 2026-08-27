# Ideogram Image Generation Skill

> **Audience**: Designers, resume builders, portfolio writers, and career-storytelling workflows in `breeze-man`.
> **Purpose**: Generate local images with Ideogram 4 FP8 for visual concepts, hero images, portfolio graphics, and document assets.

This skill uses the official `ideogram4` inference package and the gated Hugging Face model `ideogram-ai/ideogram-4-fp8`.

## Local Paths

- Model snapshot: `breeze-man/model/ideogram-4-fp8`
- Hugging Face cache: `breeze-man/model/.hf-cache`
- Generated images: prefer `breeze-man/output/<project>/images/`
- Helper scripts: `breeze-man/skillset/ideogram-image-generation/scripts/`

The workspace `.gitignore` already excludes `model/` directories and `*.safetensors`, so downloaded weights should stay out of source control.

## One-Time Setup

1. Accept the Hugging Face gate for `ideogram-ai/ideogram-4-fp8`.
2. Authenticate with Hugging Face:

```bash
hf auth login
```

or:

```bash
export HF_TOKEN="hf_..."
```

3. Create a Python 3.11 environment and install the official inference package:

```bash
cd breeze-man/skillset/ideogram-image-generation
uv venv --python python3.11 .venv
. .venv/bin/activate
uv pip install -r requirements.txt
```

4. Download the model into `breeze-man/model/`:

```bash
python scripts/download_model.py
```

## Generate An Image

Basic local generation:

```bash
cd breeze-man/skillset/ideogram-image-generation
. .venv/bin/activate
python scripts/generate_image.py \
  --prompt "editorial portrait of a senior AI product leader, cinematic lighting, confident but approachable" \
  --output ../../output/job-hup/images/ai_leader_portrait.png \
  --width 1024 \
  --height 1024 \
  --seed 42
```

Higher-quality official prompt expansion, when `IDEOGRAM_API_KEY` is available:

```bash
IDEOGRAM_API_KEY="..." \
python scripts/generate_image.py \
  --magic-prompt \
  --prompt "premium executive resume cover image for responsible AI leadership" \
  --output ../../output/job-hup/images/responsible_ai_cover.png \
  --width 1536 \
  --height 1024
```

## Operating Notes

- FP8 is the right local choice for Apple Silicon, CPU, and CUDA. NF4 is CUDA-only.
- Supported dimensions are multiples of 16 from 256 to 2048, with aspect ratios up to 6:1.
- `V4_QUALITY_48` gives best quality, `V4_DEFAULT_20` is a faster default, and `V4_TURBO_12` is for drafts.
- Without Hive moderation keys, the helper will not run external safety screening. Use conservative, professional prompts for career and public-facing assets.
- The Ideogram 4 license is non-commercial. Confirm usage rights before using generated assets in commercial materials.
