# Latest De Novo Benchmark Run

This folder contains the latest 500k-per-model Docker de novo benchmark outputs.

Key files:

| Path | Contents |
| --- | --- |
| `benchmark_summary.csv` | One row per model with speed and molecular metrics. |
| `generation_summary.csv` | Generation timing and selected batch sizes. |
| `throughput_trace.csv` | Per-batch cumulative throughput. |
| `benchmark_metadata.json` | Runtime, CUDA, GPU, and command settings. |
| `figures/` | GitHub-ready PNG charts. |

Large generated SMILES files and per-molecule metric CSVs are kept on disk for inspection but ignored by Git.

Summary:

| Model | SMILES/s | Valid | Unique valid | QED mean | SA mean |
| --- | ---: | ---: | ---: | ---: | ---: |
| `base-isomeric` | 1,510 | 0.9778 | 0.9911 | 0.6047 | 3.0693 |
| `base-nonisomeric` | 2,176 | 0.9795 | 0.9884 | 0.6081 | 3.0764 |
| `rl-isomeric` | 2,912 | 0.9826 | 0.9794 | 0.8562 | 2.4062 |
| `rl-nonisomeric` | 3,129 | 0.9827 | 0.9814 | 0.8646 | 2.4314 |
