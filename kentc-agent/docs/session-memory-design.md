# Foreground compaction with local topic files

This is the design of the `kentc-agent` runtime in `src/kentc_agent/`, the only runtime in this repository.
It compresses older history in the foreground inside the main-agent/tool loop, and stores durable details as
consolidated local Markdown topics. The former single-checkpoint package ("v1") was removed when this
runtime (formerly "v2", `kentc_agent_new_mem`) took over its name; references to v1 below are historical.
There is no hot layer, cold database, background curator, memory-specific tool, or retrieval ledger.

## Compression and recall

1. Before a main-agent request, apply the window/reserve/recent-history policy. `/compact [focus]`
   can force the same operation. Select a boundary that does not split a tool-call/result group.
2. Serialize the old prefix with tool-result prefix truncation and bounded request chunks.
   Ask the summarizer for a short task checkpoint and topic updates. Existing topic slugs are supplied
   so the model can reuse a topic instead of creating duplicates.
3. For every touched existing topic, make a foreground consolidation request containing its **complete**
   previous note and the new facts. Request one replacement Markdown note: preserve exact identifiers,
   sources, uncertainty, still-relevant facts, and explicitly superseded values. New topics need no merge
   call. Untouched notes are carried forward unchanged.
4. Publish the touched notes and an index, then commit the checkpoint and note references to the session
   journal. Only after that commit may the old prefix leave live context.
5. Subsequent main requests contain the short checkpoint, any pinned requirements, current index path, up
   to eight topic names, and recent messages. Note bodies are not automatically injected. The agent uses
   ordinary `read` or `bash` when it needs details; retrieved text returns through the normal tool-result path.

All summarization/consolidation requests use the context-summarization system prefix, so benchmark
usage is attributed to `summary`, not foreground answer generation. There is no asynchronous work.
Parsing sub-agents use their existing bounded isolated context and never create topic notes.
Workflow tool restrictions remain exact: no hidden retrieval tool is added to an allowlist.

## Pinned requirements

Exact user text can be pinned for a chat session (`--requirement TEXT`, repeatable; chat `/require <text>`,
`/requirements`, `/unrequire <number>`; `/new` starts without pins). Pins enter every request verbatim right
after the checkpoint, independent of the model-written summary, so compaction cannot paraphrase them away.
`Session.set_requirement` appends a journal `requirement` record; replay restores active pins on resume.
Active pins are limited to 4,000 characters in total. Workflows reject `--requirement`; workflow requirements
belong in the workflow instructions. A pin guarantees the text is present, not that the model obeys it.
Tests: `tests/test_requirements_and_file_writes.py`.

## Evidence in checkpoints and topics

The checkpoint format (`context/compaction.py` `FORMAT`) has Goal / Constraints / Progress / Key Decisions /
Evidence / Next Steps / Critical Context. Evidence lists verified observations with their status
(verified/unverified) and exact source path/range, tool call, or record ID. Topic extraction and merge prompts
(`EXTRACT`, `MERGE`) keep the same source and verification status on each fact; claims and hypotheses are not
evidence. The fields are model-written and can still be wrong or missing.

## Tool-call arguments

Big-result routing shrinks what tools return; it does not touch what the model sends. After a turn's results
are persisted (`executor._shorten_arguments`), every string argument of a successful call that is longer than
`big_args_tokens` (default 500) is replaced in live context by its first 200 characters, an omission marker
(character count, SHA-256 prefix, session journal path) and its last 400 characters. The tail is kept so a
file written in parts can continue where it stopped. A call that failed keeps its arguments, so the model can
correct them. For bash, "failed" also covers a non-zero exit, and a routed bash result counts as failed too
because its exit status is no longer visible. The system prompt tells the model that the marked calls ran
with the full text, to read the file for current content, and never to copy a marker.

The journal is append-only: the message record keeps the original arguments. A following
`{"type": "arguments", "id": <message id>, "arguments": {<tool call id>: <shortened JSON>}}` record
is validated (an existing assistant message, existing call ids, JSON objects) before it is written, and replay
applies it. The server's usage for that message covered the original text, so it is dropped and the shortened
message is estimated. Compaction therefore serializes the shortened view. Readers that need the exact
original, such as the Breezeman transcript, read the message records.

## Incremental file writes

While the core `write` and `edit` tools are offered to the main agent, the system prompt asks for long files as
a skeleton with unique section markers, filled one section per turn with `edit`. Each request carries a
per-turn target, `FILE_CHUNK_HINT` in `agent/loop.py`: at most `max_tokens / 4` estimated tokens of new text.
The hint is sent with the request and never stored. A `write`/`edit` call cut off at `max_output_tokens` or
with unparsable arguments is discarded; the clean retry continues from the accepted conversation (sections
already saved stay), appends `FILE_RETRY`, and halves the target (`/8`, then `/16`) until the turn succeeds.
Tests: `tests/test_requirements_and_file_writes.py`.

## Preflight

Before sending (`Agent._call`), the whole request is estimated: system prompt, tool schemas, context and
per-request notices. Without room for a reply of at least 512 tokens after the safety margin, the agent
compacts once; if the request still does not fit, it fails locally with `ContextOverflow` instead of reaching
the server. Test: `test_request_without_reply_room_is_rejected_before_the_network_call`.

## Local files and commit boundary

```text
<workspace>/.kentc-agent/
  sessions/<session>.jsonl
  memory/<session-id>/
    <generation>/
      launch.md
      operations.md
      _index.md
    <later-generation>/
      launch.md
      _index.md
```

A generation name is a random 24-character hexadecimal identifier. Topic slugs are lowercase
alphanumeric words separated by hyphens, at most 64 characters. The reserved index filename
`_index.md` cannot collide with a valid topic slug. Index entries advertise absolute note paths;
unchanged entries may point into older generations.

Notes and indexes are immutable published snapshots, not user-editable source documents.
Each journal compaction record contains the checkpoint, first kept message ID, topic root,
current index record, and topic records with relative paths and SHA-256 digests.
Files and containing directories are flushed before the journal append is flushed. Live state
changes only after the append succeeds. A failed publication can leave unreferenced generation
files; they are not promoted on restart. There is no automatic generation garbage collection.
The transcript remains append-only, so compression reduces prompt history, not journal disk usage.

Restart replays the journal, restores the checkpoint/recent prefix, and verifies the committed
files before accepting the restored view. Missing, edited, unsafe, or incompatible records fail
explicitly rather than silently discarding history. The topic root must agree with the session
and remain inside the bound workspace state directory. Keep the workspace and committed paths
in place; moving a saved workspace is not a supported path-migration operation.

`--no-session` disables the conversation journal, **not** local topic-file creation during compression.
Without a journal, those files are not automatically restored as a resumable conversation.

## Budgets and failure behavior

- Trigger: context exceeds `window - reserve_tokens`; reserve is capped at a quarter of the window.
- Recent-history target: `keep_recent_tokens`, capped at a third of the window and adjusted for learned
  token density. Tool-call groups remain intact.
- Checkpoints use the section structure above and a short word budget capped at 600 words.
- Each compression request has an explicit output budget, tokenizer-density estimate, and input headroom.
  Empty or output-truncated replies get one bounded retry without reasoning.
- Consolidation never silently truncates the old note. If the complete request cannot fit, compression
  fails and live history remains available. A large single topic can therefore stop further compression;
  the design does not promise unlimited topic/session scaling.
- Invalid JSON, duplicate fields, unsafe slugs, invalid notes, missing files, and failed persistence do not
  advance the live checkpoint. The runtime does not apply the removed v1 destructive tool-result-shortening
  fallback after a failed topic compression. A later foreground request may still fail for lack of context room.

Consolidation is model-generated, not a formal guarantee of factual retention. A valid response can
still omit or misinterpret facts. Source documents and stored large-result artifacts remain the
verification path. As in the removed v1 serialization, the 2,000-character tool-result prefix can omit buried evidence;
this implementation does not claim to fix that limitation.

Checkpoints and note bodies are historical data, not system instructions. Persona, explicit instructions,
and current workspace policies remain in the main system context. No model-generated note can change
host tool authorization or filesystem containment.

## Configuration and upgrade

The runtime uses the ordinary model, reserve, recent-history, output, tool, and workflow settings, plus its
persona option. It uses `.kentc-agent/`, `~/.config/kentc-agent/config.yaml`, and `KENTC_AGENT_`
environment settings. There are no `memory_*` knobs or curation flags.
Remove obsolete settings when upgrading from the former tiered implementation.

Use `/compact [focus]`, `/tokens`, and ordinary tools. `/offload`, `/memory`, intrinsic memory tools,
SQLite sidecars, curator threads, and model-gate APIs have been removed. Existing v1-format journals
can be replayed. Former tiered-memory journals are rejected read-only; start a fresh session instead
of expecting a compatibility shim or automatic migration.

The benchmark harnesses (`examples/compare_memory.py`, `examples/str_benchmark.py`) run this single runtime;
the former `original`/`topics` variants no longer exist. Archived A/B results in `docs/compare-run-*/`
compare the removed v1 with this runtime's predecessor and are historical. Results labelled `tiered`
describe the removed tiered implementation and provide no performance or quality evidence for the
current topic-file runtime.
