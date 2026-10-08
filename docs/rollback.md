# Activation, rollback and recovery

Run commands from the repository root. Model changes are local CLI operations; the HTTP API cannot train, upload or activate models.

Build a candidate without modifying the active pointer:

```bash
.venv/bin/reco build-bundle --report artifacts/benchmark/final
.venv/bin/reco verify-bundle artifacts/models/<printed-model-id>
```

For the first model only, add `--select` to bundle construction. Start the owned service and save its active version from `/v1/model`:

```bash
.venv/bin/reco start
curl -fsS http://127.0.0.1:8000/v1/model
.venv/bin/reco activate --model-id <candidate-model-id>
```

Activation verifies files, mappings and eligibility before changing the active JSON pointer. It retains the last-known-good pointer, stops the owned process, atomically replaces the selection, starts a fresh process and checks `/readyz` for the requested version. Corrupt or rejected candidates leave the current pointer/process intact. Startup failure restores the previous pointer and launches/verifies the previous version. Logs and the last activation result remain under the model root.

Rollback selects an already verified prior version through the same restart/probe workflow:

```bash
.venv/bin/reco rollback --model-id <prior-model-id>
```

After an interrupted activation or stale pointer, explicitly restore the validated last-known-good version:

```bash
.venv/bin/reco recover
```

Recovery rejects a missing, changed or corrupt last-known-good bundle. Process management refuses to signal a PID whose actual command/ownership token no longer matches; investigate that state rather than editing the PID to another process. Commands accept `--root` and startup/recovery accept `--port` for isolated local runs. `reco stop` preserves model selection for the next startup.

The generated showcase demonstrates all four required drills against real processes/files in its isolated `service` directory. It also preserves raw request timings and actual version/PID evidence. The test suite adds startup-failure restoration and stale-pointer recovery. See the [October 7 evidence](../evals/2026-10-07/report.html).
