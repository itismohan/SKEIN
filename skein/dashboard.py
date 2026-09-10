"""Generate a self-contained, branded Skein AI-DLC Control Panel."""
from __future__ import annotations

import base64
import hashlib
import json
from html import escape
from pathlib import Path

from .compression.telemetry import CompressionTelemetry
from .control_plane import ControlPlane
from .telemetry import TelemetryStore
from .versioning import VersionedGraphStore


def _logo_data_uri() -> str:
    """Return the bundled Skein logo as a data URI so the panel stays portable."""
    logo = Path(__file__).resolve().parent / "assets" / "skein-logo.png"
    if not logo.exists():
        return ""
    encoded = base64.b64encode(logo.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def snapshot(root: Path) -> dict:
    history = root / ".skein" / "history"
    telemetry = TelemetryStore(history).aggregate()
    compression = CompressionTelemetry(history).health()
    versioned = VersionedGraphStore(history)
    commits = list(versioned.commits())
    control = None
    control_path = root / ".skein" / "control-plane.json"
    if control_path.exists():
        try:
            control = ControlPlane(root).status()
        except (ValueError, json.JSONDecodeError):
            control = None
    return {
        "commits": [
            {"id": c.commit_id, "timestamp": c.timestamp, "author": c.author,
             "message": c.message, "spec_refs": c.spec_refs}
            for c in commits
        ],
        "cost": telemetry,
        "compression": compression,
        "conflicts": len(versioned.conflicts()),
        "control": control,
    }


def _control_card(control: dict | None) -> str:
    if not control:
        return """<section class="panel control-empty"><div><span class="eyebrow">CONTROL PLANE</span>
<h2>No active control-plane run</h2><p>Initialize a governed AI-DLC run with <code>skein control-init</code>.</p></div>
<a class="button" href="#quick-start">Open quick start</a></section>"""
    run = control["run"]
    task = run["task"]
    state = escape(run["state"].replace("_", " ").title())
    score = "—" if run.get("quality_score") is None else f"{float(run['quality_score']):.0%}"
    return f"""<section class="panel control-card"><div class="panel-head"><div><span class="eyebrow">ACTIVE CONTROL PLANE</span>
<h2>{escape(task['title'])}</h2><p>{escape(task['description'])}</p></div><span class="status status-{escape(run['state'])}">{state}</span></div>
<div class="control-metrics"><div><span>Run</span><strong>{escape(run['run_id'])}</strong></div><div><span>Risk</span><strong>{escape(task.get('risk','medium').upper())}</strong></div>
<div><span>Quality</span><strong>{score}</strong></div><div><span>Events</span><strong>{control['event_count']}</strong></div></div>
<div class="lifecycle"><span class="done">CREATED</span><i></i><span class="done">PLANNED</span><i></i><span class="active">EXECUTING</span><i></i><span>EVALUATING</span><i></i><span>APPROVAL</span><i></i><span>COMPLETED</span></div></section>"""


def render(root: Path) -> str:
    data = snapshot(root)
    logo = _logo_data_uri()
    stage_rows = "".join(
        f"<tr><td>{escape(k)}</td><td>{v['calls']}</td><td>{v['input_tokens']}</td><td>{v['output_tokens']}</td><td>{v['reasoning_tokens']}</td><td>${v['cost_usd']:.4f}</td></tr>"
        for k, v in data["cost"]["by_stage"].items()
    )
    commit_rows = "".join(
        f"<tr><td><code>{escape(c['id'])}</code></td><td>{escape(c['timestamp'])}</td><td>{escape(c['author'])}</td><td>{escape(c['message'])}</td><td>{escape(','.join(c['spec_refs']))}</td></tr>"
        for c in data["commits"][-20:][::-1]
    )
    logo_html = f'<img class="logo" src="{logo}" alt="Skein — The Continuous Thread of AI-DLC">' if logo else '<div class="wordmark">Skein</div>'
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Skein AI-DLC Control Panel — Skein Governance Dashboard</title>
<style>
:root{{--ink:#101a3a;--muted:#65708a;--line:#e3e8f2;--bg:#f6f8fc;--card:#fff;--blue:#1769ff;--purple:#7a2cff;--pink:#ef3da8;--orange:#ff7a2d;--nav:#10192b}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
.app{{display:flex;min-height:100vh}}aside{{width:245px;background:linear-gradient(180deg,#111b2f,#0b1221);color:#fff;padding:22px 16px;position:sticky;top:0;height:100vh}}
.brand{{padding:4px 10px 28px;border-bottom:1px solid #29334a;margin-bottom:16px}}.brand .mini-logo{{width:190px;height:82px;object-fit:contain;object-position:left center;filter:drop-shadow(0 8px 14px rgba(0,0,0,.2))}}
.nav a{{display:block;color:#b9c4d8;text-decoration:none;padding:11px 12px;border-radius:9px;margin:3px 0;font-size:14px}}.nav a.active,.nav a:hover{{background:#1d6cff;color:white}}
.nav .section{{font-size:10px;letter-spacing:1.5px;color:#66738b;margin:20px 12px 7px;font-weight:700}}
main{{flex:1;padding:30px 38px;max-width:1450px;margin:0 auto;width:100%}}.top{{display:flex;align-items:center;justify-content:space-between;margin-bottom:24px}}
.top h1{{font-size:28px;margin:0 0 5px}}.top p{{margin:0;color:var(--muted)}}.pill{{background:#eaf1ff;color:#185ce0;padding:8px 12px;border-radius:999px;font-size:12px;font-weight:700}}
.hero{{background:linear-gradient(110deg,#edf7ff,#fff5fd);border:1px solid #dce7fb;border-radius:18px;padding:18px 24px;display:flex;align-items:center;justify-content:space-between;min-height:165px;overflow:hidden;position:relative}}
.hero:after{{content:"";position:absolute;width:320px;height:320px;border-radius:50%;right:-140px;top:-180px;background:linear-gradient(135deg,rgba(23,105,255,.12),rgba(239,61,168,.1));}}
.hero-logo{{width:520px;max-width:58%;height:145px;object-fit:contain;object-position:left center;position:relative;z-index:1}}.hero-copy{{max-width:410px;position:relative;z-index:1}}.hero-copy strong{{font-size:18px}}.hero-copy p{{color:#5d6780;line-height:1.5;margin:8px 0 0}}
.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:18px 0}}.metric-card,.panel{{background:var(--card);border:1px solid var(--line);border-radius:14px;box-shadow:0 5px 18px rgba(18,32,67,.04)}}.metric-card{{padding:18px}}.metric-card span,.control-metrics span{{display:block;color:var(--muted);font-size:12px}}.metric-card strong{{font-size:29px;display:block;margin-top:6px}}.delta{{font-size:12px;color:#159447;margin-top:6px}}
.panel{{padding:20px;margin-top:16px}}.panel-head{{display:flex;justify-content:space-between;gap:20px;align-items:flex-start}}.panel h2{{margin:4px 0 6px;font-size:18px}}.panel p{{color:var(--muted);margin:0;line-height:1.45}}.eyebrow{{font-size:10px;letter-spacing:1.5px;font-weight:800;color:var(--blue)}}
.status{{padding:7px 10px;border-radius:999px;font-size:11px;font-weight:800;background:#eef3fa;color:#506078;white-space:nowrap}}.status-executing{{background:#e8f1ff;color:#1769ff}}.status-completed{{background:#e8f8ef;color:#128447}}.status-approval_required{{background:#fff1df;color:#d56712}}.status-failed,.status-rejected{{background:#ffe8e8;color:#c43c3c}}
.control-metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:20px}}.control-metrics div{{background:#f7f9fd;border:1px solid #e9edf5;border-radius:10px;padding:12px}}.control-metrics strong{{display:block;margin-top:5px;font-size:15px;overflow:hidden;text-overflow:ellipsis}}
.lifecycle{{display:flex;align-items:center;margin-top:20px;font-size:9px;font-weight:800;letter-spacing:.7px;color:#9aa4b7;white-space:nowrap}}.lifecycle span{{padding:7px 8px;border-radius:999px;background:#f0f3f8}}.lifecycle .done{{color:#16864a;background:#e8f8ef}}.lifecycle .active{{color:#1769ff;background:#e8f1ff}}.lifecycle i{{height:1px;background:#d7deea;flex:1;margin:0 5px}}
.two{{display:grid;grid-template-columns:1.25fr .75fr;gap:16px}}table{{border-collapse:collapse;width:100%;margin-top:14px;font-size:12px}}th,td{{border-bottom:1px solid var(--line);padding:10px 8px;text-align:left}}th{{font-size:10px;text-transform:uppercase;letter-spacing:.7px;color:#78839a}}code{{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}}pre{{background:#0d1526;color:#d9e3f7;border-radius:10px;padding:15px;overflow:auto;font-size:11px}}.button{{display:inline-block;text-decoration:none;background:var(--blue);color:#fff;padding:10px 14px;border-radius:9px;font-size:12px;font-weight:700}}.control-empty{{display:flex;align-items:center;justify-content:space-between}}footer{{color:#7c879d;font-size:11px;padding:22px 2px 4px}}
@media(max-width:900px){{aside{{display:none}}main{{padding:20px}}.grid{{grid-template-columns:repeat(2,1fr)}}.two{{grid-template-columns:1fr}}.hero-logo{{max-width:52%}}}}@media(max-width:560px){{.grid,.control-metrics{{grid-template-columns:1fr}}.hero{{display:block}}.hero-logo{{max-width:100%}}.lifecycle{{overflow:auto}}}}
</style></head><body><div class="app"><aside><div class="brand">{logo_html}</div>
<nav class="nav"><div class="section">AI-DLC</div><a class="active" href="#overview">◈ Dashboard</a><a href="#control-plane">◌ Control Plane</a><a href="#specifications">▤ Specifications</a><a href="#graph">⌘ Knowledge Graph</a><a href="#agents">♧ Agents</a><a href="#execution">◷ Execution</a><a href="#quality">◌ Quality Loop</a><a href="#evidence">▣ Evidence</a><div class="section">GOVERNANCE</div><a href="#governance">◇ Governance</a><a href="#commits">▰ Projects & History</a></nav></aside>
<main id="overview"><div class="top"><div><h1>Skein AI-DLC Control Panel</h1><p>Persistent context, governed execution, quality evidence — one continuous thread.</p></div><span class="pill">v1.0.0 · LOCAL</span></div>
<section class="hero">{f'<img class="hero-logo" src="{logo}" alt="Skein — The Continuous Thread of AI-DLC">' if logo else '<div class="wordmark">Skein</div>'}<div class="hero-copy"><strong>From idea to production — one continuous thread.</strong><p>Connect specifications, engineering knowledge, agents, execution, quality, traceability and human control across AI-DLC.</p></div></section>
<div class="grid"><div class="metric-card"><span>Graph commits</span><strong>{len(data['commits'])}</strong><div class="delta">Versioned history</div></div><div class="metric-card"><span>Agent calls</span><strong>{data['cost']['events']}</strong><div class="delta">Append-only telemetry</div></div><div class="metric-card"><span>Compression pass rate</span><strong>{data['compression']['pass_rate']:.0%}</strong><div class="delta">Verified context</div></div><div class="metric-card"><span>Write conflicts</span><strong>{data['conflicts']}</strong><div class="delta">Governance signal</div></div></div>
<div id="control-plane">{_control_card(data['control'])}</div>
<div class="two"><section class="panel" id="execution"><div class="panel-head"><div><span class="eyebrow">FINOPS / TELEMETRY</span><h2>Cost by lifecycle stage</h2></div></div><table><tr><th>Stage</th><th>Calls</th><th>Input</th><th>Output</th><th>Reasoning</th><th>Cost</th></tr>{stage_rows or '<tr><td colspan="6">No telemetry yet</td></tr>'}</table></section>
<section class="panel" id="quality"><span class="eyebrow">QUALITY / COMPRESSION</span><h2>Verification health</h2><pre>{escape(json.dumps(data['compression'], indent=2))}</pre></section></div>
<section class="panel" id="commits"><span class="eyebrow">TRACEABILITY / EVIDENCE</span><h2>Structural-diff history</h2><table><tr><th>Commit</th><th>Timestamp</th><th>Author</th><th>Message</th><th>Specs</th></tr>{commit_rows or '<tr><td colspan="5">No commits yet</td></tr>'}</table></section>
<section class="panel" id="governance"><span class="eyebrow">GOVERNANCE</span><h2>Policy posture</h2><p>Conflicts: {data['conflicts']}. Audit exports should be restricted to auditor/admin identities. The control plane does not silently mutate source code or bypass quality and approval gates.</p></section>
<section class="panel" id="quick-start"><span class="eyebrow">LOCAL QUICK START</span><h2>Run Skein locally</h2><pre>pip install -e .
skein init .
skein ingest .
skein dashboard .</pre></section>
<footer>Skein v1.0.0 · The Continuous Thread of AI-DLC · Graph · Trace · Agent Communication · One strand. End to end.</footer>
</main></div></body></html>"""


def write(root: Path, output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render(root), encoding="utf-8")
    return output
