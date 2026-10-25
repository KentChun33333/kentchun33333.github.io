# Strata + Qwen3.8-Flash-Next (IQ3_S) on this Mac

Local 125B MoE model served by [Niko1221/Strata](https://github.com/Niko1221/Strata) (Metal engine), wired into omp.

## Machine

- Apple M3 Ultra, 96 GB unified memory, macOS 27.0.1, Command Line Tools installed.

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
