# STR long-task benchmark

`examples/str_benchmark.py` runs the `kentc_agent` runtime (foreground compression with consolidated local
topic Markdown files) on one long, realistic task under a limited context window: review a synthetic case file
for 30 to 50 customers and deliver an internal STR-style HTML report in Singapore financial crime compliance
house style.

It replaces the weaknesses of the [memory comparison](memory-comparison.md): no seeded history, no single
evidence file that bypasses memory, no hidden output formats, no all-or-nothing pass, and a task that needs
many documents rather than one lookup.

## Run

```sh
uv run --no-sync python examples/str_benchmark.py --self-check                    # grader check, no model
uv run --no-sync python examples/str_benchmark.py --output docs/str-benchmark-topics.json \
  --repeats 1 --persons 40 --max-turns 80
```

Options: `--persons 30..50`, `--seed`, `--max-turns`, `--repeats`, `--timeout` (seconds per trial; 0 = no
limit). There is no variant option: the former baseline variant (v1, `original`) no longer exists, so every
trial runs the current runtime. Each trial runs in a fresh process with an empty session in a temporary
workspace, with the same case, prompt, tools (`read`, `bash`, `write`, `edit`), temperature 0, reasoning
effort `none` and a 4,096-token reply limit. Notes are recalled through the same ordinary tools; there are no
intrinsic memory tools or background curation.
Each produced `report/` is copied to `<output>.artifacts/trial-<n>/`; open `index.html` to see the website.

## The case

Generated deterministically from `--seed`. All people, companies, trusts, identifiers and accounts are
fictitious.

| Folder | Content |
|---|---|
| `profiles/` | One KYC profile per customer, rotating Markdown, Word, HTML and JSON |
| `rm_notes/` | RM call notes (`.eml`) for about a third of customers, including every planted note |
| `registry/` | Company registry extracts (directors, shareholders, registered address, bank account) |
| `trusts/` | Two trust deed summaries |
| `statements/` | `<holder ID>_statement.csv`, six months, customers, companies and trusts |
| `media/` | Two media hits |

At 40 customers the case has 121 files and about 242,000 characters of readable text, several times the
usable window of the 62,536-token local deployment. Reading everything forces foreground compaction and topic consolidation.

### Planted network

```text
 3 money mules ── structured cash deposits (SGD 18,200-19,950, five each) ──┐
   (student employed by C-shell-1, retiree with the key actor's mobile as     │ same or next day
    "alternate contact", rider living at the key actor's address)             ▼
                                         Brightpath Trading Pte. Ltd. ── "consultancy fees" ──► Northwind Advisory Pte. Ltd.
                                         (registered at key actor's address;                    (100% held by the trustee of
                                          nominee director)                                      the Harbour Light Trust)
                                                                                                         │ "capital distribution"
                                                                                                         ▼
                              key actor ◄── "beneficiary distribution" (shown as "M TAN") ── Harbour Light Trust (T01)
                              Marcus Tan Wei Ming                                            beneficiary named by NRIC only
```

Links are hidden: statements show abbreviated names ("BRIGHTPATH TRDG", "M TAN", mule initials) and account
numbers, while holders' account numbers are only in profiles, registry extracts and deeds. The trust names the
beneficiary in a different name order, confirmed only by NRIC.

### Decoys

| Decoy | Tests |
|---|---|
| Marcus Tan Wei Liang | Name-only matching against the key actor (different NRIC and date of birth) |
| Media article on "Marcus Tan, 58" | An allegation that matches neither Marcus Tan by age |
| Lim Family Trust beneficiary | Legitimate trust distributions with documented source of wealth |
| Business owner | Large but documented company flows and dividends |
| Foreign student | Regular family remittances, documented |
| One cash deposit of SGD 19,800.00 | Just under the threshold once, explained by a documented car sale |

## Deliverables and grading

The prompt fixes both deliverables: `report/findings.json` (keys, roles and typology vocabulary given) and
`report/index.html` (section ids, inline SVG network, house style). Grading is deterministic. Each criterion
scores 0 to 1; an axis is the mean of its criteria (key actor counts double); the overall score weights the
axes. Changing any file under `case/` scores 0.

| Axis (weight) | Criteria |
|---|---|
| A. Overall picture (0.25) | persons reviewed; placement total (1% = 1, 10% = 0.5); period start and end (exact = 1, 7 days = 0.5); typology Jaccard; summary names the key actor |
| B. Cross-identification (0.45) | key actor; subjects F1; linked entities F1; roles; decoys not flagged (0 when nothing is flagged); cited evidence paths exist |
| C. Report (0.30) | HTML written; self-contained; six section ids; graph node recall; graph edges; no conclusory words; no tipping-off phrasing; `SGD 1,234.56` amounts; `08 Jun 2026` dates; recommendation mentions STRO; no unknown customer/entity IDs; `findings.json` contract followed |

Reasoning criteria read the findings leniently: an ID may be written as a string or as an object with `"id"`,
and the period as the asked object or a string with two dates. Following the stated contract exactly is scored
once, in `findings_contract`, so a format slip costs format points instead of zeroing the analysis. A section
runs from the element carrying its id to the next section id in document order, so both
`<section id="network">` and `<h2 id="network">` followed by the content are accepted.

`--self-check` grades three reports without a model: none (0.0), a reference built from the ground truth (1.0)
and a naive one that flags every decoy, names a decoy as key actor and uses conclusory and tipping-off wording
(0.74: B 0.52, C 0.83).

Process measures are recorded beside the score: model calls and tokens by kind (foreground and summary,
including topic consolidation), answer/close wall time, compactions, tool counts and errors, repeated reads,
and approximate file coverage (files named in `read` paths or `bash` commands; globs are not expanded).

## Historical results: removed v1 vs former tiered-memory v2

All results below compare the removed v1 package with the removed tiered implementation; neither exists
any more. Saved numbers and artifacts are unchanged. No live-model quality or performance result for the
current topic-file runtime is claimed here; the recorded v1 vs topic-file v2 A/B runs are in
[compare-run-4rep-1zpd8yum](compare-run-4rep-1zpd8yum/report.md) and are historical as well.

31 Oct 2026, `huihui-v2-swift-qwen3.8-flash-next-iq3_s`, window 62,536, 40 customers, seed 7, 80 model calls,
two repeats (raw results removed 2026-11-02; numbers below are historical). The saved report was
regraded after the grader changes above; runs without a report are unaffected.

| Variant | Trial | Overall | A | B | C | Wall (s) | Model calls | How it ended |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| v1 | 1 | 0.00 | 0.00 | 0.00 | 0.00 | 534 | 81 (1 summary) | 80 `bash` calls; no file written; stopped at the limit |
| v1 | 2 | **0.81** | 0.67 | 0.87 | 0.83 | 681 | 82 (2 summaries) | Near-complete report; stopped at the limit while still editing |
| v2 | 1 | 0.00 | 0.00 | 0.00 | 0.00 | 32 | 8 | Model wrote a `<tool_call>` block as plain text; accepted as the final answer |
| v2 | 2 | 0.00 | 0.00 | 0.00 | 0.00 | 40 | 10 | Same |

- v1 trial 2 identified the key actor, exactly the five planted subjects, all three linked entities and no
  decoy as a subject, with a 9-node, 8-edge network graph (it also drew the explained decoy P012). It lost
  points on roles (`cash_injector` instead of `money_mule`), the placement total (SGD 305,895.94: it added
  the decoy's explained SGD 19,800.00), the period end (the later
  property payment), extra non-entity items in `linked_entities`, two missing sections (`grounds`,
  `recommendation`) and the findings contract (objects instead of IDs). Before the grader correction the same
  report scored 0.51.
- Both v2 runs, and a separate probe run, ended within ten calls with a tool call emitted as text
  (`<tool_call><function=bash>...`) and accepted as the final answer. v1 did not hit it in 160 calls.
- v1 succeeded once and failed once with no output; v2 has no valid trial.

### Root cause of the v2 text tool calls

A traced reproduction showed calls 1-9 offered `read`/`bash` and returned structured calls; after about
17,900 characters of `bash` output the ledger reached its 6,000-token per-user-turn allowance, the loop
removed `read`, `bash` and `web_search` from the offered tools, and call 10 returned the `bash` call as text
with `finish=stop`. The allowance was charged for workspace reads as well as memory retrieval, so a
single-turn task could read only about 6,000 tokens in total. The model still needed `bash`; the server
returned the undeclared call as text [inference from the trace: server internals not inspected].

Fix (v2 only): only `context_search`/`context_read` are charged to the turn allowance and withdrawn when it is
spent; workspace reads keep the call, resident and headroom limits. A reply containing `<tool_call>` or
`<function=...>` without a structured call is rejected and retried through the existing invalid-output path.

### Rerun after the fix

Same case and settings, five repeats each (raw results removed 2026-11-02).

| Variant | Overall (5 runs) | Wall (s), median | Calls used | Foreground prompt tokens/call | s per call | How runs ended |
|---|---|---:|---:|---:|---:|---|
| v1 | 0, 0, 0, 0, 0 | 474 | 80 of 80 | 28,095 | 4.9 | All stopped at the call limit; 1 to 6 summaries each |
| v2 | 0, 0, 0, 0, 0 | 1,354 | 80 of 80 | 14,965 | 16.8 | On the last call, which offers no tools: three text tool calls and one over-long reply ended in `IncompleteReply`; one text answer |

- The text-tool-call defect no longer ends v2 early: every v2 run used all 80 calls (291 to 1,525 s, against
  32 to 40 s before).
- No run of either variant wrote `report/`. Both spent their calls on `bash` exploration (60 to 91 `bash`
  calls per run); one v1 run called `write`/`edit` five times without leaving `report/` at grading time. With this
  model, 80 calls are not enough to finish the task; the earlier 0.81 run was the exception.
- v2 holds about half the prompt per call (resident cap and eviction) but each call takes 3.4 times as long:
  0.84 s per 1,000 prompt tokens against 0.17 s for v1. The pattern fits prompt-cache misses: v1 appends to an
  unchanged prefix between compactions, while v2's eviction rewrites earlier history [inference: server
  cache statistics were not recorded]. Prompt tokens per call and seconds per call are medians over runs.
- On the final call v2 offers no tools; when the deliverables are files, the model keeps trying to call tools,
  so the forced final answer did not help this task.

### 1,000-call runs

The harness now routes requests through a pass-through proxy that records the server's
`cached_tokens`/prefill time per request. v2 changes before these runs: resident eviction leaves room for full
call-capped responses and releases a block down to a low watermark; the last call keeps `write`/`edit`.
One run each (raw results removed 2026-11-02).

| Run | Overall | Calls | Wall | Cache hits | How it ended |
|---|---:|---:|---:|---:|---|
| v1 | 0.56 | 1,000 (+17 summaries) | 6,341 s | 97% | Call limit; section fragments in `_s1-3.html` never assembled into `index.html`; flagged the explained-deposit decoy instead of the nominee director |
| v2, first attempt | - | 798 when stopped | - | - | The same 18-character `grep` result (an account number that does not exist) 353 times in a row |
| v2, repeat guard | 0.00 | 158 | 660 s | 87% | Replied "Understood - I have enough evidence. Writing the deliverables now." with no tool call |
| v2, reworded note | 0.00 | 200 | 1,617 s | 50% | Stopped as stalled; no `write`/`edit` call |

- The 353-call loop came from duplicate detection: a repeat counted as stale only when a reference was
  shorter than the result, so tiny identical results never triggered the stall note. Now any result identical
  to one in context is stale, a lookup that returned the same result three times in a user turn is refused
  with a structured result, and eight stale batches in a row stop the run.
- The stall note asked for "the final answer"; with file deliverables the model answered in text. It now
  says to call `write`/`edit` when the task asks for files.
- With these guards v2 no longer spends hundreds of calls repeating itself. Its per-call time fell from
  16.8 s (80-call runs, before the eviction change) to 4.1 s in the 158-call run, close to v1's 4.9 s.
- Neither variant, with this model, reliably moves from analysis to writing the deliverables. One run each
  is anecdotal.

## Limits

- One synthetic case design. A model or agent tuned to it would not show general STR ability.
- The style checks are lexical. They do not judge narrative quality, British spelling or whether each
  inference is labelled.
- Typology and role labels come from fixed lists in the prompt; free-text reasoning is not scored.
- File coverage is approximate.
- Trials on a shared local model run sequentially; server caches and thermal state are not controlled.
  Use several repeats before drawing conclusions.
