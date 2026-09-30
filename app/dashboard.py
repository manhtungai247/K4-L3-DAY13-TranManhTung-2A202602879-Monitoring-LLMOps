from __future__ import annotations

import json
import math
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import yaml


def _nearest_rank_percentile(values: list[float | int], p: float) -> float | None:
    if not values:
        return None
    s = sorted(values)
    k = max(1, math.ceil((p / 100.0) * len(s)))
    return float(s[min(k - 1, len(s) - 1)])


def load_dashboard_data(
    log_path: Path,
    config_path: Path,
    now: datetime | None = None,
) -> dict[str, Any]:
    # 1. Load config
    try:
        config_text = config_path.read_text(encoding="utf-8")
        config_data = yaml.safe_load(config_text)
    except Exception:
        config_data = {}

    dashboard_cfg = config_data.get("dashboard", {})
    window_minutes = int(dashboard_cfg.get("time_range_minutes", 60))

    # 2. Read logs
    records: list[dict[str, Any]] = []
    if log_path.exists():
        for line in log_path.read_text(encoding="utf-8").splitlines():
            line_str = line.strip()
            if not line_str:
                continue
            try:
                rec = json.loads(line_str)
                if isinstance(rec, dict) and "ts" in rec:
                    records.append(rec)
            except Exception:
                continue

    # Determine reference time
    parsed_records: list[tuple[datetime, dict[str, Any]]] = []
    for r in records:
        ts_str = str(r["ts"])
        try:
            dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            parsed_records.append((dt, r))
        except Exception:
            continue

    if now is None:
        if parsed_records:
            now = max(dt for dt, _ in parsed_records)
        else:
            now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    window_start = now - timedelta(minutes=window_minutes)

    # Filter records within window
    window_records = [r for dt, r in parsed_records if window_start <= dt <= now]

    # Latency calculations
    latencies: list[int] = []
    ttfts: list[int] = []
    latency_minute_buckets: dict[str, list[int]] = {}

    # Traffic calculations
    received_count = 0
    traffic_minute_buckets: dict[str, int] = {}

    # Error calculations
    failed_count = 0
    error_types: dict[str, int] = {}
    tool_success_true = 0
    tool_success_total = 0

    # Cost calculations
    cost_total = 0.0
    cost_minute_buckets: dict[str, float] = {}

    # Token calculations
    tokens_in_total = 0
    tokens_out_total = 0
    tokens_minute_buckets: dict[str, dict[str, int]] = {}

    # Quality calculations
    quality_scores: list[float] = []

    for dt, r in parsed_records:
        if not (window_start <= dt <= now):
            continue

        evt = r.get("event")
        minute_key = dt.strftime("%H:%M")

        # Track tool_success across all events that have it
        if "tool_success" in r and r["tool_success"] is not None:
            tool_success_total += 1
            if r["tool_success"] is True:
                tool_success_true += 1

        if evt == "request_received":
            received_count += 1
            traffic_minute_buckets[minute_key] = traffic_minute_buckets.get(minute_key, 0) + 1

        elif evt == "response_sent":
            lat = r.get("latency_ms")
            if isinstance(lat, (int, float)):
                latencies.append(int(lat))
                latency_minute_buckets.setdefault(minute_key, []).append(int(lat))

            ttft = r.get("ttft_ms")
            if isinstance(ttft, (int, float)):
                ttfts.append(int(ttft))

            cost = r.get("cost_usd")
            if isinstance(cost, (int, float)):
                cost_val = float(cost)
                cost_total += cost_val
                cost_minute_buckets[minute_key] = cost_minute_buckets.get(minute_key, 0.0) + cost_val

            t_in = r.get("tokens_in")
            t_out = r.get("tokens_out")
            if isinstance(t_in, (int, float)) and isinstance(t_out, (int, float)):
                tokens_in_total += int(t_in)
                tokens_out_total += int(t_out)
                b = tokens_minute_buckets.setdefault(minute_key, {"in": 0, "out": 0})
                b["in"] += int(t_in)
                b["out"] += int(t_out)

            q = r.get("quality_score")
            if isinstance(q, (int, float)):
                quality_scores.append(float(q))

        elif evt == "request_failed":
            failed_count += 1
            err_type = str(r.get("error_type", "UnknownError"))
            error_types[err_type] = error_types.get(err_type, 0) + 1

    p50 = _nearest_rank_percentile(latencies, 50)
    p95 = _nearest_rank_percentile(latencies, 95)
    p99 = _nearest_rank_percentile(latencies, 99)
    ttft_p95 = _nearest_rank_percentile(ttfts, 95)

    error_rate_pct = (
        round((failed_count / received_count) * 100, 2)
        if received_count > 0
        else None
    )

    retrieval_success_rate_pct = (
        round((tool_success_true / tool_success_total) * 100, 2)
        if tool_success_total > 0
        else None
    )

    avg_quality = (
        round(sum(quality_scores) / len(quality_scores), 3)
        if quality_scores
        else None
    )

    rate_per_minute = round(received_count / max(1, window_minutes), 2)

    return {
        "title": dashboard_cfg.get("title", "K4-L3B Day 13 Monitoring & LLMOps"),
        "time_range_minutes": window_minutes,
        "window_start": window_start.isoformat(),
        "window_end": now.isoformat(),
        "total_records_in_window": len(window_records),
        "panels": {
            "latency": {
                "title": "Latency percentiles and TTFT",
                "unit": "ms",
                "p50": p50,
                "p95": p95,
                "p99": p99,
                "ttft_p95": ttft_p95,
                "threshold": {"aggregation": "p95", "operator": "lte", "value": 3000},
                "series": [
                    {"minute": m, "p95": _nearest_rank_percentile(vals, 95)}
                    for m, vals in sorted(latency_minute_buckets.items())
                ],
            },
            "traffic": {
                "title": "Request traffic",
                "unit": "requests_per_minute",
                "total_requests": received_count,
                "rate_per_minute": rate_per_minute,
                "threshold": {"aggregation": "rate_per_minute", "operator": "gte", "value": 1},
                "series": [
                    {"minute": m, "count": cnt}
                    for m, cnt in sorted(traffic_minute_buckets.items())
                ],
            },
            "errors": {
                "title": "Error rate and retrieval success",
                "unit": "percent",
                "error_rate_pct": error_rate_pct,
                "retrieval_success_rate_pct": retrieval_success_rate_pct,
                "error_types": error_types,
                "threshold": {"aggregation": "error_rate_pct", "operator": "lte", "value": 2},
            },
            "cost": {
                "title": "Cost over time",
                "unit": "usd",
                "total": round(cost_total, 6),
                "threshold": {"aggregation": "total", "operator": "lte", "value": 2.5},
                "series": [
                    {"minute": m, "cost": round(c, 6)}
                    for m, c in sorted(cost_minute_buckets.items())
                ],
            },
            "tokens": {
                "title": "Input and output tokens",
                "unit": "tokens",
                "tokens_in": tokens_in_total,
                "tokens_out": tokens_out_total,
                "total_tokens": tokens_in_total + tokens_out_total,
                "threshold": {"aggregation": "sum_by_field", "operator": "lte", "value": 50000},
                "series": [
                    {"minute": m, "in": b["in"], "out": b["out"]}
                    for m, b in sorted(tokens_minute_buckets.items())
                ],
            },
            "quality": {
                "title": "Quality proxy",
                "unit": "score_0_to_1",
                "mean": avg_quality,
                "threshold": {"aggregation": "mean", "operator": "gte", "value": 0.75},
            },
        },
    }
