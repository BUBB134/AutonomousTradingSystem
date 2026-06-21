---
name: strategy-experiment
description: Design or implement deterministic research-only strategy experiments using versioned inputs, explicit time semantics, recorded seeds, immutable manifests, and reproducible outputs. Use for strategy hypotheses, synthetic or approved historical backtests, experiment manifests, benchmark comparisons, or research result generation that must remain separate from independent validation and paper execution.
---

# Strategy Experiment

## Define the experiment before running it

1. Read `../../../TRADING_MANDATE.md`, `../../../AGENTS.md`,
   `../../../ARCHITECTURE.md`, `../../../QUALITY.md`, the active ticket, and relevant nested
   `AGENTS.md` files.
2. State the falsifiable hypothesis, decision rule, universe, frequency, information cutoff,
   timezone, input versions, configuration version, code version, seed, benchmarks, costs, and
   expected artifacts.
3. Use only synthetic data or explicitly approved, versioned historical data. Do not add runtime
   downloads, market-data SDKs, broker access, credentials, or live-capital paths.

## Preserve chronology and reproducibility

1. Make information availability explicit for every decision timestamp.
2. Prevent future observations, revised values, or outcome-derived filters from influencing an
   earlier signal.
3. Inject clocks and randomness; record seeds and material versions.
4. Keep strategy output limited to typed signals. Route any proposed positions through separate
   portfolio and risk interfaces owned by later stages.
5. Write immutable experiment inputs, outputs, and provenance through versioned public contracts.

## Test and report

1. Add deterministic unit, invariance, chronology, and failure-path tests appropriate to the
   experiment.
2. Compare with declared benchmarks and include realistic costs when the ticket supports them.
3. Report negative, inconclusive, and failed results without rewriting prior artifacts.
4. Do not claim independent validation, promotion, or operational approval. Hand immutable
   artifacts to the independent validation workflow.
5. Run `uv run python scripts/validate.py` and document exact reproduction commands.
