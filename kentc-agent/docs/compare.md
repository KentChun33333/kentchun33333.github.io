# Topic-file runtime: historical V1 vs V2 comparison and benchmark runbook

## Purpose and agent task

Benchmark the `kentc_agent` runtime (`src/kentc_agent/`: foreground checkpoint compaction plus consolidated
local topic Markdown, formerly "v2") on two live-model suites. The former baseline variant (`original`, the
v1 single-checkpoint package) no longer exists; the harnesses run only this runtime. The recorded A/B runs
in `docs/compare-run-*/` compared v1 with v2 and are historical.

An agent executing this document must run the preflight, execute the two benchmark suites sequentially,
retain raw evidence, and produce the report specified below. Reading this document is not
permission to modify the runtime, change the grading rubric, or overwrite earlier results.
Live trials use the configured local model and consume inference resources; do not switch to a paid or
remote provider without authorization. If asked only to prepare instructions, do not start live trials.

**Primary question:** does the runtime complete the tasks correctly and retain useful detail at acceptable
compression, recall, latency, and storage cost? A faster failed run is not a performance improvement.
Comparisons with the historical v1 numbers are cross-run, not paired: source, prompts and graders may have
changed since those runs.

**Attribution limit:** whole-runtime measurements are not a memory-only ablation. Do not attribute every
observed difference to topic files.

## Material implementation differences (historical: removed V1 vs current runtime)

The V1 column describes the removed package and is kept to interpret the recorded A/B runs. Mechanisms
added after those runs (pinned requirements, incremental file writes, preflight, checkpoint Evidence section;
see [topic-file design](session-memory-design.md)) are not covered by any recorded live run.

| Area | V1 (removed) | Current runtime (former V2) | Benefit and cost/risk |
|---|---|---|---|
| Main loop and executor | Model/tool loop, tool allowlists, result routing | Same overall structure; still uses `executor.py` | No additional memory execution layer; ordinary tool restrictions still apply |
| Compression trigger | Window minus reserve; keep recent messages | Same budget policy | Comparable trigger, but compressed prompt sizes can diverge |
| Compression output | Markdown checkpoint string | `CompactionResult(checkpoint, topics)` | Separates immediate task state from durable details; introduces structured-response validation failures |
| Repeated compression | Update previous checkpoint | Update checkpoint and consolidate touched existing topics using complete prior notes | May retain detail outside the short checkpoint; extra model calls can still omit or distort facts |
| Main context | Checkpoint plus recent messages | Short checkpoint, index path, bounded topic-name list, recent messages | Less automatic detail injection; agent must recognize when and what to recall |
| Recall | Re-read original sources when checkpoint is insufficient | Ordinary `read`/`bash` can also inspect topic notes | More recovery paths, but extra tool rounds and possible missed/wrong-topic recall |
| Checkpoint size | Window-derived requested word budget | Word budget additionally capped at 600 and validated | Bounds checkpoint growth; relevant details may move out of immediate context |
| Persistence | Session JSONL | Journal plus immutable note/index generations and SHA-256 verification | Commit-before-drop and restart checks; more files, I/O, and disk use; no automatic generation GC |
| Oversized existing topic | No corresponding topic merge | Fail if the complete merge request cannot fit | Avoids silent input truncation; a large topic can prevent further compression |
| Compression failure | May shorten tool results to make room | Preserve history; no destructive shortening fallback | Better retention, but context exhaustion can stop the run rather than continue |
| Tool-call boundaries | User/assistant cut boundaries | Explicit pending-call tracking and cut validation | Protects complete tool-call/result groups; invalid cuts are rejected |
| Model reply handling | Older retry behavior | Bounded empty/invalid retries; overflow retries count toward call budget; detects standalone textual tool-call envelopes | Better bounded execution; earlier budget exhaustion and possible false-positive envelope detection |
| Exception repair | Complete missing tool results | Also guard repaired results and omit arbitrary exception bodies from repair status | Less unsafe/unbounded text enters context; less diagnostic detail in that status |
| Large results | Can retain a reference to a workspace source file | Also snapshot the source text | Observed content remains available after source changes; extra reads/writes and disk use |
| Repeated calls | No detection | Same tool + arguments + identical result while the first result is still live → pointer to that result, not a second copy | Stops repetition loops early; a repeat after compaction gets the full result again |
| Long command output | Keep the end | grep/rg-shaped output keeps the first matches plus per-file counts; other output keeps the end and states the total line count | Search results stay navigable; detection is heuristic (≥ 60% match-shaped lines) |
| Reply cut inside a tool call | Generic "complete response" retry | Retry instruction says to write large content in parts (≤ ~300 lines, then append) | Fewer lost deliverables at the output limit; costs extra calls |
| Final-answer guidance | "Verify your work when possible" | When the task produces files or figures: re-derive key numbers with a tool, cross-check deliverables, generate derived files from structured data, never repeat a check; last call answers now unless an explicitly requested output file is still missing | Targets reasoning and consistency errors; verification costs calls under tight budgets |
| Document parser | Older incomplete-response handling | Retries non-normal completion; closes worker lifecycle | Stricter completion, but useful partial output may be rejected and retries cost tokens/time |
| Instructions/persona | Extra instructions supplied at startup; workspace instructions truncated at 20,000 characters | Saved persona/instructions can resume; workspace instructions are not truncated | Continuity and no silent instruction truncation; stale saved instructions or huge policy files can consume context |
| Isolation | `.kentc-agent`, `KENTC_AGENT_*` | At the time: separate state dir, env prefix and CLI. Now the only runtime, using `.kentc-agent`, `KENTC_AGENT_*`, `kentc-agent` | Historical; no separate deployment remains |

There is no hot/cold cache, SQLite store, background curator, intrinsic memory tool, or retrieval ledger.
Both serializers (v1 historically, and the current runtime) expose only the first 2,000 characters of each old tool result to summarization.
Topic memory does not automatically recover evidence omitted by that prefix, guarantee factual retention,
or provide unlimited scaling. Published note files are verified snapshots, not hand-editable documents.

Relevant implementation: [compaction](../src/kentc_agent/context/compaction.py),
[session](../src/kentc_agent/adapters/session.py),
[budget](../src/kentc_agent/agent/budget.py),
[loop](../src/kentc_agent/agent/loop.py),
[executor](../src/kentc_agent/agent/executor.py).
See [topic-file design](session-memory-design.md) for storage and failure semantics.

## Experiment rules

1. Run from the repository root in one shell. Use only synthetic fixtures and fresh temporary sessions.
   Never seed a trial from real user sessions or real compliance/customer records.
2. Freeze source, model/deployment, context window, prompts, graders, seed, tools, output limits, and run
   budgets for the entire comparison. Record source hashes and environment/deployment metadata before
   running. Recheck source hashes afterward; source drift invalidates combining affected trials.
3. The harnesses have no variant option; every trial runs the current runtime. Do not reconstruct the
   removed v1 or `tiered` implementations for a new comparison.
4. Run sequentially on the shared model. Do not parallelize trials, run both suites concurrently, or
   concurrently run another inference workload.
5. Use four repetitions per suite for the main run below. This is a small sample, not
   proof of statistical significance or a p95 estimate. Any reduced run must be labelled a smoke run.
6. Do not change settings, raise the budget for selected trials, inject extra memory tools, repair generated reports,
   reveal ground truth to the agent, or retry only losing trials. Keep failures and incomplete outputs.
7. Both harnesses construct `Settings` directly. They do **not** load normal CLI/user/workspace configuration
   or honor `KENTC_AGENT_*` endpoint overrides through the usual configuration loader. Their default
   upstream is `http://127.0.0.1:8081/v1`, discovered through `/models`; STR inserts a local usage proxy.
   Neither benchmark CLI exposes a base-URL option. If the required deployment is unavailable, report the
   missing prerequisite rather than silently changing global defaults or using a different provider.
8. Temperature and reasoning effort are controlled, but equal configured `max_turns` is not necessarily
   equal HTTP-call allowance: retry accounting differs, and compression calls are separate. Report actual
   calls and tokens, including extraction, consolidation, and retries wherever usage is available.
9. Do not overwrite historical JSON or artifact directories. Former v1/v2 and tiered results are historical
   evidence, not measurements of the current runtime. Never mix their schemas or samples with new results.

## Step 1 — Preflight and a fresh output directory

Install dependencies if needed; do not upgrade the model or dependencies mid-comparison:

```sh
uv sync --extra dev
uv run --no-sync python examples/compare_memory.py --help
uv run --no-sync python examples/str_benchmark.py --help
uv run --no-sync pytest -q tests/test_topic_compaction.py tests/test_new_memory_runtime.py tests/test_requirements_and_file_writes.py
uv run --no-sync python examples/str_benchmark.py --self-check
```

The STR self-check makes no model calls. Expect an empty report score of 0, a reference score of 1,
and a deliberately flawed report scoring below the reference. These checks validate mechanics/graders,
not live-model quality. If a check fails, preserve its output and diagnose before launching trials; do not
rerun merely to confirm an already observed failure.

Create a unique result directory and use the same shell for subsequent commands:

```sh
RUN_DIR="$(mktemp -d docs/compare-run-XXXXXX)"
printf 'Results: %s\n' "$RUN_DIR"
curl --fail --silent --show-error --noproxy '*' --max-time 10 \
  http://127.0.0.1:8081/v1/models > "$RUN_DIR/models-before.json"
```

Inspect the response before proceeding: the selected model must have a positive deployed context limit
(`meta.n_ctx` or `max_model_len`). Record the selected model ID, window, quantization/backend if known,
Python/platform, dependency state, source hashes, and whether cache/server state is controlled in
`$RUN_DIR/environment.md`. Never put credentials in this file. Do not assume a historical model name or
window still applies. A very large window may avoid compression entirely; mark that limitation rather
than silently shrinking the window or claiming to have measured memory behavior.

## Step 2 — Seeded-history robustness suite

```sh
uv run --no-sync python examples/compare_memory.py \
  --repeats 4 --output "$RUN_DIR/memory.json"
```

The parent runner executes both cases; do not use its internal worker switches as a replacement for the
full run (`--case`/`--trial` select a single trial). Shared settings include temperature 0, main/sub effort `none`,
2,048 output tokens, configured `max_turns=8`, reserve 16,384, recent-history target 20,000, and tools
`read`/`bash`. Actual reserve/recent targets remain capped by the discovered window.

- **Buried revision:** recover the approved revision, signed amendment, exact identifiers and rollback
  SHA, and distinguish a later unapproved proposal. Crucial evidence lies beyond the summarization prefix.
- **Failed repair:** distinguish recurring decoder errors from a separate cache error and an unsupported
  success claim. The rubric requires a real failing `verify.py --strict` tool observation, not just an answer
  asserting that verification ran. Failure of that fixture verification is expected evidence, not a reason
  to repair the intentionally faulty fixture.

This suite imports completed history instead of generating it through normal tool admission. History
creation/native earlier compression costs are excluded. The agent can re-read the evidence file.
It measures imported-history recovery, not long-task throughput or memory-only recall. See
[case definitions and measurement details](memory-comparison.md).

## Step 3 — Empty-session long-task suite

After Step 2 finishes:

```sh
uv run --no-sync python examples/str_benchmark.py \
  --repeats 4 --persons 40 --seed 7 \
  --max-turns 80 --timeout 10800 --output "$RUN_DIR/str.json"
```

Each trial starts empty and receives the same multi-format synthetic case and prompt. Tools are
`read`, `bash`, `write`, `edit`; temperature 0, main/sub effort `none`, output limit 4,096.
The case covers linked identities, transactions, decoys, and a structured HTML report. Grade axes are
A: overall picture, B: cross-identification, C: report; retain both axis and overall scores.
These are process demonstrations, not real STR filings, legal advice, or compliance decisions.

Generated reports, when present, are copied to `$RUN_DIR/str.artifacts/trial-<n>/`.
Inspect `index.html` in a browser and compare `findings.json` with the rubric; do not edit either artifact.
A missing artifact is a result. The deterministic HTML rubric is not proof that layout renders correctly.
See [STR benchmark specification](str-benchmark.md).

## Step 4 — Audit completeness and classify outcomes

- `memory.json` and `str.json` must contain every planned repetition; the memory suite must also
  contain both cases. Report every trial, not whichever score looks best.
- Check model/window equality and case/corpus hashes. The harnesses enforce these within each suite;
  also verify deployment consistency across suites and inspect a fresh `/models` response afterward.
- Check process errors, timeout/limit stops, missing final answers, and missing provider usage. The runners
  write JSON after completed trials; a subprocess timeout/crash can abort the remaining run. Preserve
  partial JSON and console evidence, label the run incomplete, and do not treat missing trials as successes
  or silently exclude them. A rerun needs a new directory and a declared reason.
- Check that compression actually happened using compaction observations/statuses. No successful
  compaction means the trial does not establish topic-memory effectiveness. Distinguish a compression
  failure from a completed compression followed by failed recall.
- Where logs permit, identify ordinary reads of note indexes/topics versus re-reading original evidence.
  A correct answer obtained from original sources does not prove that a topic note retained the fact.
  STR's compact tool log and truncated statuses limit forensic detail; say when the mechanism is unknown.
- Classify failures using observed evidence: no compression exercised; extraction/merge failure;
  persistence failure; missed/wrong recall; wrong answer despite recall; tool loop/budget exhaustion;
  provider/infrastructure failure. Do not invent an explanation when logs cannot distinguish causes.

## Step 5 — Deliverables and interpretation

Write `$RUN_DIR/report.md` with links to raw JSON, environment metadata, and saved report artifacts.
Include:

1. **Protocol and validity:** exact commands, repetitions, source/environment identity, matched inputs,
   any deviations, incomplete trials, whether compression/recall was observed, and uncontrolled cache load.
2. **Correctness table:** memory pass counts and failed checks by case; STR overall and A/B/C
   scores, missing reports, fixture changes, and abnormal terminations. Show per-trial values and medians.
3. **Cost table:** answer wall time, final-answer first-content time where available, answer-plus-close
   time, foreground/summary request counts, prompt/completion tokens, missing-usage counts, and client
   peak RSS. Compute totals from raw trial values; do not add separate medians and call it a median total.
4. **Behavior:** repeated reads/calls, tool errors, file coverage, compactions, note recall evidence, and
   source-recovery behavior. Include failed/incomplete trials.
5. **Assessment:** whether the tasks are completed, with which failure modes and at what cost; any
   comparison with historical v1/v2 numbers must be labelled cross-run. State which evidence supports it.

Sum foreground and summary usage to report total inference cost. Missing usage is unknown, not zero.
First-content time is not time to first internal reasoning/tool delta. Peak RSS covers the client process,
not model-server/GPU memory, and is not a direct measure of retained memory-note size. STR cache metrics
are provider-dependent: unavailable cache/timing fields are not evidence of zero cache use or zero work.

The shipped harnesses delete their temporary workspaces. They preserve result JSON and STR report
artifacts, **not** the full session journals, topic generations, or every trace. They do not measure disk-growth
curves, workspace relocation, long-horizon restart quality, or all consolidation losses. Existing regression
tests cover selected mechanics, not those live-model quality claims. If deeper evidence is required,
report the instrumentation gap and propose a separately scoped experiment rather than silently changing
this comparison mid-run.

Historical context: [recorded v1 vs v2 runs](compare-run-4rep-1zpd8yum/report.md),
[prior memory experiments](memory-comparison.md) and [prior STR results](str-benchmark.md).
Those recorded runs cannot establish the quality of the current runtime.
