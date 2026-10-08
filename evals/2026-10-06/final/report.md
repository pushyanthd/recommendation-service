# CPU recommendation comparison — movielens_1m

Phase: **frozen_final_test**. Status: **experimental_quality_objective_failed**.

Full prediction-time catalog; all unseen future positives remain in denominators. Scoring timings are in-process measurements, not HTTP load results. Offline ratings do not establish engagement or revenue effects.

| Variant | Users | NDCG@10 | Recall@10 | Recall@20 | HitRate@10 | Coverage@10 | Fallback | Scoring P95 ms | Failures |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| popularity | 1188 | 0.218277 | 0.057307 | 0.093712 | 0.642256 | 0.0383 | 0.0000 | 0.877 | 0 |
| item_knn | 1188 | 0.244413 | 0.063598 | 0.103511 | 0.649832 | 0.0669 | 0.0354 | 1.006 | 0 |
| als_cpu | 1188 | 0.196194 | 0.063736 | 0.108018 | 0.640572 | 0.3021 | 0.0354 | 0.950 | 0 |

```json
{
  "backend": "cpu",
  "data_fingerprint": "a6898adb50b9ca05aa231689da44c217cb524e7ebd39d264c56e2832f2c54e20",
  "data_mode": "movielens_1m",
  "execution_identity": {
    "dependencies": {
      "fastapi": "0.142.2",
      "implicit": "0.7.3",
      "numpy": "2.5.3",
      "pydantic": "2.13.5",
      "scipy": "1.18.1",
      "threadpoolctl": "3.7.0"
    },
    "dependency_lock_sha256": "d93e9d8ba152520f8ab15fed9bd3e244e219db0b06745b971d61d761a0eb7655",
    "python": "3.12.12",
    "source_files": {
      "__init__.py": "6d6f9595cfccb7646730a08104bf455c9d6d85c5789258cfe9793d49d84c5d8b",
      "api.py": "0903339a63fcde354beac18642e602be464eeb4de65ab45a6582a10f928e5875",
      "benchmark.py": "915c186ae162aefba395f6278b8b033d06a14ca8d2c6f09e1f7590050a0f3fa8",
      "cli.py": "25ddeeabcd2d26c9d04b365f224c3a101c3d670d1aea55689d6dcd1cfdbccd54",
      "contracts.py": "98e352800e53eeb8e130aeedcb9c0e443d5cfe8896712be6c4f5ee72b7e8e180",
      "data.py": "1cbaafd8ef2fbd9203632af8bfa46a839466586be1055518991a93f60fa33ada",
      "evaluation.py": "bc148d96df3d675c5d6dd37b9ea8c48aea2b2aa3f1739ae7c07b9a208253341a",
      "evidence.py": "68d4c9b8e866cefb82156080fdbd86a825bfb399010b2c8839c6d8da5505c879",
      "fixtures/movies.json": "52ededb370ed9f7618f72d466e2886850db677b302a97c6adcb2da56c9f5d634",
      "ingestion.py": "ec5d3152db9a280292886de78eabf6f78bbd790b9297fe2c0e2d716af73d0b44",
      "ranking.py": "6671b0531773530f239b086b6821a2cf255e1a0e1f7349d5b25ac0ae4babba3c",
      "reports.py": "52c8a00225d7fbd7ae6b7b2a0980bfde355c67a037a63b2525e88abc88309a69",
      "selection.py": "2b68d9a726e6a4ebadd672af7f5f6d45d933a69f83859f13a953876c741f4586",
      "storage.py": "93312e59b0c8badf3363db8b68c7cad7c3394e9ac556dfcfd0586f65821efa08",
      "ui/index.html": "2aa8df52e47184c8a2ae3761675b28c4b70ef0cb54787028e46e4440cabf114c"
    }
  },
  "final_quality_gates": [
    {
      "comparison": {
        "candidate": "item_knn",
        "interval_scope": "Paired benchmark users; shared items/training limit generalization",
        "metrics": {
          "hit_rate_at_10": {
            "absolute_difference": 0.007575757575757576,
            "paired_95_interval": [
              -0.013468013468013467,
              0.02861952861952862
            ]
          },
          "ndcg_at_10": {
            "absolute_difference": 0.02613617339046683,
            "paired_95_interval": [
              0.01837645214134087,
              0.03459936345469998
            ]
          },
          "recall_at_10": {
            "absolute_difference": 0.006291525938799548,
            "paired_95_interval": [
              0.0008299020145209701,
              0.011738044765962137
            ]
          },
          "recall_at_20": {
            "absolute_difference": 0.009798714477462792,
            "paired_95_interval": [
              0.003715703112295294,
              0.01631904782670067
            ]
          }
        },
        "paired_users": 1188,
        "relative_ndcg_gain": 0.11973865479425956,
        "samples": 2000,
        "seed": 42
      },
      "passed": true,
      "reasons": [],
      "variant": "item_knn"
    },
    {
      "comparison": {
        "candidate": "als_cpu",
        "interval_scope": "Paired benchmark users; shared items/training limit generalization",
        "metrics": {
          "hit_rate_at_10": {
            "absolute_difference": -0.0016835016835016834,
            "paired_95_interval": [
              -0.029461279461279462,
              0.026936026936026935
            ]
          },
          "ndcg_at_10": {
            "absolute_difference": -0.022083209521291728,
            "paired_95_interval": [
              -0.03421700194291319,
              -0.00948913904444332
            ]
          },
          "recall_at_10": {
            "absolute_difference": 0.006428813741111423,
            "paired_95_interval": [
              -0.0008626851436670525,
              0.01398487712736901
            ]
          },
          "recall_at_20": {
            "absolute_difference": 0.014306228215796519,
            "paired_95_interval": [
              0.005828033855368277,
              0.02334716425292568
            ]
          }
        },
        "paired_users": 1188,
        "relative_ndcg_gain": -0.10117065578481864,
        "samples": 2000,
        "seed": 42
      },
      "passed": false,
      "reasons": [
        "ndcg_relative_gain_below_objective",
        "ndcg_interval_not_above_zero"
      ],
      "variant": "als_cpu"
    }
  ],
  "hardware": {
    "als_threads": 2,
    "blas_threads_during_fit_and_scoring": 1,
    "machine": "arm64",
    "numerical_libraries": [],
    "peak_process_rss_bytes": 958218240,
    "platform": "macOS-26.6.2-arm64-arm-64bit"
  },
  "http_load_gate": "unmeasured_no_promotion",
  "limitations": [
    "Rating activity timestamps are not verified viewing/exposure times",
    "Missing ratings are unobserved preferences",
    "Fixture correctness cannot establish MovieLens ranking quality",
    "No product pass or deployment promotion before HTTP and bundle checks"
  ],
  "phase": "frozen_final_test",
  "protocol": {
    "bootstrap_samples": 2000,
    "bootstrap_seed": 42,
    "maximum_peak_rss_bytes": 2147483648,
    "maximum_recall_at_20_drop": 0.01,
    "maximum_single_fit_seconds": 600.0,
    "minimum_relative_ndcg_gain": 0.1,
    "near_tie_absolute_ndcg": 0.001,
    "positive_rating_min": 4,
    "protocol": "chronological-full-catalog-v1",
    "test_start": 0.9,
    "train_fraction": 0.8,
    "variants": [
      "popularity",
      "item_knn",
      "als_cpu"
    ],
    "warm_http_p95_objective_ms": 50.0
  },
  "release_status": "experimental_quality_objective_failed",
  "resource_gate": true,
  "schema_version": 1,
  "selection": {
    "promotion_status": "pending_http_resource_and_bundle_gates",
    "quality_gates": [
      {
        "comparison": {
          "candidate": "item_knn",
          "interval_scope": "Paired benchmark users; shared items/training limit generalization",
          "metrics": {
            "hit_rate_at_10": {
              "absolute_difference": 0.005439709882139619,
              "paired_95_interval": [
                -0.006346328195829556,
                0.01813236627379873
              ]
            },
            "ndcg_at_10": {
              "absolute_difference": 0.008866954398135767,
              "paired_95_interval": [
                0.003926097634791934,
                0.013702922211801414
              ]
            },
            "recall_at_10": {
              "absolute_difference": 0.004810882563633702,
              "paired_95_interval": [
                0.0006255308212381545,
                0.008964118278280796
              ]
            },
            "recall_at_20": {
              "absolute_difference": 0.00246065671600328,
              "paired_95_interval": [
                -0.0024474488038315335,
                0.007840121857042994
              ]
            }
          },
          "paired_users": 1103,
          "relative_ndcg_gain": 0.03405095138098141,
          "samples": 2000,
          "seed": 42
        },
        "passed": false,
        "reasons": [
          "ndcg_relative_gain_below_objective"
        ],
        "variant": "item_knn"
      },
      {
        "comparison": {
          "candidate": "als_cpu",
          "interval_scope": "Paired benchmark users; shared items/training limit generalization",
          "metrics": {
            "hit_rate_at_10": {
              "absolute_difference": -0.006346328195829556,
              "paired_95_interval": [
                -0.025385312783318223,
                0.012692656391659111
              ]
            },
            "ndcg_at_10": {
              "absolute_difference": -0.007337745884873807,
              "paired_95_interval": [
                -0.014071867170941272,
                -0.0005110343111944903
              ]
            },
            "recall_at_10": {
              "absolute_difference": 0.0074394893491618735,
              "paired_95_interval": [
                -0.00026379547207831274,
                0.01480639796166996
              ]
            },
            "recall_at_20": {
              "absolute_difference": 0.010086154229342786,
              "paired_95_interval": [
                0.0016372962037878845,
                0.018677451874821678
              ]
            }
          },
          "paired_users": 1103,
          "relative_ndcg_gain": -0.02817847224119768,
          "samples": 2000,
          "seed": 42
        },
        "passed": false,
        "reasons": [
          "ndcg_relative_gain_below_objective",
          "ndcg_interval_not_above_zero"
        ],
        "variant": "als_cpu"
      }
    ],
    "selected_for_final_refit": "popularity",
    "serving_variant": "popularity",
    "test_labels_used_for_selection": false
  },
  "split": {
    "test_cutoff": 978133414,
    "test_events": 100021,
    "train_events": 800164,
    "validation_cutoff": 975768738,
    "validation_events": 100024
  },
  "evidence_kind": "aggregate_summary_not_raw_user_evidence",
  "raw_source_report_sha256": "cfe320cd30c9850077e7ee2af3d13f7b2c7f6b2d98382c444baa3e5b05242e25",
  "raw_user_accounting_verified_before_export": true,
  "variant_diagnostics": [
    {
      "catalog_fingerprint": "4e2e566f458a7ea01369a560b7ed0ad8ae26581f7dee7309d9202fa7a5ccb467",
      "catalog_size": 3678,
      "cohorts": {
        "sparse": {
          "descriptive_only": false,
          "metrics": {
            "hit_rate_at_10": 0.7948717948717948,
            "ndcg_at_10": 0.29058576974605826,
            "recall_at_10": 0.05900106740794275,
            "recall_at_20": 0.10115599576422293
          },
          "users": 39
        },
        "warm": {
          "descriptive_only": false,
          "metrics": {
            "hit_rate_at_10": 0.6288014311270125,
            "ndcg_at_10": 0.20932206093774236,
            "recall_at_10": 0.05665266750672867,
            "recall_at_20": 0.09261854554661329
          },
          "users": 1118
        },
        "zero_history": {
          "descriptive_only": false,
          "metrics": {
            "hit_rate_at_10": 0.9354838709677419,
            "ndcg_at_10": 0.45025673787635917,
            "recall_at_10": 0.07876333921957233,
            "recall_at_20": 0.12378582846166745
          },
          "users": 31
        }
      },
      "completed_users": 1188,
      "config": {
        "als": null,
        "min_likes_for_personalization": 3,
        "neighbors": null,
        "positive_rating_min": 4,
        "variant": "popularity"
      },
      "coverage_at_10": 0.03833605220228385,
      "data_fingerprint": "a6898adb50b9ca05aa231689da44c217cb524e7ebd39d264c56e2832f2c54e20",
      "data_mode": "movielens_1m",
      "eligible_users": 1188,
      "failed_users": 0,
      "fallback_rate": 0.0,
      "fit_ms": 1090.761500003282,
      "history_fingerprint": "22572ce3623eddd4534a5e47561d5fc82806031fe1a1fe486a19309651dd2385",
      "metric_protocol": "binary-future-positive-4-unseen-full-catalog-v1",
      "metrics": {
        "hit_rate_at_10": 0.6422558922558923,
        "ndcg_at_10": 0.21827682493489844,
        "recall_at_10": 0.05730672341518448,
        "recall_at_20": 0.0937121030624832
      },
      "model_id": "movielens_1m-087582f44d7b5e9a",
      "no_target_users": 4852,
      "popular_fraction_at_10": 1.0,
      "positive_targets": 54452,
      "scoring_latency_ms": {
        "p50": 0.8192294917535037,
        "p95": 0.8772035012952983
      },
      "target_fingerprint": "6d75bceedce88d2b44b558df10800fc1f0a4a7bf9479d11aec49854d015481d4",
      "total_users": 6040,
      "unreachable_positives": 45,
      "variant": "popularity"
    },
    {
      "catalog_fingerprint": "4e2e566f458a7ea01369a560b7ed0ad8ae26581f7dee7309d9202fa7a5ccb467",
      "catalog_size": 3678,
      "cohorts": {
        "sparse": {
          "descriptive_only": false,
          "metrics": {
            "hit_rate_at_10": 0.7435897435897436,
            "ndcg_at_10": 0.3272564069433807,
            "recall_at_10": 0.05719732652537353,
            "recall_at_20": 0.10443599010118941
          },
          "users": 39
        },
        "warm": {
          "descriptive_only": false,
          "metrics": {
            "hit_rate_at_10": 0.6386404293381037,
            "ndcg_at_10": 0.23581545909264306,
            "recall_at_10": 0.06340103844565002,
            "recall_at_20": 0.10291635683470284
          },
          "users": 1118
        },
        "zero_history": {
          "descriptive_only": false,
          "metrics": {
            "hit_rate_at_10": 0.9354838709677419,
            "ndcg_at_10": 0.45025673787635917,
            "recall_at_10": 0.07876333921957233,
            "recall_at_20": 0.12378582846166745
          },
          "users": 31
        }
      },
      "completed_users": 1188,
      "config": {
        "als": null,
        "min_likes_for_personalization": 3,
        "neighbors": 100,
        "positive_rating_min": 4,
        "variant": "item_knn"
      },
      "coverage_at_10": 0.06688417618270799,
      "data_fingerprint": "a6898adb50b9ca05aa231689da44c217cb524e7ebd39d264c56e2832f2c54e20",
      "data_mode": "movielens_1m",
      "eligible_users": 1188,
      "failed_users": 0,
      "fallback_rate": 0.03535353535353535,
      "fit_ms": 2085.82420804305,
      "history_fingerprint": "22572ce3623eddd4534a5e47561d5fc82806031fe1a1fe486a19309651dd2385",
      "metric_protocol": "binary-future-positive-4-unseen-full-catalog-v1",
      "metrics": {
        "hit_rate_at_10": 0.6498316498316499,
        "ndcg_at_10": 0.2444129983253653,
        "recall_at_10": 0.06359824935398403,
        "recall_at_20": 0.103510817539946
      },
      "model_id": "movielens_1m-c31e300b0c9b15fc",
      "no_target_users": 4852,
      "popular_fraction_at_10": 0.9966329966329966,
      "positive_targets": 54452,
      "scoring_latency_ms": {
        "p50": 0.8485625148750842,
        "p95": 1.0063373803859574
      },
      "target_fingerprint": "6d75bceedce88d2b44b558df10800fc1f0a4a7bf9479d11aec49854d015481d4",
      "total_users": 6040,
      "unreachable_positives": 45,
      "variant": "item_knn"
    },
    {
      "catalog_fingerprint": "4e2e566f458a7ea01369a560b7ed0ad8ae26581f7dee7309d9202fa7a5ccb467",
      "catalog_size": 3678,
      "cohorts": {
        "sparse": {
          "descriptive_only": false,
          "metrics": {
            "hit_rate_at_10": 0.7692307692307693,
            "ndcg_at_10": 0.2791908008527626,
            "recall_at_10": 0.05542861964639851,
            "recall_at_20": 0.09798884883349748
          },
          "users": 39
        },
        "warm": {
          "descriptive_only": false,
          "metrics": {
            "hit_rate_at_10": 0.627906976744186,
            "ndcg_at_10": 0.18625368068330939,
            "recall_at_10": 0.06360862116248948,
            "recall_at_20": 0.10793099442913973
          },
          "users": 1118
        },
        "zero_history": {
          "descriptive_only": false,
          "metrics": {
            "hit_rate_at_10": 0.9354838709677419,
            "ndcg_at_10": 0.45025673787635917,
            "recall_at_10": 0.07876333921957233,
            "recall_at_20": 0.12378582846166745
          },
          "users": 31
        }
      },
      "completed_users": 1188,
      "config": {
        "als": {
          "factors": 32,
          "iterations": 15,
          "positive_confidence": 20,
          "regularization": 0.1,
          "seed": 42,
          "threads": 2
        },
        "min_likes_for_personalization": 3,
        "neighbors": null,
        "positive_rating_min": 4,
        "variant": "als_cpu"
      },
      "coverage_at_10": 0.3020663404023926,
      "data_fingerprint": "a6898adb50b9ca05aa231689da44c217cb524e7ebd39d264c56e2832f2c54e20",
      "data_mode": "movielens_1m",
      "eligible_users": 1188,
      "failed_users": 0,
      "fallback_rate": 0.03535353535353535,
      "fit_ms": 2894.3121249903925,
      "history_fingerprint": "22572ce3623eddd4534a5e47561d5fc82806031fe1a1fe486a19309651dd2385",
      "metric_protocol": "binary-future-positive-4-unseen-full-catalog-v1",
      "metrics": {
        "hit_rate_at_10": 0.6405723905723906,
        "ndcg_at_10": 0.19619361541360675,
        "recall_at_10": 0.0637355371562959,
        "recall_at_20": 0.10801833127827973
      },
      "model_id": "movielens_1m-f559bf70c67b0beb",
      "no_target_users": 4852,
      "popular_fraction_at_10": 0.7372053872053872,
      "positive_targets": 54452,
      "scoring_latency_ms": {
        "p50": 0.8958335092756897,
        "p95": 0.9499766601948066
      },
      "target_fingerprint": "6d75bceedce88d2b44b558df10800fc1f0a4a7bf9479d11aec49854d015481d4",
      "total_users": 6040,
      "unreachable_positives": 45,
      "variant": "als_cpu"
    }
  ]
}
```
