---
language:
- en
task_categories:
- text-generation
pretty_name: R2E-Gym-Subset-Verified
tags:
- software-engineering
- code
- swe
- rl
---

# R2E-Gym-Subset-Verified

[![GitHub](https://img.shields.io/badge/research--environments-r2e__gym__v1-181717?logo=github)](https://github.com/PrimeIntellect-ai/research-environments/tree/main/environments/swe/r2e_gym_v1)

Gold-patch-validated subset of
[`R2E-Gym/R2E-Gym-Subset`](https://huggingface.co/datasets/R2E-Gym/R2E-Gym-Subset)
([paper](https://arxiv.org/abs/2504.07164)). The `train` split contains
**4,522 / 4,578 rows (98.78%)** verified scoreable end-to-end: apply the gold patch, run the
upstream `/testbed/run_tests.sh` baked into the row's image, check the parsed outcomes against
`expected_output_json`.

## Changes vs upstream

* **Validation-only subset** — our passes, run in fresh sandboxes per row: one full pass at
  concurrency 200, then a **10× retry pass** over failures to separate flaky from
  deterministically broken.
* **Drop criterion**: a row lands in the `dropped` split iff gold validation fails on all 10
  retries (0/10). Flaky rows (≥1/10) stay in `train` since they recover during normal
  training/eval.
* The **56 drops** are dominated by network/timing-sensitive tests (`aiohttp` + `tornado`
  account for 39) and dataset drift (tests now passing that `expected_output_json` marks
  failed). `metadata/filtered_drops.json` lists every dropped `commit_hash` with its failure
  reason.
* Schema and row content are otherwise unchanged.

Upstream declares no dataset license; we mirror that and declare none. The data derives from public GitHub repositories under their own licenses; the R2E-Gym project code is Apache-2.0.

## Splits

| Split | Rows |
|---|---:|
| `train` | 4,522 |
| `dropped` | 56 |

## How to use

Install the [`r2e_gym_v1`](https://github.com/PrimeIntellect-ai/research-environments/tree/main/environments/swe/r2e_gym_v1) taskset from
[research-environments](https://github.com/PrimeIntellect-ai/research-environments), then run it
end-to-end with [verifiers](https://github.com/PrimeIntellect-ai/verifiers):

```bash
uv pip install --prerelease=allow "git+https://github.com/PrimeIntellect-ai/research-environments.git#subdirectory=environments/swe/r2e_gym_v1"
uv run eval --taskset.id r2e_gym_v1 -m <your-model> -n 100 -r 4
```


## Original Dataset Card

Upstream [`R2E-Gym/R2E-Gym-Subset`](https://huggingface.co/datasets/R2E-Gym/R2E-Gym-Subset) publishes no prose dataset card (auto-generated metadata only) — see the dataset page and the [project README](https://github.com/R2E-Gym/R2E-Gym) for documentation.

