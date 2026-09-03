# Optional Preparation Accelerators

Accelerators reduce repeated source reading; they do not determine the final deliverable and do not replace evidence verification.

## Graphify

Use Graphify as an optional relationship extractor when all of these are true:

- the `graphify` command is already installed;
- the input is a repository or relationship-heavy mixed folder;
- cross-file calls, imports, dependencies, or code-to-document links matter to the objective;
- the generated graph can be checked against source paths before use.

Prefer native distillation for small inputs, linear documents, or tasks where relationships are not central. Never install Graphify automatically. Code-only extraction can remain local; semantic extraction over documents may use a configured model provider, so preserve the user's data-handling constraints.

Run the adapter in dry-run mode first:

```bash
python3 skills/knowledge-distill/scripts/graphify_accelerator.py task-config.resolved.json
```

Execution requires an explicit flag:

```bash
python3 skills/knowledge-distill/scripts/graphify_accelerator.py task-config.resolved.json --execute
```

The graph is supporting evidence. Keep `EXTRACTED`, `INFERRED`, and ambiguous relationships distinguishable, and verify major implementation claims against their source locations.

## Semantic retrieval

Use semantic retrieval when the distilled corpus is still too large for direct consumption or when audience questions use terminology different from the sources. Retrieve candidates with semantic and lexical signals, apply metadata constraints, and then expand structural neighbors when a graph exists.

Semantic retrieval selects context; it does not create reliable relationships. Preserve stable source IDs and record why each retrieved item was included.
