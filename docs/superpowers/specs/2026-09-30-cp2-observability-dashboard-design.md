# CP2: Traces, Prompt Versioning, Dashboard, and Alerts

**Status:** Design approved in chat; awaiting written review before implementation planning.

## Goal

Complete the repository work for CP2 so a student can inspect each request from the `lab-agent-run` root to its retrieval and generation children, see six live operational panels based on `data/logs.jsonl`, and use an explained SLO with three actionable alerts. Preserve the existing local prompt fallback and the requirement that traces contain no raw user input or output.

## Scope

- Add Langfuse v4 child observations for retrieval and generation.
- Attach model, token usage, cost, and the managed prompt object to the generation observation.
- Keep decorator input and output capture disabled. Keep `correlation_id` in trace metadata.
- Implement a local web dashboard with exactly six panels, a 60-minute UTC window, 30-second refresh, units, and thresholds from `config/dashboard.yaml`.
- Correct retrieval-success mapping so it uses every record that has `tool_success`, including `response_sent` and `request_failed`.
- Explain the existing SLO/error budget and define three symptom-based alerts with runbooks.
- Add tests for tracing updates, metric calculation, malformed/empty log handling, and configuration contracts.

## Out of scope

- Changing the fake LLM response behavior or optimizing prompts.
- Sending raw prompt text, compiled user input, or generated output to Langfuse.
- Adding Streamlit, plotting packages, or other runtime dependencies.
- Creating the student's Langfuse project or changing labels through a third-party UI. The student performs prompt creation, promote/rollback, and captures project evidence in their own Langfuse project.
- Running the official incident challenge during CP2.

## Trace design

Keep the current root observation named `lab-agent-run` and its trace name `day13-agent-request`. Decorate `retrieve()` with a retrieval observation (`retriever` or `span`) and `FakeLLM.generate()` with a `generation` observation. Both decorators set `capture_input=False` and `capture_output=False`.

The generation implementation updates the active Langfuse generation with the model, input/output token usage, cost details using the current estimate, and `prompt=managed_prompt` when Langfuse supplied a managed prompt. The compiled prompt text is passed only to the fake model for its local behavior; it is not used as the Langfuse prompt link. Local fallback requests have no managed prompt link but retain `prompt_source`, name, label, and version metadata. The root metadata continues to carry `correlation_id`.

Langfuse's Python SDK supports generation updates through `update_current_generation()` and links managed prompts to a specific generation through the `prompt` parameter. Nested `@observe` calls create child observations. The implementation must use the installed v4 APIs. References: [prompt-to-trace linking](https://langfuse.com/docs/prompt-management/features/link-to-traces), [token and cost tracking](https://langfuse.com/docs/observability/features/token-and-cost-tracking), and [Python instrumentation](https://langfuse.com/docs/observability/sdk/instrumentation).

## Dashboard design

### Module interface

Create a testable metrics module in `app/dashboard.py` with a small entry point such as:

```python
load_dashboard_data(log_path: Path, config_path: Path, now: datetime | None = None) -> dict
```

It reads the YAML panel contract and JSONL log source, filters to the latest 60 minutes in UTC, skips malformed JSON lines, and returns a JSON-serializable snapshot with panel values, one-minute series, unit, and configured threshold. Missing or empty log input returns empty/null values rather than raising or fabricating zero-valued rates. A zero denominator yields `None` for the corresponding percentage.

### Runtime interface

Add `scripts/dashboard.py` as a standard-library HTTP server bound only to `127.0.0.1` (default port `8501`). It serves one self-contained HTML page and a JSON endpoint for the snapshot. The page renders six named panels with inline SVG/HTML, shows the 60-minute UTC window and units, renders configured threshold lines, and refreshes the snapshot every 30 seconds. It does not expose raw log lines in the browser.

### Six panel calculations

| Panel | Source records and calculation |
|---|---|
| Latency | `response_sent`: nearest-rank P50/P95/P99 of `latency_ms` and P95 of `ttft_ms`; one-minute series and P95 threshold. |
| Traffic | `request_received`: total and request count per minute. |
| Errors | Error rate = `request_failed / request_received * 100`; error breakdown by `error_type`; retrieval success = successful `tool_success` records divided by all records with non-null `tool_success`, across event types. |
| Cost | `response_sent`: cost per minute and total USD. |
| Tokens | `response_sent`: input/output token totals and minute series. |
| Quality | `response_sent`: mean `quality_score`. |

The `errors.events` contract includes `request_received`, `request_failed`, and `response_sent` so its declared source matches the retrieval-success calculation.

## SLO and alert design

Keep the SLO target at 99.5% of requests returning successfully within 3,000 ms over 28 days. Explain the 0.5% error budget and the conversion `10,000 requests × 0.5% = 50 allowed bad requests` in `config/slo.yaml`.

All alerts use Slack channel `#k4-l3b-alerts`, owner `student-2A202602879`, and their existing runbook anchors:

1. `HighLatencyP95`: P95 latency above 3,000 ms for 5 minutes; warning.
2. `HighErrorRate`: request error rate above 2% for 5 minutes; critical.
3. `LowRetrievalSuccess`: retrieval success below 90% for 5 minutes; warning.

Each matching `docs/alerts.md` section retains the `## Alert 1/2/3` heading and documents user impact, the first three checks in Metrics → Logs → Traces order, mitigation, and owner.

## Prompt versioning workflow

The current `resolve_prompt()` behavior already reads `LANGFUSE_PROMPT_NAME` and `LANGFUSE_PROMPT_LABEL`, uses the 60-second prompt cache, and reports managed/local fallback metadata. Do not change that behavior unless new tests reveal a defect.

The student creates a **Text** prompt named `day13-chat` in their individual Langfuse project with `{{feature}}`, `{{docs}}`, and `{{message}}`; labels v1 `baseline` and `production`; creates v2 labeled `candidate`; sends the same safe sample request under baseline and candidate; promotes `production` to v2; then rolls it back to v1. Restart the API after label changes to clear the prompt cache. Save the two trace IDs and screenshots of versions and post-promote/post-rollback labels in the report/evidence directory.

## Failure behavior and privacy

- If Langfuse keys are absent or prompt fetch fails, the app remains runnable on the existing local fallback and labels the trace source accordingly.
- Do not attach raw input/output to root, retrieval, or generation observations.
- Do not include raw JSONL rows in dashboard responses; only derived aggregates and error-type counts are displayed.
- Malformed log lines are skipped. An absent/empty file and zero-denominator calculations produce a visible empty state.
- Bind the dashboard server to loopback only.

## Verification plan

Use test-first changes. Tests cover decorator observation types and capture flags, generation update fields and prompt object identity, no raw prompt content in update payloads, nearest-rank percentiles, UTC-window filtering, per-minute aggregation, error rate, retrieval-success denominator, empty/corrupt logs, and required panel/alert config.

After implementation:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\validate_dashboard.py
.\.venv\Scripts\python.exe scripts\dashboard.py
```

With the API running and a project configured, send at least ten safe sample requests, wait several seconds for Langfuse background export, and verify the root/retrieval/generation tree plus model, prompt version, token usage, cost, and correlation ID in the student's Langfuse project. The student captures dashboard and Langfuse UI evidence; CP2 does not use the official challenge file.
