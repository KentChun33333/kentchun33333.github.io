# Live-model memory comparison

The harness benchmarks the `kentc_agent` runtime (foreground compaction into local topic Markdown files) on two synthetic long-history challenges. It measures the whole runtime, not isolated storage, and uses no user sessions. The former baseline variant (v1 `original` checkpoint compaction) no longer exists; recorded results below compare it with earlier implementations and are historical.

**Scope:** bulk history is seeded rather than produced through native tool-result admission. These are oversized imported-history/resume robustness challenges, not steady-state throughput measurements. Every trial receives identical original evidence and the same recovery file. Recorded results below belong to the removed v1 and the former tiered implementation; the recorded v1 vs topic-file v2 A/B runs are in [compare-run-4rep-1zpd8yum](compare-run-4rep-1zpd8yum/report.md), also historical.

## Reproduce

From `kentc-agent/`, with the local OpenAI-compatible deployment running at the default endpoint:

```sh
uv run --no-sync python examples/compare_memory.py \
  --repeats 2 --output docs/memory-comparison-topics.json
```

Optional `--case {buried_revision,failed_repair}` limits the run to one challenge. There is no variant option.

The harness uses explicit `Settings`, not user/workspace configuration or environment overrides. It deliberately makes live model requests. Each trial uses a temporary workspace and a fresh client process. Those workspaces are removed afterward; answers, grades, tool observations, request measurements, and aggregate results remain in the JSON output.

## Matched protocol

- Every trial receives the exact same 66-message synthetic history: an initial user request, 32 completed `read` exchanges, and an archive-completion assistant message. Corpus SHA-256 equality is checked across trials.
- Each individual historical tool result is below the existing 3,000 estimated-token big-result threshold. The total history exceeds the deployed request window after system/tool overhead. Historical messages are seeded rather than generated/admitted by an agent; their generation and native historical eviction costs are excluded.
- The exact original evidence also exists in `evidence.log`. The agent gets `read` and `bash`, with no intrinsic memory tools.
- Trials use the discovered local model/context window, temperature `0`, main/sub-agent reasoning effort `none`, 2,048 output tokens, eight foreground model calls, reserve 16,384, and recent-history preference 20,000. The deployment identity and window must remain unchanged between trials.
- The runtime performs checkpoint extraction and touched-topic consolidation synchronously during compression. Notes are recalled through ordinary tools. There is no curator, idle drain, hot layer, or retrieval quota; all compression calls are counted as summary work.
- Trials run sequentially on the shared model, never concurrently. The model server itself is not restarted between trials. (Historical A/B runs alternated variant order by repetition.)

## Challenge 1: buried revision and amendment

The archive contains 253,331 characters. Four records concern a fictional tenant, `CEDAR-17`:

1. An older approved revision 6.
2. `APR-07`: approved revision 7, quota 471, region `eu-west-2`, and a full rollback SHA.
3. `AMD-02`: a signed amendment to revision 7, changing **only** the quota to 417.
4. A later revision 8 proposal with quota 999 that was **not** approved.

These records occur roughly 6 KB into their respective early tool results, beyond both variants' 2,000-character summarization prefix. Both must recover original evidence if it is no longer resident; a summary-only answer is insufficient. The much longer unrelated tail creates capacity pressure without providing the answers.

A passing answer must recover revision **7**, amended quota **417**, region **`eu-west-2`**, the exact full rollback SHA, and pending revision/quota **8 / 999**, with both approved-record and amendment IDs. Evidence/code files must remain unchanged. The grading values are synthetic, not private deployment information.

## Challenge 2: repeated failure versus an unsupported success claim

The archive contains 253,294 characters. Early records describe:

- Attempts **A** and **C** reproducing exactly `E_FRAME_MARKER pipeline/decoder.py:73 expected=0x7E observed=0x00`.
- Attempt **B** claiming a fix and a happy-path smoke pass, without a strict verification result.
- Attempt **D** containing the same error code but a different path/observed value: `pipeline/cache.py:73`, `0xFF`. It must not be merged with the decoder error.

Unlike challenge 1, these records appear near the start of their tool results: **the original summarizer receives the error evidence**. This avoids making both challenges solely tests of its prefix truncation.

Both agents must execute the same read-only `python3 verify.py --strict` against a deliberately faulty miniature decoder. The independent fixture smoke observed exit code **1** with `FAILED test_reject_zero_marker` and the decoder error above.

A passing answer must report unresolved status, live exit code **1**, the correct failing test, recurring attempts **A/C**, the separate cache path, exact expected/observed markers, and the three supporting error-record IDs. The harness checks that a real `bash` observation contains the failed test and either the shell's exit-one marker or the explicitly captured child `EXIT=1`; an answer merely asserting that verification ran does not pass. Evidence/code files must remain unchanged. The diagnostic path/line is a synthetic label, not a Python traceback location.

## Measurement definitions

- **Answer wall time:** from entering `Agent.run` to its return/error. Includes foreground compression, tool work, and note recall. Excludes fixture construction, seeded history ingestion, and agent initialization; ingestion/init are recorded separately.
- **Answer first-content time:** time until the first streamed content of the final non-tool foreground reply. Includes prerequisite summarization/tool loops. This is not merely the first tool-call delta or internal summarizer token.
- **Answer plus close:** wall time from entering `Agent.run` until agent close finishes (`answer_plus_close_s`). No background idle phase.
- **Tokens:** provider-reported prompt/completion counts per request, separated into foreground and summary (checkpoint extraction and topic consolidation). Missing usage is counted explicitly. Summed prompt tokens measure processed request volume, not unique source tokens or uncached prefill work.
- **Memory:** lifetime peak RSS of each fresh **client** process, including Python/imports/fixture data. Baseline peak RSS is recorded before history ingestion. The model server/GPU footprint is excluded.
- **Correctness:** exact consumer-visible fields, evidence IDs, required real verification, and unchanged fixtures. All checks must pass. This is a narrow deterministic rubric, not a general semantic quality judge.

**Historical results only:** every recorded result below compares v1 with the removed tiered-memory v2, including its then-current quotas, curator, loop policies, and idle-close measurements. Saved JSON and numbers are preserved; none measure the current runtime.

## Recorded results before the capacity correction

Recorded on 2026-10-30 using local text-only model `huihui-v2-swift-qwen3.8-flash-next-iq3_s`, deployed window **62,536**. Eight live trials were run; their machine-readable results were removed on 2026-11-02 and the values below are historical. Values below are medians of two trials; half-token medians are not fractional provider usage.

| Challenge | Variant | Passed | Time to return/error (s) | All-request input tokens | All-request output tokens | Model calls | Client peak RSS (MiB) |
|---|---|---:|---:|---:|---:|---:|---:|
| Buried revision | Original | 0/2 | 71.56 | 197,016.5 | 1,338 | 9 | 41.78 |
| Buried revision | Tiered | 0/2 | 50.50 | 40,089.5 | 68 | 1 | 42.48 |
| Failed repair | Original | 2/2 | 60.66 | 140,181 | 1,071 | 7 | 40.38 |
| Failed repair | Tiered | 0/2 | 50.86 | 40,082 | 92.5 | 1 | 42.52 |

**There is no demonstrated tiered-memory performance win in this experiment.** Its shorter runs and lower token counts ended in admission failure, not successful answers.

- **Original, buried revision:** both runs found the relevant original records through tools, but continued checking and exhausted the eight foreground-call allowance without a final answer. Each also made one summarization request. This is a termination/tool-loop failure, not proof that the source was unrecoverable.
- **Original, failed repair:** both runs answered every required field correctly and executed the failing verification. Final-answer first-content time was **58.55 s** median. Each made one summarization request; total model-call counts were six and eight.
- **Tiered, both challenges:** all four runs returned `CapacityConflict: No allowance for the minimum retrieval response; stop or narrow this task.` after the first model reply requested tools, before any requested tool executed. There was no final answer or final-answer TTFT.
- **Background curation:** enabled, but no curation job/request started in the four failing tiered trials. This experiment consequently does **not** measure active background overhead or benefit. Zero calls must not be interpreted as zero general curation cost.
- **History ingestion:** the original's median append times were **4.18 / 3.78 ms** for the two cases; tiered times were **31.95 / 33.50 ms**. These are excluded from the run-time column and include the respective persistence/indexing work, not model generation.

### Admission failure isolated without inference

A separate host-only replay reproduced the tiered rejection with **zero model calls**:

| Point | Prompt estimate | Resident tool-response units | Request headroom |
|---|---:|---:|---:|
| After ordinary capacity offload | 40,478 | 38,342 | 16,884 |
| After admission's forced offload | 22,106 | 20,180 | 35,256 |

The resident cap is **8,000**. Before the correction, `Retrieval.begin_batch` observed the oversized resident set and asked for a forced offload; `Session.offload` still honored the **20,000** recent-history preference. That left more than 8,000 units of historical tool bodies live even though ample request headroom existed, so the ledger could not reserve even a minimum status. This identified an imported-history/resume admission limitation; it did not establish that ordinary native sessions accumulated the same invalid resident state. No agent code or limits were changed during these baseline trials.

### Grading correction

The initial grader incorrectly rejected the original repair runs because `python3 verify.py --strict; echo \"EXIT=$?\"` reports shell exit zero while correctly capturing the verification child's exit one. The rubric was corrected to accept the observed `EXIT=1` together with the actual failed-test output. Regrading recorded observations yielded the two passes above; a negative smoke with the same answer but no tool observations remained a failure. No model trial was rerun or discarded for this correction. Existing fixture-integrity observations were preserved.

## Resident-capacity correction

The new variant now handles resident pressure independently from request-window pressure. It evicts only
enough oldest **completed tool exchanges**, using the ledger's exact envelope estimator, to leave room for
the next batch's minimum statuses and outstanding reservations. This applies to unannotated imported
results as well as normal retrieval. Recency is not protection; original user/system/developer text and
entire batches with an unanswered sibling remain protected. Raw originals stay in the cold store.
Call, turn, resident, output, and recency settings were not increased.

The same host-only fixture now admits a real cold-source search with **zero model calls**:

| Point | Resident tool-response units | Other observation |
|---|---:|---|
| Before resident admission | 38,342 | Same oversized imported history |
| After selective release | 6,054 | Minimum status reservation 34; prompt estimate 7,819 |
| After the search result | 6,943 | Turn spend 889; exact approved rollback SHA recovered |

The resident cap remains **8,000**. Regression coverage proves a failing-before/passing-after real file
read from an overloaded history, preserved original goal, exact cold originals, durable restart
projection, and rejection without dropping a batch containing an unanswered sibling. The complete
suite passed **305 tests**, with five SWIG deprecation warnings. A rebuilt wheel also passed an actual
fresh-artifact isolated installation smoke: resident **860 → 430** under a **500** cap, with all
originals preserved.

### Unchanged live-workload rerun

The same corpora, questions, model/window, limits, tool allowlists, grading, two repetitions, and
sequential order were rerun after the correction. The original package was not edited. The eight
new trials' raw results were removed on 2026-11-02; the values below are historical.

| Challenge | Variant | Passed | Time to return/stop (s) | With idle/close (s) | All-request input tokens | All-request output tokens | Model calls | Client peak RSS (MiB) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Buried revision | Original control | 0/2 | 67.67 | 67.67 | 190,996 | 1,235 | 9 | 41.64 |
| Buried revision | Corrected tiered | 0/2 | 85.64 | 96.40 | 108,249 | 957 | 9 | 47.80 |
| Failed repair | Original control | 0/2 | 62.76 | 62.76 | 184,452 | 1,117.5 | 9 | 41.39 |
| Failed repair | Corrected tiered | 0/2 | 85.61 | 95.71 | 107,237.5 | 887 | 9 | 48.05 |

**The capacity defect is corrected, but the challenge tasks still do not pass.** The four corrected
tiered runs had **zero `CapacityConflict` exceptions**, executed eight to ten tools per run, and
retained unchanged evidence/code fixtures. Instead, every run of both variants reached the eight-call
foreground limit while still requesting tools, so none returned a final answer or final-answer TTFT.
Observed traces repeatedly search already-found evidence; this is a separate termination/tool-selection
problem. The control repair case varied from 2/2 in the earlier experiment to 0/2 here despite the
original source remaining unchanged, reinforcing the limits of a two-repetition quality comparison.

Each tiered run also made one real curation request, taking roughly eight to nine seconds, included in
the total token/call columns and idle/close time. All four jobs failed host validation: the revision
case produced invalid `source_ids`, and the repair case failed the identical-error-fingerprint check.
These are independent semantic-curation failures, not resident-capacity failures. The checks were not
relaxed to admit unsupported cards. No active-curation benefit or end-to-end speed improvement is
established; the corrected variant is slower on these unsuccessful runs despite fewer input tokens.

## Wrap-up and duplicate-result rerun

The tiered variant then gained two loop changes; the original package was not edited. A retrieval-class
result identical to a tool result still in the live view is admitted as a `duplicate_of` reference (the
original stays journaled), and search hits already live are returned as `in_context` IDs. After two
consecutive batches without new information a transient note asks the model to answer or change approach,
and the last call under `max_turns` is offered no tools. The same corpora, model/window
(`huihui-v2-swift-qwen3.8-flash-next-iq3_s`, 62,536), limits, grading, two repetitions and sequential
order were rerun (raw results removed 2026-11-02).

| Challenge | Variant | Passed | Time to return/stop (s) | With idle/close (s) | Foreground input tokens | Model calls | Client peak RSS (MiB) |
|---|---|---:|---:|---:|---:|---:|---:|
| Buried revision | Original control | 0/2 | 67.89 | 67.89 | 183,779.5 | 9 | 43.05 |
| Buried revision | Tiered + wrap-up | **2/2** | 104.21 | 110.61 | 101,854.5 | 9 | 49.02 |
| Failed repair | Original control | 0/2 | 65.25 | 65.25 | 174,678.5 | 9 | 41.51 |
| Failed repair | Tiered + wrap-up | 0/2 | 88.08 | 98.20 | 101,481 | 9 | 49.60 |

- Every tiered run returned a final answer (median first content 102.68 s / 85.74 s); every original run
  again stopped at the eight-call limit without one. The forced tool-free last call produced the answers.
- Both buried-revision tiered runs recovered every required field, including the exact rollback SHA.
- Failed repair, trial 1: every answer field was correct and the agent really ran
  `python3 verify.py --strict; echo "EXIT_CODE=$?"` (observed `FAILED test_reject_zero_marker`, `EXIT_CODE=1`).
  The rubric accepts only `[exit code 1]` or `EXIT=1`, so `live_verification` failed. The rubric was not
  changed after the fact; this is recorded as a fail.
- Failed repair, trial 2: `distinct_error_path` carried an explanatory suffix instead of the bare path.
- The harness records raw `tool_end` results, before admission, so it cannot show which results were
  collapsed to `duplicate_of`. Tiered runs repeated an identical raw result 0–2 times.
- Curation: one request per tiered run, all rejected by host validation again (`source_ids`, identical
  error fingerprint). No curation benefit is established.
- Tiered foreground input was 44.6% / 41.9% lower; answer time was 53.5% / 35.0% longer. The tiered variant
  was already slower before this change (85.6 s vs 67.7 s), so the cause is not isolated here.

## Interpretation limits

Two repetitions per variant/case are a small paired smoke comparison, not a statistically stable benchmark or a p95 estimate. The wrap-up change is a loop policy, not a memory mechanism: the same forced tool-free last call would likely change the original variant's results as well. Histories are synthetic, the model is local/text-only, and no scanned-PDF or vision workload is included. Model-server caches, thermal state, and unrelated server activity are not controlled. Background work receives a measured idle opportunity but is not given a subsequent user turn in which its cards could help; its cost is visible, while long-horizon benefit remains unmeasured. Results must not be generalized to all task quality, latency, memory growth, or large-session scaling.
