# Core Loops

## Loop 1: Discover

Output:

- `data-cooked/source-index.md`
- `analysis/discovery.md`

Actions:

- Inventory raw sources.
- Classify type, size, source, likely domain, and parsing difficulty.
- Identify duplicates, noisy material, generated material, scans, images, URLs, and source gaps.
- Assign stable `source-XXX` IDs.

Discovery must answer:

- What is in the input?
- What appears important?
- What appears noisy or duplicate?
- What requires OCR, table extraction, URL fetching, or manual review?
- What source IDs will be used?

## Loop 2: Define Cook Spec

Output:

- `analysis/parse-plan.md`

For each source specify:

```text
source_id
raw_path
detected_type
parser_strategy
output_md_path
expected_content
known_risks
```

Parser strategies include:

- PDF text extraction or OCR fallback.
- DOCX to Markdown.
- XLSX/XLSM sheet summaries and extracted tables.
- CSV profile plus Markdown table.
- HTML/article extraction.
- URL fetch plus snapshot.
- XML/JSON structural summary.
- Image OCR or visual description.
- Plain text normalization.

## Loop 3: Cook

Output:

- `data-cooked/source-XXX.md`

Rules:

- Include provenance in every cooked file.
- Preserve headings, tables, names, dates, numbers, workflows, and decision language.
- Do not perform deep interpretation yet.
- Mark parser uncertainty clearly.

Suggested header:

```md
# Cooked Source: source-001

- Raw file: `data-raw/example.pdf`
- Type: PDF
- Parser: pdf-text-extract
- Parsed at: YYYY-MM-DD
- Confidence: high | medium | low
- Notes: OCR used / tables may be imperfect / images not parsed

---
```

## Loop 4: Analyze

Outputs:

- `analysis/flow.md`
- `analysis/dependency.md`
- `analysis/terminology.md`
- `analysis/core-thought-model.md`
- `analysis/evidence-map.md`
- `analysis/boundaries-and-invalidation.md`
- `analysis/open-questions.md`

Rules:

- Derive analysis from `data-cooked/`.
- Major claims must cite source IDs.
- Flow comes before terminology cleanup.
- Preserve contradictions.
- Mark weak evidence explicitly.

## Loop 5: Knowledge

Outputs:

- `knowledge/read-order.md`
- `knowledge/executive-summary.md`
- `knowledge/big-picture.md`
- `knowledge/domain-reference.md`
- `knowledge/workflow-reference.md`
- `knowledge/system-model.md`
- `knowledge/activation-adherence-scorecard.md` for agent/harness topics
- Embedded ASCII-style stacking diagrams in Markdown (Mermaid is forbidden)

Rules:

- Reusable knowledge should be concise, source-grounded, operational, and heavily compressed/deduplicated while maintaining high coverage. Cross-reference single canonical explanations rather than repeating details.
- Distinguish evidence, inference, recommendation, and open question.
- Include boundaries and invalidation criteria for practical recommendations.
- Overall workflow diagrams must use an ASCII stacking flow layout with the core module in the center, input data contracts on the left, and output data contracts on the right:
  ```text
  [Input Data Contract]  -->  [Core Module]  -->  [Output Data Contract]
  [Input Data Contract]  -->  [Core Module]  -->  [Output Data Contract]
  ```

## Loop 6: Feedback-Driven Skill Evolution

Use when the user critiques or evaluates the output.

Outputs:

- `analysis/feedback-log.md`
- `analysis/iq-training-evaluation.md`
- `analysis/skill-evolution-ledger.md` when the skill itself changes

Actions:

- Capture feedback.
- Classify error pattern.
- Patch current output first.
- Patch the skill only when feedback generalizes.
- Record what changed and why.

