# Latest Derivative Benchmark Run

This folder contains the latest Docker derivative-generation benchmark artifacts. The original run sampled 10,000 conditioned candidate SMILES per model; the stored `.smi` files have been post-filtered to canonical RDKit-valid unique derivatives, excluding molecules identical to the seed structures.

Seed file:

- `seeds/reference_randomized.smi`
- 1,888 unique seed variants
- 30,417 randomized RDKit attempts
- stop reason: `stagnation_limit`
- benchmark expansion: `samples_per_seed=6`, clipped to 10,000 candidate inputs per model

Key files:

| Path | Contents |
| --- | --- |
| `benchmark_summary.csv` | One row per model with speed and molecular metrics. |
| `generation_summary.csv` | Candidate count, accepted output count, seed expansion, timing, and batch size. |
| `throughput_trace.csv` | Output and candidate throughput summary. |
| `benchmark_metadata.json` | Runtime, CUDA, GPU, and command settings. |
| `seeds/reference_randomized.json` | Randomized seed generation metadata. |
| `figures/` | GitHub-ready PNG charts. |

Summary:

| Model | Candidates | Output | Output SMILES/s | Candidate SMILES/s | QED mean | SA mean | Ro5 pass |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `base-isomeric` | 10,000 | 1,637 | 272 | 1,662 | 0.6329 | 3.0501 | 0.9188 |
| `base-nonisomeric` | 10,000 | 1,235 | 244 | 1,972 | 0.6744 | 3.1332 | 0.9352 |
| `rl-isomeric` | 10,000 | 1,135 | 270 | 2,376 | 0.7631 | 2.9723 | 1.0000 |
| `rl-nonisomeric` | 10,000 | 858 | 203 | 2,364 | 0.7773 | 3.0010 | 1.0000 |
