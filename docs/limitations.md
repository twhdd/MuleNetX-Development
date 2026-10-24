# Known limitations

This document lists what MuleNetX does not do or cannot measure, and the defaults that shape its results. Read it before drawing conclusions from any output. Decision IDs (DEC-nn) are in SRS §1.6; open questions (OQ-nn) are in [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md).

## The data: PaySim

- **The labels mark transactions, not people.** PaySim is synthetic. Its labels say which transactions are fraud. It has no authoritative mule-account labels and no ring ground truth.
- **What evaluation can and cannot measure.**
  - Account-level metrics use a derived label: an account with any fraud-labelled transaction in the window.
  - "Reference rings" are the weakly connected components of the fraud-transaction subgraph that have at least 3 positive accounts (§28.7). This is a construction, not ground truth.
  - Metrics that need labels PaySim lacks are reported as `NOT_MEASURABLE` with the reason, never as zero. Examples are mule-account identity and ring identity ground truth.
  - Every evaluation report carries the PaySim limitation statement.
- **Few multi-hop chains.** Most PaySim accounts have a single transaction, so multi-hop chains are rare (DEC-02). Ring, motif and intervention behaviour is therefore demonstrated on deterministic fixtures and on the synthetic fixture used by `make demo`, which injects a dense cluster. Results on real PaySim may contain few or no potential fraud ring candidates. That is an honest result, not a fault.
- **No synthetic injection.** The §7.10 synthetic pattern injection is not built. It is disabled by default in the SRS. The `is_synthetic_injection` flag and the `SYNTHETIC DATA` label exist but are never set by this build (OQ-71).

## Modelling defaults (DEC-01 … DEC-05)

| ID | Default |
|---|---|
| DEC-01 | Acceptance runs on the PaySim reference slice, at most 1,000,000 rows. Analytics run in-process with NetworkX. The Neo4j GDS benchmark tier is not built. |
| DEC-02 | Profiling runs before analytics, and injection is off (see above). |
| DEC-03 | Under the `RISK_FEATURES_UNAVAILABLE` regime, features F19, F31, F33, F36 and F37 are unavailable everywhere, and rules R03–R05 never fire. |
| DEC-04 | One dataset is active at a time. Earlier contexts remain readable through lineage parameters. |
| DEC-05 | The model does retrospective detection: did activity in the observation window carry a fraud label? It is not a forecast. |

These defaults await Partha's confirmation (SRS §1.6, G-01 … G-04).

## Scores and signals

- **Risk scores are analytical signals, not determinations.** SHAP explains the ML component only, which is about half of the pre-propagation score.
- **Rings are candidates.** Community membership is not proof of a ring. A potential fraud ring candidate is a prompt for investigation.
- **Exhaustive enumeration can be capped.** Ring-scope and baseline path enumeration stop at `analytic_max_paths` (10,000). When that happens:
  - the affected features and intervention metrics are marked `LOWER_BOUND_TRUNCATED`;
  - `metrics_are_lower_bounds` is set.

  Merchant hubs in PaySim-like data make the cap easy to reach.
- **Interventions are counterfactual.** Each analysis removes candidates from a frozen baseline graph. It does not model how the network would adapt.
- **The network-risk counterexample differs from the SRS.** It uses the normative formula. Removing account A gives 0.4390244, not the 0.40 printed in AT-INT-09 (OQ-80).

## Copilot

The copilot is optional and advisory (§21).

- **Hardware.**
  - The default `qwen2.5:7b-instruct` needs about 8 GiB of memory in the Docker VM.
  - On a 4 GiB VM with CPU only, the 1.5B model takes minutes per answer, far beyond the 20 s timeout. The copilot then reports `COPILOT_UNAVAILABLE`.
  - In the one live run with a reduced context window, the small model's answer was rejected by validation (OQ-85).
  - A grounded answer from a real model has not been observed on the build host.
- **Validation.** An answer is discarded when it:
  - cites unknown references;
  - states uncited facts or signals;
  - uses deny-listed wording;
  - exceeds 1,024 output tokens.

  The discarded text is never shown.
- **Capacity.** Answers are limited to one generation at a time and six questions per user per minute.

## Operations and performance

- **AT-OPS-05 latency targets are unverified.** They were not verified on the reference hardware (8 vCPU / 32 GiB) with the PaySim reference slice, because the PaySim file and that hardware were unavailable. Measurements on the synthetic dataset met the targets; see [benchmark.md](benchmark.md). The Phase 3 gate stays open on this (OQ-72).
- **Ring evidence is recomputed on each read.** The cache holds the last two contexts. The first request for a large ring can be slow (OQ-78).
- **Sign-out on reload.** The dashboard keeps its session in tab memory (§20.2), so reloading the page signs the user out.
