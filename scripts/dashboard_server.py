"""Dashboard runtime local: đọc data/logs.jsonl và hiển thị 6 panel theo config/dashboard.yaml.

Chạy: python scripts/dashboard_server.py  ->  mở http://127.0.0.1:8765
Tham số: --port, --window (phút, mặc định 60), --logs.
"""

import argparse
import json
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
THRESHOLDS = {"p95_ms": 3000, "traffic_rpm": 1, "error_pct": 2, "cost_total": 2.5, "tokens_total": 50000, "quality": 0.75}
INCIDENT_MS = 2000  # ngưỡng challenge (config/challenge.json)


def pct(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = (len(s) - 1) * q / 100
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def load(logs: Path, window: int) -> dict:
    rows = []
    for line in logs.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    now = datetime.now(timezone.utc)
    start = now - timedelta(minutes=window)
    inwin = []
    for r in rows:
        try:
            ts = datetime.fromisoformat(r["ts"].replace("Z", "+00:00"))
        except (KeyError, ValueError):
            continue
        if ts >= start:
            inwin.append((ts, r))
    resp = [(t, r) for t, r in inwin if r.get("event") == "response_sent"]
    reqs = [(t, r) for t, r in inwin if r.get("event") == "request_received"]
    fails = [(t, r) for t, r in inwin if r.get("event") == "request_failed"]
    lat = [r["latency_ms"] for _, r in resp]
    ttft = [r["ttft_ms"] for _, r in resp]

    def by_min(items, fn):
        out = {}
        for t, r in items:
            k = t.replace(second=0, microsecond=0).isoformat()
            out.setdefault(k, []).append(fn(r))
        return out

    tool = [r.get("tool_success") for _, r in resp if r.get("tool_success") is not None]
    slow = sorted(({"ts": r["ts"], "latency_ms": r["latency_ms"], "correlation_id": r["correlation_id"],
                    "feature": r.get("feature")} for _, r in resp if r["latency_ms"] > INCIDENT_MS),
                  key=lambda x: -x["latency_ms"])
    return {
        "window_min": window,
        "start": start.isoformat(), "end": now.isoformat(),
        "latency": {"p50": pct(lat, 50), "p95": pct(lat, 95), "p99": pct(lat, 99), "ttft_p95": pct(ttft, 95),
                    "series": [{"t": t.isoformat(), "v": r["latency_ms"]} for t, r in resp]},
        "traffic": {"count": len(reqs), "rpm": len(reqs) / window,
                    "series": {k: len(v) for k, v in by_min(reqs, lambda r: 1).items()}},
        "errors": {"error_pct": 100 * len(fails) / len(reqs) if reqs else 0.0, "failed": len(fails),
                   "retrieval_success_pct": 100 * sum(1 for x in tool if x) / len(tool) if tool else 100.0},
        "cost": {"total": sum(r["cost_usd"] for _, r in resp),
                 "series": {k: sum(v) for k, v in by_min(resp, lambda r: r["cost_usd"]).items()}},
        "tokens": {"in": sum(r["tokens_in"] for _, r in resp), "out": sum(r["tokens_out"] for _, r in resp)},
        "quality": {"mean": sum(r["quality_score"] for _, r in resp) / len(resp) if resp else 0.0,
                    "series": {k: sum(v) / len(v) for k, v in by_min(resp, lambda r: r["quality_score"]).items()}},
        "slow": slow[:6], "thresholds": THRESHOLDS, "incident_ms": INCIDENT_MS,
    }


PAGE = r"""<!doctype html><html lang="vi"><head><meta charset="utf-8"><title>K4-L3B Day 13 Monitoring &amp; LLMOps</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root{--bg:#0f1115;--card:#171a21;--bd:#2a2f3a;--tx:#e6e8ee;--mu:#8b93a5;--ok:#3ecf8e;--bad:#ff6b6b;--ln:#6ea8fe;--th:#f5a623}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--tx);font:14px/1.4 system-ui,Segoe UI,sans-serif;padding:16px}
h1{font-size:18px;margin:0}.sub{color:var(--mu);font-size:12px;margin:2px 0 14px}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}@media(max-width:900px){.grid{grid-template-columns:1fr}}
.card{background:var(--card);border:1px solid var(--bd);border-radius:8px;padding:12px}
.card h2{font-size:13px;margin:0 0 2px}.unit{color:var(--mu);font-size:11px}
.big{font-size:26px;font-weight:600;margin:6px 0}.row{display:flex;gap:14px;flex-wrap:wrap;color:var(--mu);font-size:12px}
.row b{color:var(--tx)}.bad{color:var(--bad)!important}.ok{color:var(--ok)}canvas{width:100%;height:120px;display:block;margin-top:6px}
.th{color:var(--th);font-size:11px}table{width:100%;border-collapse:collapse;font-size:12px;margin-top:10px}
td,th{text-align:left;padding:3px 6px;border-bottom:1px solid var(--bd)}th{color:var(--mu);font-weight:500}
.banner{margin-bottom:12px;padding:8px 12px;border:1px solid var(--bad);border-radius:8px;color:var(--bad);font-size:13px}
</style></head><body>
<h1>K4-L3B Day 13 Monitoring &amp; LLMOps</h1>
<div class="sub" id="sub"></div><div id="banner"></div>
<div class="grid">
<div class="card"><h2>Latency percentiles and TTFT</h2><span class="unit">ms · threshold P95 ≤ 3000</span><div class="big" id="lat"></div><div class="row" id="latr"></div><canvas id="c1"></canvas></div>
<div class="card"><h2>Request traffic</h2><span class="unit">requests_per_minute · threshold ≥ 1</span><div class="big" id="tr"></div><div class="row" id="trr"></div><canvas id="c2"></canvas></div>
<div class="card"><h2>Error rate and retrieval success</h2><span class="unit">percent · threshold error ≤ 2%</span><div class="big" id="er"></div><div class="row" id="err"></div></div>
<div class="card"><h2>Cost over time</h2><span class="unit">usd · threshold total ≤ 2.5</span><div class="big" id="co"></div><canvas id="c4"></canvas></div>
<div class="card"><h2>Input and output tokens</h2><span class="unit">tokens · threshold total ≤ 50000</span><div class="big" id="tk"></div><div class="row" id="tkr"></div></div>
<div class="card"><h2>Quality proxy</h2><span class="unit">score 0–1 · threshold mean ≥ 0.75</span><div class="big" id="qu"></div><canvas id="c6"></canvas></div>
</div>
<div class="card" style="margin-top:12px"><h2>Slow requests (latency &gt; <span id="inc"></span> ms) — dùng correlation_id để mở trace</h2>
<table><thead><tr><th>ts (UTC)</th><th>correlation_id</th><th>feature</th><th>latency_ms</th></tr></thead><tbody id="slow"></tbody></table></div>
<script>
const $=id=>document.getElementById(id), f=(x,d=0)=>Number(x).toFixed(d);
function line(cv,pts,th,color,fmt){const dpr=devicePixelRatio||1,w=cv.clientWidth,h=cv.clientHeight;cv.width=w*dpr;cv.height=h*dpr;
 const g=cv.getContext('2d');g.scale(dpr,dpr);g.clearRect(0,0,w,h);if(!pts.length)return;
 const xs=pts.map(p=>p.x),xmin=Math.min(...xs),xmax=Math.max(...xs)||1,ymax=Math.max(...pts.map(p=>p.y),th||0)*1.15||1,L=40;
 const X=x=>L+(xmax===xmin?0.5:(x-xmin)/(xmax-xmin))*(w-L-6),Y=y=>h-14-(y/ymax)*(h-22);
 g.strokeStyle='#2a2f3a';g.fillStyle='#8b93a5';g.font='10px sans-serif';
 for(let i=0;i<=2;i++){const y=ymax*i/2;g.beginPath();g.moveTo(L,Y(y));g.lineTo(w,Y(y));g.stroke();g.fillText(fmt(y),2,Y(y)+3)}
 if(th!=null){g.strokeStyle='#f5a623';g.setLineDash([4,3]);g.beginPath();g.moveTo(L,Y(th));g.lineTo(w,Y(th));g.stroke();g.setLineDash([]);g.fillStyle='#f5a623';g.fillText('threshold '+fmt(th),L+4,Y(th)-3)}
 g.strokeStyle=color;g.fillStyle=color;g.lineWidth=1.5;g.beginPath();pts.forEach((p,i)=>i?g.lineTo(X(p.x),Y(p.y)):g.moveTo(X(p.x),Y(p.y)));g.stroke();
 pts.forEach(p=>{g.beginPath();g.arc(X(p.x),Y(p.y),2.5,0,7);g.fill()});
 const a=new Date(xmin),b=new Date(xmax),t=d=>d.toISOString().substr(11,5);g.fillStyle='#8b93a5';g.fillText(t(a),L,h-2);g.fillText(t(b)+'Z',w-38,h-2)}
const ser=o=>Object.entries(o).sort().map(([k,v])=>({x:Date.parse(k),y:v}));
async function draw(){const d=await (await fetch('/api'+location.search)).json(),T=d.thresholds;
 $('sub').textContent=`Time range: last ${d.window_min} min · ${d.start.substr(0,19)}Z → ${d.end.substr(0,19)}Z · refresh 30s · source data/logs.jsonl`;
 const L=d.latency;$('lat').innerHTML=`P95 <span class="${L.p95>T.p95_ms?'bad':'ok'}">${f(L.p95)} ms</span>`;
 $('latr').innerHTML=`<span>P50 <b>${f(L.p50)}</b></span><span>P95 <b>${f(L.p95)}</b></span><span>P99 <b>${f(L.p99)}</b></span><span>TTFT P95 <b>${f(L.ttft_p95)}</b></span>`;
 line($('c1'),L.series.map(s=>({x:Date.parse(s.t),y:s.v})),T.p95_ms,'#6ea8fe',v=>f(v));
 $('tr').innerHTML=`${f(d.traffic.rpm,2)} <span class="unit">req/min avg</span>`;$('trr').innerHTML=`<span>requests <b>${d.traffic.count}</b></span>`;
 line($('c2'),ser(d.traffic.series),T.traffic_rpm,'#3ecf8e',v=>f(v,1));
 $('er').innerHTML=`<span class="${d.errors.error_pct>T.error_pct?'bad':'ok'}">${f(d.errors.error_pct,1)} %</span> <span class="unit">error rate</span>`;
 $('err').innerHTML=`<span>failed <b>${d.errors.failed}</b></span><span>retrieval success <b>${f(d.errors.retrieval_success_pct,1)}%</b></span>`;
 $('co').innerHTML=`$${f(d.cost.total,4)} <span class="unit">total</span>`;line($('c4'),ser(d.cost.series),null,'#c792ea',v=>f(v,4));
 $('tk').innerHTML=`${d.tokens.in+d.tokens.out} <span class="unit">total</span>`;$('tkr').innerHTML=`<span>tokens_in <b>${d.tokens.in}</b></span><span>tokens_out <b>${d.tokens.out}</b></span>`;
 $('qu').innerHTML=`<span class="${d.quality.mean<T.quality?'bad':'ok'}">${f(d.quality.mean,3)}</span> <span class="unit">mean</span>`;line($('c6'),ser(d.quality.series),T.quality,'#ffd166',v=>f(v,2));
 $('inc').textContent=d.incident_ms;$('slow').innerHTML=d.slow.map(s=>`<tr><td>${s.ts.substr(0,19)}</td><td>${s.correlation_id}</td><td>${s.feature}</td><td class="bad">${s.latency_ms}</td></tr>`).join('')||'<tr><td colspan=4>không có</td></tr>';
 $('banner').innerHTML=d.slow.length?`<div class="banner">⚠ Incident: ${d.slow.length}+ request vượt ${d.incident_ms} ms — P95 ${f(L.p95)} ms, TTFT P95 ${f(L.ttft_p95)} ms, lỗi ${f(d.errors.error_pct,1)}% → chậm nhưng không lỗi</div>`:''}
draw();setInterval(draw,30000);
</script></body></html>"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--window", type=int, default=60)
    ap.add_argument("--logs", default=str(REPO_ROOT / "data" / "logs.jsonl"))
    args = ap.parse_args()
    logs = Path(args.logs)

    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.startswith("/api"):
                body, ctype = json.dumps(load(logs, args.window)).encode(), "application/json"
            else:
                body, ctype = PAGE.encode(), "text/html; charset=utf-8"
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    print(f"Dashboard: http://127.0.0.1:{args.port}  (window={args.window}m, logs={logs})")
    ThreadingHTTPServer(("127.0.0.1", args.port), H).serve_forever()


if __name__ == "__main__":
    main()
