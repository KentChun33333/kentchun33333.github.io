# Strata + Qwen3.8-Flash-Next (IQ3_S) on this Mac

Local 125B MoE model served by [Niko1221/Strata](https://github.com/Niko1221/Strata) (Metal engine), wired into omp.

## Machine

- Apple M3 Ultra, 96 GB unified memory, macOS 27.0.1, Command Line Tools installed.

## Huihui v2 Swift IQ3_S

The active server is now **Huihui v2 Swift IQ3_S**, not Swift IQ3_XXS. Both downloaded shards in `~/Developer/Strata-data/` match the SHA-256 hashes published by [Huihui v2](https://huggingface.co/huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-v2-GGUF/tree/main/swift-IQ3_S):

- Shard 1: `9cdb79ad99ef066064628f13b67ace8ef077d02d9d3848a53b11d5c3cbe94332`
- Shard 2: `04e1f010edbeacbce3a8948abf0044e858d73a37fc74a0e58abeeff98cbe4f0f`

Metal maps one native GGUF, but Swift splits its layers between both shards. Prepared `metal/huihui-v2-swift-iq3_s-metal.gguf` (51.18 GiB) using `metal/tools/metal_repack.py --verify`: all 1,223 output tensors are byte-identical to their source tensors. The PLE table stays on disk in **shard 1**. Do not delete either source shard.

`tools/iq_pack.py` prepared `packs/swift-iq3_s/`, including Swift's own tokenizer. Its 96 float conversions were exact; no rounded conversions were needed. No checksum bypass or runtime refusal vector is used.

Configuration: `~/Developer/Strata/strata-swift-iq3_s.json`. Preset: **Swift-IQ3S-Mac**. Engine: prebuilt Metal 0.1.48. Context: 62,536. Text only; vision and MTP are off for this compatibility trial. The original IQ3_S config, weights and preset remain intact.

### Daily use: start here

Setup is already complete on this Mac. **Do not repeat the preparation steps below for normal use.** Strata runs the model server; omp or Pi is the terminal app you use to chat with it.

#### 1. Start the model server

Open Terminal and run this from any directory:

```sh
~/.local/bin/strata launch --preset Swift-IQ3S-Mac --no-tui
```

Wait for `Ready: http://127.0.0.1:8081`. The command then returns to your shell; the server keeps running in the background. You do not need to keep a dedicated terminal open for it. If the same preset is already running, the launcher reuses it.

If the original `IQ3S-Mac` model is running instead, stop it first with `~/.local/bin/strata launch --stop --preset IQ3S-Mac`, then run the Swift launch command. Load only one model at a time.

#### 2. Open an interactive chat

Choose **one** of these apps. Run it in your project directory if you want it to work on that project's files.

**omp:**

```sh
omp --model strata/huihui-v2-swift-qwen3.8-flash-next-iq3_s
```

**Or Pi:**

```sh
pi --model strata/huihui-v2-swift-qwen3.8-flash-next-iq3_s
```

Type your prompt in the app. The explicit `--model` selects Swift for this session without changing your default model. Exiting the app does not stop the Strata server.

For a single prompt that prints its answer and exits:

```sh
omp --model strata/huihui-v2-swift-qwen3.8-flash-next-iq3_s \
  -p "Explain how a hash table works."
```

#### 3. Check status or watch activity

```sh
~/.local/bin/strata launch --status
```

For the live monitor, use a second terminal while chatting:

```sh
~/.local/bin/strata monitor --url http://127.0.0.1:8081
```

The API endpoint for other clients is `http://127.0.0.1:8081/v1`, without an API key. To check which model is actually loaded:

```sh
curl -fsS http://127.0.0.1:8081/health
```

Look for `"loaded": true` and `"model": "huihui-v2-swift-qwen3.8-flash-next-iq3_s"`. If the connection is refused, start the server using step 1.

#### 4. Stop the model when finished

This stops the server and unloads the model; it does not delete the downloaded files:

```sh
~/.local/bin/strata launch --stop --preset Swift-IQ3S-Mac
```

#### Optional: switch back to the original model

Stop Swift, start the original preset, and select the original model ID in your terminal app:

```sh
~/.local/bin/strata launch --stop --preset Swift-IQ3S-Mac
~/.local/bin/strata launch --preset IQ3S-Mac --no-tui
omp --model strata/qwen3.8-flash-next-iq3_s
```

For Pi, use `pi --model strata/qwen3.8-flash-next-iq3_s` instead. Both presets use port 8081, so do not run them together.

### Reproduce the preparation

These commands use the existing Strata checkout and Python environment. Both Swift shards must be fully downloaded in `~/Developer/Strata-data/` first. Stop any loaded model before repacking or preparing a pack; do not run two large models concurrently.

```sh
cd ~/Developer/Strata
strata launch --stop --preset IQ3S-Mac
strata launch --stop --preset Swift-IQ3S-Mac

.venv/bin/python metal/tools/metal_repack.py \
  --shard1 ../Strata-data/Swift-Qwen3.8-Flash-Next-GSQ-RCO-IQ3_S-00001-of-00002.gguf \
  --out ../Strata-data/metal/huihui-v2-swift-iq3_s-metal.gguf \
  --verify

STRATA_GGUF_PY="$PWD/third_party/llama.cpp/gguf-py" \
  .venv/bin/python tools/iq_pack.py \
  --gguf ../Strata-data/metal/huihui-v2-swift-iq3_s-metal.gguf \
  --out ../Strata-data/packs/swift-iq3_s \
  --compat-bf16
```

Keep `strata-swift-iq3_s.json` pointed at the repacked file for both `--native` and `--native-dense-gguf`, the original Swift **shard 1** for `--ple-gguf`, and the Swift pack's `tokenizer/`. Reusing the original model's pack or assuming the PLE table is in shard 2 is incorrect for this checkpoint.

The first successful launch saved the preset with:

```sh
strata launch --family swift --model IQ3_S --context 62536 \
  --vision off --mtp off --parallel 1 --port 8081 --access local \
  --save-preset Swift-IQ3S-Mac --no-tui --yes
```

Preparation adds a 51.18 GiB repacked GGUF plus the pack alongside the two source shards; leave room for those files. The engine executable is pinned to version 0.1.48 in the JSON configuration, so verify its path when upgrading Strata.


Verified: health reports Swift loaded, `17 × 23` returned `391`, and omp/Pi compatibility probes each passed a prompt and a structured `get_weather` call. Actual `omp -p` and `pi -p` requests both returned `pong`. A 256-token hash-table explanation measured **61.9 tok/s decode**, with no draft tokens; it reached the requested token limit. This is one smoke measurement, not a comparative benchmark. These checks establish local text/tool compatibility, not benchmark quality, refusal reduction, vision or MTP compatibility.

## What was done

1. Cloned the repo to `~/Developer/Strata`.
2. First installed UD-Q4_K_XL (~4-bit, `./setup.sh --yes --model UD-Q4_K_XL ...`). It needs ~91 GB but Metal keeps only ~72 GB resident on 96 GB, so experts streamed from the SSD: ~9-11 tok/s. Strata's docs recommend it from 128 GB.
3. Switched to **IQ3_S** (the recommended pack for 96 GB; fits in memory): ~45-57 tok/s decode, ~109 tok/s prompt (warm).
   ```
   cd ~/Developer/Strata && ./setup.sh --model IQ3_S --vision yes
   ```
   Setup wrote `strata-iq3_s.json` (context 65536, images on) and `run-iq3_s.sh`; model files are in `~/Developer/Strata-data/`.
4. The Q4 files (~217 GB incl. the repacked copy) were deleted to make room. The old `strata-unsloth-ud-q4_k_xl.json` / `run-unsloth-ud-q4_k_xl.sh` in the repo are stale.
5. Added an omp provider in `~/.omp/agent/models.yml` (below).

6. Installed the official Strata CLI with its checksum- and signature-verifying installer, then downloaded prebuilt Metal engine **0.1.48**. The CLI reused the existing model, pack, MTP and image projector without downloading another model.
7. Saved launcher preset `IQ3S-Mac`, with localhost port 8081, context **62536**, GPU vision and one request at a time. The launcher initially reused the source engine; corrected `strata-iq3_s.json`'s engine and vision executable paths to `~/.local/share/strata/components/engine/0.1.48-macos-arm64-metal/`. Confirmed both running processes use those binaries. The source binaries and original `.bak` config remain available.
8. Verified health, a chat reply (53 tok/s on a 20-token response), omp/Pi prompt-and-tool compatibility probes, and actual `omp -p` / `pi -p` requests (both returned `pong`). This is a smoke test, not evidence of a speed improvement. Control/refusal vectors remain unsupported on Metal.

## Why port 8081, not 8080

Port 8081 was chosen to avoid a separate `llama-server` on 8080. Keep using 8081 for the existing omp/Pi endpoints. Do not start the old Python server alongside the launcher on the same port.

## Launch

```sh
strata launch --preset IQ3S-Mac --no-tui
```

The launcher starts a background server and returns. It does not need this assistant session to stay open. If `strata` is not on PATH, use `~/.local/bin/strata`.

```sh
strata launch --status
strata monitor --url http://127.0.0.1:8081
```

The first prompt after a start can be slower while macOS reads the model file. The original Python launch remains available, but must not run concurrently on port 8081:

```sh
cd ~/Developer/Strata
.venv/bin/python serve/server.py --engine strata --config strata-iq3_s.json --port 8081
```

## Verify

```sh
curl http://127.0.0.1:8081/health   # "status": "ok", "loaded": true, "model": "qwen3.8-flash-next-iq3_s"
curl http://127.0.0.1:8081/v1/chat/completions -H "Content-Type: application/json" \
  -d '{"model":"strata","messages":[{"role":"user","content":"Say hello."}],"max_tokens":64,"reasoning_effort":"none"}'
```

Chat UI with live monitor: <http://127.0.0.1:8081/>

## Stop

```sh
strata launch --stop --preset IQ3S-Mac
```

## Endpoints

| Use | URL |
| --- | --- |
| OpenAI-compatible | `http://127.0.0.1:8081/v1` |
| Anthropic-compatible | `http://127.0.0.1:8081/v1/messages` |
| Claude Code | `ANTHROPIC_BASE_URL=http://127.0.0.1:8081` |

One request at a time (no parallel slots on Mac). No API key; listens on 127.0.0.1 only. To expose beyond localhost use `--host 0.0.0.0` with `--api-key <secret>`.

## omp

`~/.omp/agent/models.yml`:

```yaml
providers:
  strata:
    baseUrl: http://127.0.0.1:8081/v1
    auth: none
    api: openai-completions
    models:
      - id: qwen3.8-flash-next-iq3_s
        name: Qwen3.8-Flash-Next IQ3_S (Strata, local)
        reasoning: true
        input: [text, image]
        contextWindow: 65536
        maxTokens: 8192
```

Use: `omp --model strata/qwen3.8-flash-next-iq3_s` (the default in `~/.omp/agent/config.yml` is unchanged). Start the Strata server first. If the port changes, update `baseUrl`.

## Pi agent

`~/.pi/agent/models.json` has a `strata` provider next to `local-llama`:

```json
"strata": {
  "name": "Strata (local)",
  "baseUrl": "http://127.0.0.1:8081/v1",
  "api": "openai-completions",
  "apiKey": "local",
  "compat": { "supportsDeveloperRole": false, "supportsReasoningEffort": true, "maxTokensField": "max_tokens" },
  "models": [{ "id": "qwen3.8-flash-next-iq3_s", "name": "Qwen3.8-Flash-Next IQ3_S (Strata)",
    "reasoning": true, "input": ["text", "image"], "contextWindow": 65536, "maxTokens": 8192,
    "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 } }]
}
```

Use: `pi --model strata/qwen3.8-flash-next-iq3_s` (or pick it in `/model`). Check: `pi --list-models | grep strata`.

## Update / switch

The prebuilt installation is updated with `strata update`. Restart the preset afterwards. This migration pins the imported config's executable paths to engine 0.1.48: after a future engine update, verify the running executable path before assuming the newer component is in use.

The following commands are for the preserved source installation, not the prebuilt engine:

```sh
cd ~/Developer/Strata && ./update.sh          # update Strata without starting
./setup.sh --setup --model Q2_0               # another size (Q2_0 is the fastest)
./setup.sh --build                            # rebuild the Metal engine
```

Setup is resumable. A model switch needs free disk: ~85 GB per pack. Docs: `~/Developer/Strata/docs/MAC.md`, `docs/INSTALL.md`.
