# Benchmarks

The benchmark commands generate molecules for each selected model and then compute RDKit metrics.

De novo benchmark:

```bash
igen3 benchmark --count 500000 --output-dir benchmarks/latest
```

Partial benchmark workflow:

```bash
igen3 randomize-smiles \
  --smiles "N1(C(COC)=O)C(C)CN(CC1)C(c1cc(Cl)ccc1)" \
  --max-variants 10000 \
  --stagnation-limit 5000 \
  --output benchmarks/partial_latest/seeds/reference_randomized.smi \
  --metadata-output benchmarks/partial_latest/seeds/reference_randomized.json

igen3 benchmark-partial \
  --seed-file benchmarks/partial_latest/seeds/reference_randomized.smi \
  --count 10000 \
  --output-dir benchmarks/partial_latest
```

Outputs:

| Path | Contents |
| --- | --- |
| `benchmark_summary.csv` | One-row-per-model speed and molecular metric summary. |
| `generation_summary.csv` | Generation timing, batch size, and output path. |
| `throughput_trace.csv` | Per-batch cumulative throughput for line plots. |
| `all_molecule_metrics.csv` | Per-molecule RDKit descriptor table. |
| `smiles/*.smi` | Generated SMILES files. |
| `figures/*.png` | GitHub-ready benchmark charts. |
| `benchmark_metadata.json` | Runtime, CUDA, PyTorch, and benchmark settings. |

Metrics include validity, unique-valid fraction, duplicate fraction, QED, LogP, molecular weight, TPSA, hydrogen bond donors/acceptors, rotatable bonds, Lipinski rule-of-five pass fraction, and SA score when the RDKit SA scorer is available. Figures include throughput, molecular quality, descriptor distributions, throughput trace, and a separate mean SA score chart.
