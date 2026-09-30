from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app.dashboard import load_dashboard_data, _nearest_rank_percentile


def test_nearest_rank_percentile():
    assert _nearest_rank_percentile([], 95) is None
    assert _nearest_rank_percentile([10, 20, 30, 40, 50], 50) == 30.0
    assert _nearest_rank_percentile([10, 20, 30, 40, 50], 95) == 50.0
    assert _nearest_rank_percentile([100], 99) == 100.0


def test_load_dashboard_data_empty(tmp_path: Path):
    log_file = tmp_path / "empty.jsonl"
    log_file.write_text("", encoding="utf-8")
    cfg_file = Path("config/dashboard.yaml")

    data = load_dashboard_data(log_file, cfg_file)
    assert data["total_records_in_window"] == 0
    assert data["panels"]["latency"]["p50"] is None
    assert data["panels"]["errors"]["error_rate_pct"] is None
    assert data["panels"]["cost"]["total"] == 0.0


def test_load_dashboard_data_with_records(tmp_path: Path):
    log_file = tmp_path / "test.jsonl"
    lines = [
        {"ts": "2026-09-30T10:00:00Z", "event": "request_received", "service": "api"},
        {
            "ts": "2026-09-30T10:00:01Z",
            "event": "response_sent",
            "service": "api",
            "latency_ms": 1200,
            "ttft_ms": 50,
            "tokens_in": 30,
            "tokens_out": 100,
            "cost_usd": 0.0015,
            "quality_score": 0.85,
            "tool_name": "retrieval",
            "tool_success": True,
        },
        {"ts": "2026-09-30T10:01:00Z", "event": "request_received", "service": "api"},
        {
            "ts": "2026-09-30T10:01:02Z",
            "event": "request_failed",
            "service": "api",
            "error_type": "RuntimeError",
            "tool_name": "retrieval",
            "tool_success": False,
        },
    ]
    log_file.write_text("\n".join(json.dumps(l) for l in lines) + "\n", encoding="utf-8")
    cfg_file = Path("config/dashboard.yaml")
    ref_time = datetime(2026, 9, 30, 10, 5, 0, tzinfo=timezone.utc)

    data = load_dashboard_data(log_file, cfg_file, now=ref_time)
    assert data["total_records_in_window"] == 4
    assert data["panels"]["latency"]["p50"] == 1200.0
    assert data["panels"]["traffic"]["total_requests"] == 2
    assert data["panels"]["errors"]["error_rate_pct"] == 50.0
    assert data["panels"]["errors"]["retrieval_success_rate_pct"] == 50.0
    assert data["panels"]["cost"]["total"] == 0.0015
    assert data["panels"]["tokens"]["total_tokens"] == 130
    assert data["panels"]["quality"]["mean"] == 0.85
