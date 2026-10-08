# CPU recommendation service showcase

Status: **experimental_quality_objective_failed**. Selected: **popularity**.

Model: `movielens_1m-087582f44d7b5e9a-052d6efc4263ecfe`. Data: `movielens_1m`.

| Method | Final NDCG@10 | Final Recall@20 |
|---|---:|---:|
| popularity | 0.218277 | 0.093712 |
| item_knn | 0.244413 | 0.103511 |
| als_cpu | 0.196194 | 0.108018 |

HTTP: 5000/5000 completed; 0 failures; warm client P95 11.516 ms; 20.00 requests/s.

API process peak RSS: 175.3 MiB. Snapshot startup load: 302.55 ms.

## Recovery drills

- corrupt_candidate_rejected: passed
- forced_gate_rejection: passed
- restart_preserves_version_and_ranking: passed
- rollback_restores_exact_prior_version: passed

Validation selection is preserved. Final metrics do not select a new model. Offline rating recovery does not establish viewing, clicks or revenue. HTTP latency includes client queueing. Docker/whole-system memory is separate. Raw timings and process evidence remain in ignored local artifacts.
