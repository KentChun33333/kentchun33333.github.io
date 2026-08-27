# Topology: Code Repository Input

Use this flow when the input is a code repo, package, product codebase, agent framework, or implementation folder.

## Reasoning Topology

```text
entrypoints
  -> module map
  -> runtime workflow
  -> data/control flow
  -> dependencies/contracts
  -> failure modes
  -> extension points
  -> reusable implementation knowledge
```

## Required Analysis Emphasis

- Entrypoints: CLI, API, app boot, jobs, tests, agents, scripts.
- Module map: key packages, ownership boundaries, responsibilities.
- Runtime workflow: what runs first, what calls what, what state changes.
- Data model: schemas, events, configs, prompts, tools, memory, artifacts.
- External dependencies: services, libraries, APIs, file formats.
- Contracts: function signatures, interface expectations, env vars, config keys.
- Tests and validation: how behavior is verified.
- Failure modes: errors, retries, missing config, security risks, hidden coupling.

## Output Preferences

Add or emphasize:

- `knowledge/module-map.md`
- `knowledge/runtime-workflow.md`
- `knowledge/contracts-reference.md`
- `knowledge/extension-guide.md`
- Pseudocode or small runnable examples when useful.

## Boundary Checks

- Do not infer behavior from filenames alone.
- Distinguish implemented behavior from planned behavior in docs.
- Mark untested code paths.
- Preserve uncertainty when tests or runtime cannot be run.

## Invalidation Tests

- A workflow claim is invalidated if entrypoints or tests show another path.
- An architecture claim is weak if only README docs support it and code contradicts it.
- A dependency claim is weak if it is unused or dev-only.

