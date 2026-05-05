# Latest De Novo Benchmark Run

This folder contains the latest Docker de novo benchmark artifacts. The original run sampled 500,000 candidate SMILES per model; the stored `.smi` files have been post-filtered to canonical RDKit-valid unique SMILES.

Key files:

| Path | Contents |
| --- | --- |
| `benchmark_summary.csv` | One row per model with speed and molecular metrics. |
| `generation_summary.csv` | Candidate count, accepted output count, timing, and batch size. |
| `throughput_trace.csv` | Output and candidate throughput summary. |
| `benchmark_metadata.json` | Runtime, CUDA, GPU, and command settings. |
| `figures/` | GitHub-ready PNG charts. |

Large generated SMILES files and per-molecule metric CSVs are kept on disk for inspection but ignored by Git.

Summary:

| Model | Candidates | Output | Output SMILES/s | Candidate SMILES/s | QED mean | SA mean | Ro5 pass |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `base-isomeric` | 500,000 | 484,565 | 1,463 | 1,510 | 0.6045 | 3.0727 | 0.8808 |
| `base-nonisomeric` | 500,000 | 484,057 | 2,107 | 2,176 | 0.6079 | 3.0778 | 0.8808 |
| `rl-isomeric` | 500,000 | 481,140 | 2,802 | 2,912 | 0.8551 | 2.4169 | 0.9996 |
| `rl-nonisomeric` | 500,000 | 482,180 | 3,018 | 3,129 | 0.8636 | 2.4411 | 0.9997 |
