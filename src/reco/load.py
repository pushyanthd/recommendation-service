"""Open-loop HTTP measurements including client queueing, with bounded concurrency."""

import asyncio
import time
from pathlib import Path
from typing import Any

import numpy as np

from reco.storage import atomic_json, sha256_file


async def measure_http(
    base_url: str,
    output: Path,
    expected_model_id: str,
    requests: int = 5000,
    rate: float = 20,
    warmup: int = 200,
) -> dict[str, Any]:
    import httpx

    if not base_url.startswith("http://127.0.0.1:"):
        raise ValueError("Load measurement requires the owned loopback service")
    if not 1 <= requests <= 10000 or not 0 < rate <= 100 or not 0 <= warmup <= 1000:
        raise ValueError("Load configuration exceeds limits")
    output.mkdir(parents=True, exist_ok=True)
    limits = httpx.Limits(max_connections=4, max_keepalive_connections=4)
    async with httpx.AsyncClient(base_url=base_url, timeout=10, limits=limits) as client:
        response = await client.get("/v1/model")
        response.raise_for_status()
        model = response.json()
        if model["model_id"] != expected_model_id:
            raise ValueError("Load model identity differs from bundle")
        response = await client.get("/v1/profiles")
        response.raise_for_status()
        profiles = response.json()
        response = await client.get("/v1/catalog")
        response.raise_for_status()
        catalog = response.json()
        mixes = []
        for cohort in ("warm", "sparse", "zero_history"):
            profile = next((row for row in profiles if row["cohort"] == cohort), None)
            if profile is None:
                if cohort == "zero_history":
                    continue  # Ephemeral empty likes still exercise zero-history serving.
                raise ValueError(f"Missing load cohort: {cohort}")
            mixes.append((cohort, {"user_id": profile["user_id"], "k": 10}))
        for count in (0, 1, 3):
            mixes.append(
                (
                    f"ephemeral_{count}",
                    {
                        "liked_movie_ids": [row["movie_id"] for row in catalog[:count]],
                        "k": 10,
                    },
                )
            )
        for index in range(warmup):
            response = await client.post("/v1/recommendations", json=mixes[index % len(mixes)][1])
            response.raise_for_status()
            if response.json()["model_id"] != expected_model_id:
                raise ValueError("Model changed during warmup")
        rows: list[dict[str, Any]] = []
        semaphore = asyncio.Semaphore(4)
        started = time.perf_counter()

        async def request_one(index: int, scheduled: float) -> None:
            name, payload = mixes[index % len(mixes)]
            row: dict[str, Any] = {"sequence": index, "profile_type": name, "error": None}
            try:
                async with semaphore:
                    sent = time.perf_counter()
                    row["queue_ms"] = (sent - scheduled) * 1000
                    response = await client.post("/v1/recommendations", json=payload)
                    row["status"] = response.status_code
                    response.raise_for_status()
                    result = response.json()
                    if result["model_id"] != expected_model_id:
                        raise ValueError("Model changed during measurement")
                    row["scoring_ms"] = result["elapsed_ms"]
                    row["fallback_reason"] = result["fallback_reason"]
                    row["variant"] = result["variant"]
            except (httpx.HTTPError, ValueError, KeyError) as exc:
                row["error"] = type(exc).__name__
            row["wall_ms"] = (time.perf_counter() - scheduled) * 1000
            rows.append(row)

        tasks = []
        for index in range(requests):
            scheduled = started + index / rate
            await asyncio.sleep(max(0, scheduled - time.perf_counter()))
            tasks.append(asyncio.create_task(request_one(index, scheduled)))
        await asyncio.gather(*tasks)
        duration = time.perf_counter() - started
        response = await client.get("/metrics")
        response.raise_for_status()
        (output / "metrics.prom").write_text(response.text)
        response = await client.get("/v1/model")
        response.raise_for_status()
        final_model = response.json()
        if final_model["model_id"] != expected_model_id:
            raise ValueError("Model changed at measurement completion")
    rows.sort(key=lambda row: row["sequence"])
    atomic_json(output / "timings.json", rows)
    timings = np.array([row["wall_ms"] for row in rows])
    failures = sum(row["error"] is not None for row in rows)
    summary = {
        "protocol": "open-loop-http-v1",
        "model_id": expected_model_id,
        "data_mode": model["data_mode"],
        "configuration": {
            "requests": requests,
            "offered_requests_per_second": rate,
            "warmup": warmup,
            "concurrency_cap": 4,
            "k": 10,
            "mix": [name for name, _ in mixes],
        },
        "scheduled": requests,
        "completed": requests - failures,
        "failed": failures,
        "error_rate": failures / requests,
        "duration_seconds": duration,
        "achieved_requests_per_second": requests / duration,
        "client_wall_ms": {
            "p50": float(np.percentile(timings, 50)),
            "p95": float(np.percentile(timings, 95)),
            "max": float(timings.max()),
        },
        "queue_ms_p95": float(np.percentile([row["queue_ms"] for row in rows], 95)),
        "fallback_requests": sum(row.get("fallback_reason") is not None for row in rows),
        "startup_load_ms": model["startup_load_ms"],
        "peak_api_process_rss_bytes": final_model["peak_process_rss_bytes"],
        "raw_timings_sha256": sha256_file(output / "timings.json"),
        "metrics_sha256": sha256_file(output / "metrics.prom"),
        "reference_protocol_complete": requests == 5000 and rate == 20 and warmup == 200,
        "http_gate_passed": failures == 0 and float(np.percentile(timings, 95)) < 50,
        "memory_gate_passed": final_model["peak_process_rss_bytes"] < 2 * 1024**3,
    }
    atomic_json(output / "summary.json", summary)
    return summary
