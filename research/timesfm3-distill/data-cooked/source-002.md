# Cooked Source: source-002

- Raw file: `data-raw/sources.md` (arXiv:2310.10688v4 entry)
- Type: Research paper HTML/PDF
- Parser: direct HTML extraction
- Parsed at: 2026-09-02
- Confidence: high
- Notes: This paper describes the original TimesFM, not the TimesFM-3 multivariate architecture.

---

The original TimesFM casts forecasting as patched next-window prediction. Contiguous input patches are mapped by an input residual MLP into transformer tokens with positional encodings. Stacked causal self-attention layers produce contextual token representations; an output residual block maps each representation to a future output patch. Patching shortens the token sequence, while longer output patches reduce autoregressive decoding steps.

Training uses a mixture of real and synthetic time series and masking that exposes varied context lengths. Per-series normalization handles scale variation. The original paper evaluates zero-shot forecasting across held-out datasets and explicitly notes that results are benchmark-specific.

TimesFM-3 inherits the patched decoder lineage but materially changes the runtime with multivariate alternating attention and a single-pass masked-horizon decode. Those TimesFM-3 details come from source-001 and source-003, not this paper.
