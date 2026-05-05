# Latest Partial Benchmark Run

This folder contains the latest 10k-per-model partial-generation benchmark outputs.

Seed file:

- `seeds/reference_randomized.smi`
- 1,888 unique seed variants
- 30,417 randomized RDKit attempts
- stop reason: `stagnation_limit`
- benchmark expansion: `samples_per_seed=6`, clipped to 10,000 inputs per model

Key files:

| Path | Contents |
| --- | --- |
| `benchmark_summary.csv` | One row per model with speed and molecular metrics. |
| `generation_summary.csv` | Generation timing, seed expansion, and selected batch sizes. |
| `throughput_trace.csv` | Per-batch cumulative throughput. |
| `benchmark_metadata.json` | Runtime, CUDA, GPU, and command settings. |
| `seeds/reference_randomized.json` | Randomized seed generation metadata. |
| `figures/` | GitHub-ready PNG charts. |

Summary:

| Model | SMILES/s | Valid | Unique valid | QED mean | SA mean |
| --- | ---: | ---: | ---: | ---: | ---: |
| `base-isomeric` | 1,662 | 0.9964 | 0.1644 | 0.8016 | 2.6067 |
| `base-nonisomeric` | 1,972 | 0.9978 | 0.1239 | 0.8226 | 2.6009 |
| `rl-isomeric` | 2,376 | 0.9887 | 0.1149 | 0.8313 | 2.5769 |
| `rl-nonisomeric` | 2,364 | 0.9859 | 0.0871 | 0.8391 | 2.5534 |
