from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.cli import configure_utf8_stdio
from app.dashboard import load_dashboard_data

CONFIG_PATH = REPO_ROOT / "config" / "dashboard.yaml"
LOG_PATH = REPO_ROOT / "data" / "logs.jsonl"

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>K4-L3B Day 13 Monitoring & LLMOps Dashboard</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #090d16;
      --card-bg: rgba(17, 24, 39, 0.85);
      --card-border: rgba(255, 255, 255, 0.08);
      --card-hover-border: rgba(99, 102, 241, 0.4);
      --text: #f3f4f6;
      --text-muted: #9ca3af;
      --primary: #6366f1;
      --primary-light: #818cf8;
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
      --cyan: #06b6d4;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background-color: var(--bg);
      background-image: 
        radial-gradient(at 0% 0%, rgba(99, 102, 241, 0.12) 0px, transparent 50%),
        radial-gradient(at 100% 100%, rgba(6, 182, 212, 0.08) 0px, transparent 50%);
      color: var(--text);
      font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
      min-height: 100vh;
      padding: 24px;
    }
    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 24px;
      border-bottom: 1px solid var(--card-border);
      margin-bottom: 24px;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 14px;
    }
    .logo-badge {
      width: 44px;
      height: 44px;
      border-radius: 12px;
      background: linear-gradient(135deg, #6366f1, #06b6d4);
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 20px;
      color: white;
      box-shadow: 0 0 20px rgba(99, 102, 241, 0.4);
    }
    h1 {
      font-size: 22px;
      font-weight: 700;
      letter-spacing: -0.02em;
    }
    .subtitle {
      font-size: 13px;
      color: var(--text-muted);
    }
    .meta-bar {
      display: flex;
      align-items: center;
      gap: 16px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 12px;
    }
    .badge {
      padding: 6px 12px;
      border-radius: 9999px;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--card-border);
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }
    .badge-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--success);
      box-shadow: 0 0 8px var(--success);
      animation: pulse 2s infinite;
    }
    @keyframes pulse {
      0% { opacity: 1; }
      50% { opacity: 0.4; }
      100% { opacity: 1; }
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 20px;
    }
    @media (max-width: 1200px) { .grid { grid-template-columns: repeat(2, 1fr); } }
    @media (max-width: 768px) { .grid { grid-template-columns: 1fr; } }
    
    .card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      padding: 20px;
      backdrop-filter: blur(12px);
      transition: all 0.2s ease;
      display: flex;
      flex-direction: column;
      position: relative;
      overflow: hidden;
    }
    .card:hover {
      border-color: var(--card-hover-border);
      transform: translateY(-2px);
    }
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 16px;
    }
    .card-title {
      font-size: 14px;
      font-weight: 600;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    .card-unit {
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      color: var(--cyan);
      background: rgba(6, 182, 212, 0.1);
      padding: 2px 8px;
      border-radius: 6px;
    }
    .main-metric {
      font-size: 36px;
      font-weight: 800;
      font-family: 'JetBrains Mono', monospace;
      letter-spacing: -0.03em;
      margin-bottom: 6px;
      display: flex;
      align-items: baseline;
      gap: 8px;
    }
    .metric-sub {
      font-size: 13px;
      color: var(--text-muted);
      font-family: 'Plus Jakarta Sans', sans-serif;
      font-weight: 500;
    }
    .submetrics {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 8px;
      margin-top: 14px;
      padding-top: 14px;
      border-top: 1px solid var(--card-border);
    }
    .submetric-box {
      background: rgba(0, 0, 0, 0.2);
      border-radius: 8px;
      padding: 8px 10px;
      font-family: 'JetBrains Mono', monospace;
    }
    .submetric-label {
      font-size: 11px;
      color: var(--text-muted);
      display: block;
      margin-bottom: 4px;
    }
    .submetric-value {
      font-size: 14px;
      font-weight: 600;
    }
    .threshold-badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-size: 11px;
      font-family: 'JetBrains Mono', monospace;
      margin-top: 12px;
      padding: 4px 8px;
      border-radius: 6px;
    }
    .threshold-ok {
      background: rgba(16, 185, 129, 0.12);
      color: var(--success);
      border: 1px solid rgba(16, 185, 129, 0.25);
    }
    .threshold-breach {
      background: rgba(239, 68, 68, 0.15);
      color: var(--danger);
      border: 1px solid rgba(239, 68, 68, 0.35);
      font-weight: 700;
    }
    .sparkline-svg {
      width: 100%;
      height: 60px;
      margin-top: 14px;
    }
    .footer {
      margin-top: 32px;
      padding-top: 16px;
      border-top: 1px solid var(--card-border);
      display: flex;
      justify-content: space-between;
      color: var(--text-muted);
      font-size: 12px;
      font-family: 'JetBrains Mono', monospace;
    }
  </style>
</head>
<body>
  <div class="header">
    <div class="brand">
      <div class="logo-badge">M</div>
      <div>
        <h1 id="dash-title">K4-L3B Day 13 Monitoring & LLMOps</h1>
        <div class="subtitle" id="dash-subtitle">Real-time Observability: Metrics &rarr; Logs &rarr; Traces &rarr; Root Cause</div>
      </div>
    </div>
    <div class="meta-bar">
      <div class="badge"><div class="badge-dot"></div> LIVE REFRESH (30s)</div>
      <div class="badge" id="time-window">WINDOW: LAST 60M (UTC)</div>
      <div class="badge" id="record-count">0 RECORDS</div>
    </div>
  </div>

  <div class="grid">
    <!-- Panel 1: Latency -->
    <div class="card" id="panel-latency">
      <div class="card-header">
        <span class="card-title">1. Latency & TTFT</span>
        <span class="card-unit">ms</span>
      </div>
      <div class="main-metric" id="latency-p95">--<span class="metric-sub">P95</span></div>
      <div id="latency-threshold" class="threshold-badge threshold-ok">Target: P95 &le; 3000 ms</div>
      <div class="submetrics">
        <div class="submetric-box">
          <span class="submetric-label">P50</span>
          <span class="submetric-value" id="latency-p50">--</span>
        </div>
        <div class="submetric-box">
          <span class="submetric-label">P99</span>
          <span class="submetric-value" id="latency-p99">--</span>
        </div>
        <div class="submetric-box">
          <span class="submetric-label">TTFT P95</span>
          <span class="submetric-value" id="latency-ttft">--</span>
        </div>
      </div>
    </div>

    <!-- Panel 2: Traffic -->
    <div class="card" id="panel-traffic">
      <div class="card-header">
        <span class="card-title">2. Request Traffic</span>
        <span class="card-unit">req/min</span>
      </div>
      <div class="main-metric" id="traffic-rate">--<span class="metric-sub">req/min</span></div>
      <div id="traffic-threshold" class="threshold-badge threshold-ok">Target: Rate &ge; 1 req/min</div>
      <div class="submetrics">
        <div class="submetric-box" style="grid-column: span 3;">
          <span class="submetric-label">Total Requests In Window</span>
          <span class="submetric-value" id="traffic-total">--</span>
        </div>
      </div>
    </div>

    <!-- Panel 3: Errors & Retrieval -->
    <div class="card" id="panel-errors">
      <div class="card-header">
        <span class="card-title">3. Error Rate & Retrieval</span>
        <span class="card-unit">percent</span>
      </div>
      <div class="main-metric" id="error-rate">--%<span class="metric-sub">Error Rate</span></div>
      <div id="error-threshold" class="threshold-badge threshold-ok">Target: Error &le; 2%</div>
      <div class="submetrics">
        <div class="submetric-box" style="grid-column: span 2;">
          <span class="submetric-label">Retrieval Success</span>
          <span class="submetric-value" id="retrieval-success">--%</span>
        </div>
        <div class="submetric-box">
          <span class="submetric-label">Failed Types</span>
          <span class="submetric-value" id="error-breakdown">0</span>
        </div>
      </div>
    </div>

    <!-- Panel 4: Cost -->
    <div class="card" id="panel-cost">
      <div class="card-header">
        <span class="card-title">4. Cost Over Time</span>
        <span class="card-unit">usd</span>
      </div>
      <div class="main-metric" id="cost-total">$0.000<span class="metric-sub">Total</span></div>
      <div id="cost-threshold" class="threshold-badge threshold-ok">Target: Total &le; $2.50</div>
      <div class="submetrics">
        <div class="submetric-box" style="grid-column: span 3;">
          <span class="submetric-label">Model Pricing Tier</span>
          <span class="submetric-value" style="font-size: 12px;">$3/M In &middot; $15/M Out</span>
        </div>
      </div>
    </div>

    <!-- Panel 5: Tokens -->
    <div class="card" id="panel-tokens">
      <div class="card-header">
        <span class="card-title">5. Input & Output Tokens</span>
        <span class="card-unit">tokens</span>
      </div>
      <div class="main-metric" id="tokens-total">--<span class="metric-sub">Total Tokens</span></div>
      <div id="tokens-threshold" class="threshold-badge threshold-ok">Target: Tokens &le; 50,000</div>
      <div class="submetrics">
        <div class="submetric-box">
          <span class="submetric-label">Tokens In</span>
          <span class="submetric-value" id="tokens-in">--</span>
        </div>
        <div class="submetric-box">
          <span class="submetric-label">Tokens Out</span>
          <span class="submetric-value" id="tokens-out">--</span>
        </div>
        <div class="submetric-box">
          <span class="submetric-label">Avg/Req</span>
          <span class="submetric-value" id="tokens-avg">--</span>
        </div>
      </div>
    </div>

    <!-- Panel 6: Quality -->
    <div class="card" id="panel-quality">
      <div class="card-header">
        <span class="card-title">6. Quality Proxy</span>
        <span class="card-unit">score [0..1]</span>
      </div>
      <div class="main-metric" id="quality-mean">--<span class="metric-sub">Mean Score</span></div>
      <div id="quality-threshold" class="threshold-badge threshold-ok">Target: Score &ge; 0.75</div>
      <div class="submetrics">
        <div class="submetric-box" style="grid-column: span 3;">
          <span class="submetric-label">Quality Heuristic Signals</span>
          <span class="submetric-value" style="font-size: 12px;">Doc presence &middot; Length &middot; Keyword match</span>
        </div>
      </div>
    </div>
  </div>

  <div class="footer">
    <span>Contract: config/dashboard.yaml &middot; Source: data/logs.jsonl</span>
    <span id="last-updated">Last Updated: --</span>
  </div>

  <script>
    async function updateDashboard() {
      try {
        const res = await fetch('/api/metrics');
        if (!res.ok) return;
        const d = await res.json();
        
        document.getElementById('record-count').innerText = `${d.total_records_in_window} RECORDS`;
        document.getElementById('last-updated').innerText = `Last Updated: ${new Date().toISOString()}`;
        
        // Latency
        const lat = d.panels.latency;
        document.getElementById('latency-p95').innerHTML = `${lat.p95 !== null ? Math.round(lat.p95) : '--'}<span class="metric-sub">P95 ms</span>`;
        document.getElementById('latency-p50').innerText = lat.p50 !== null ? `${Math.round(lat.p50)} ms` : '--';
        document.getElementById('latency-p99').innerText = lat.p99 !== null ? `${Math.round(lat.p99)} ms` : '--';
        document.getElementById('latency-ttft').innerText = lat.ttft_p95 !== null ? `${Math.round(lat.ttft_p95)} ms` : '--';
        const latThresh = document.getElementById('latency-threshold');
        if (lat.p95 !== null && lat.p95 > 3000) {
          latThresh.className = 'threshold-badge threshold-breach';
          latThresh.innerText = `BREACH: P95 ${Math.round(lat.p95)} ms > 3000 ms`;
        } else {
          latThresh.className = 'threshold-badge threshold-ok';
          latThresh.innerText = `OK: P95 &le; 3000 ms`;
        }

        // Traffic
        const traf = d.panels.traffic;
        document.getElementById('traffic-rate').innerHTML = `${traf.rate_per_minute !== null ? traf.rate_per_minute : '--'}<span class="metric-sub">req/min</span>`;
        document.getElementById('traffic-total').innerText = `${traf.total_requests} requests`;

        // Errors
        const err = d.panels.errors;
        const errPct = err.error_rate_pct !== null ? err.error_rate_pct : 0;
        document.getElementById('error-rate').innerHTML = `${errPct}%<span class="metric-sub">Error Rate</span>`;
        document.getElementById('retrieval-success').innerText = err.retrieval_success_rate_pct !== null ? `${err.retrieval_success_rate_pct}%` : '100%';
        const errThresh = document.getElementById('error-threshold');
        if (errPct > 2) {
          errThresh.className = 'threshold-badge threshold-breach';
          errThresh.innerText = `BREACH: Error rate ${errPct}% > 2%`;
        } else {
          errThresh.className = 'threshold-badge threshold-ok';
          errThresh.innerText = `OK: Error rate &le; 2%`;
        }
        const errCount = Object.values(err.error_types || {}).reduce((a, b) => a + b, 0);
        document.getElementById('error-breakdown').innerText = `${errCount} errs`;

        // Cost
        const cst = d.panels.cost;
        document.getElementById('cost-total').innerHTML = `$${cst.total.toFixed(4)}<span class="metric-sub">USD</span>`;

        // Tokens
        const tok = d.panels.tokens;
        document.getElementById('tokens-total').innerHTML = `${tok.total_tokens.toLocaleString()}<span class="metric-sub">Tokens</span>`;
        document.getElementById('tokens-in').innerText = tok.tokens_in.toLocaleString();
        document.getElementById('tokens-out').innerText = tok.tokens_out.toLocaleString();
        const avgTok = traf.total_requests > 0 ? Math.round(tok.total_tokens / traf.total_requests) : 0;
        document.getElementById('tokens-avg').innerText = avgTok.toLocaleString();

        // Quality
        const q = d.panels.quality;
        document.getElementById('quality-mean').innerHTML = `${q.mean !== null ? q.mean : '--'}<span class="metric-sub">Mean</span>`;
        const qThresh = document.getElementById('quality-threshold');
        if (q.mean !== null && q.mean < 0.75) {
          qThresh.className = 'threshold-badge threshold-breach';
          qThresh.innerText = `BREACH: Quality ${q.mean} < 0.75`;
        } else {
          qThresh.className = 'threshold-badge threshold-ok';
          qThresh.innerText = `OK: Score &ge; 0.75`;
        }

      } catch (e) {
        console.error("Dashboard refresh error:", e);
      }
    }
    updateDashboard();
    setInterval(updateDashboard, 30000);
  </script>
</body>
</html>
"""


class DashboardRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/" or self.path == "/index.html":
            content = HTML_TEMPLATE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        elif self.path.startswith("/api/metrics"):
            data = load_dashboard_data(LOG_PATH, CONFIG_PATH)
            body = json.dumps(data).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format: str, *args) -> None:
        pass  # Suppress default server access logs in stdout


def main() -> None:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description="K4-L3B Day 13 Local Dashboard Server")
    parser.add_argument("--port", type=int, default=8501, help="Port to bind (default: 8501)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host (default: 127.0.0.1)")
    args = parser.parse_args()

    server_address = (args.host, args.port)
    httpd = HTTPServer(server_address, DashboardRequestHandler)
    print(f"Observability Dashboard running on http://{args.host}:{args.port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping dashboard server...")
        httpd.server_close()


if __name__ == "__main__":
    main()
