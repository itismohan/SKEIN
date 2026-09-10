"""Statistical evaluation of matched Baseline vs Skein pilot evidence.

No claim is emitted as statistically supported unless paired observations exist.  The
implementation uses deterministic bootstrap confidence intervals (seeded) and reports
effect size, median/mean deltas, sample size, and evidence grade.
"""
from __future__ import annotations

import json
import math
import random
import statistics
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = "0.5.0"
RESULT_NAME = ".skein/evaluation-results.json"
REPORT_NAME = ".skein/evaluation-report.md"


@dataclass(frozen=True)
class EvaluationConfig:
    bootstrap_samples: int = 2000
    confidence_level: float = 0.95
    seed: int = 42
    minimum_tasks: int = 10
    success_tolerance_pct: float = 2.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _paired_rows(root: Path) -> list[dict[str, Any]]:
    candidates = [root / ".skein" / "pilot-task-results.json", root / ".skein" / "pilot-experiment-metrics.json", root / ".skein" / "connector-task-results.json"]
    for path in candidates:
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        rows = data.get("tasks") or data.get("paired_tasks") or data.get("results")
        if isinstance(rows, list) and rows:
            grouped: dict[str, dict[str, Any]] = {}
            for row in rows:
                if not isinstance(row, dict):
                    continue
                task = str(row.get("task_id") or row.get("scenario_id") or "")
                mode = str(row.get("experiment") or row.get("mode") or "")
                if task and mode in {"baseline", "skein"}:
                    grouped.setdefault(task, {})[mode] = row
            pairs = []
            for task, pair in sorted(grouped.items()):
                if "baseline" in pair and "skein" in pair:
                    pairs.append({"task_id": task, "baseline": pair["baseline"], "skein": pair["skein"]})
            if pairs:
                return pairs
    return []


def _bootstrap_ci(values: list[float], *, samples: int, confidence: float, seed: int) -> tuple[float, float] | None:
    if not values:
        return None
    if len(values) == 1:
        return values[0], values[0]
    rng = random.Random(seed)
    means = []
    n = len(values)
    for _ in range(max(100, samples)):
        means.append(statistics.mean(rng.choices(values, k=n)))
    alpha = (1.0 - confidence) / 2.0
    means.sort()
    lo = means[max(0, int(math.floor(alpha * len(means))))]
    hi = means[min(len(means) - 1, int(math.ceil((1 - alpha) * len(means))) - 1)]
    return round(lo, 6), round(hi, 6)


def _metric_value(row: dict[str, Any], names: Iterable[str]) -> float | None:
    for name in names:
        value = row.get(name)
        if isinstance(value, (int, float)):
            return float(value)
    return None


def _paired_metric(pairs: list[dict[str, Any]], baseline_names: Iterable[str], skein_names: Iterable[str], *, higher_is_better: bool = False, config: EvaluationConfig) -> dict[str, Any]:
    deltas: list[float] = []
    baseline: list[float] = []
    skein: list[float] = []
    for pair in pairs:
        b = _metric_value(pair["baseline"], baseline_names)
        s = _metric_value(pair["skein"], skein_names)
        if b is None or s is None:
            continue
        baseline.append(b); skein.append(s)
        # Positive means improvement regardless of metric direction.
        deltas.append((s - b) if higher_is_better else (b - s))
    ci = _bootstrap_ci(deltas, samples=config.bootstrap_samples, confidence=config.confidence_level, seed=config.seed) if deltas else None
    bmean = statistics.mean(baseline) if baseline else None
    smean = statistics.mean(skein) if skein else None
    reduction_pct = None if not baseline or bmean == 0 else ((smean - bmean) / bmean * 100.0)
    if reduction_pct is not None and not higher_is_better:
        reduction_pct = -reduction_pct
    elif reduction_pct is not None:
        reduction_pct = reduction_pct
    supported = bool(ci and ci[0] > 0 and len(deltas) >= config.minimum_tasks)
    return {
        "n": len(deltas), "baseline_mean": bmean, "skein_mean": smean,
        "baseline_median": statistics.median(baseline) if baseline else None,
        "skein_median": statistics.median(skein) if skein else None,
        "improvement_pct": round(reduction_pct, 4) if reduction_pct is not None else None,
        "paired_mean_improvement": statistics.mean(deltas) if deltas else None,
        "bootstrap_ci": ci, "confidence_level": config.confidence_level,
        "statistically_supported": supported,
    }


def _success_metric(pairs: list[dict[str, Any]], config: EvaluationConfig) -> dict[str, Any]:
    def success(row: dict[str, Any]) -> bool | None:
        v = row.get("success")
        if isinstance(v, bool): return v
        if isinstance(v, (int, float)): return bool(v)
        outcome = str(row.get("outcome", "")).lower()
        return True if outcome in {"success", "passed", "pass", "ok"} else False if outcome in {"failure", "failed", "error", "fail"} else None
    b = [success(p["baseline"]) for p in pairs]; s = [success(p["skein"]) for p in pairs]
    b = [x for x in b if x is not None]; s = [x for x in s if x is not None]
    br = sum(b) / len(b) if b else None; sr = sum(s) / len(s) if s else None
    delta = (sr - br) * 100 if br is not None and sr is not None else None
    guardrail = delta is not None and delta >= -config.success_tolerance_pct
    return {"baseline_rate": br, "skein_rate": sr, "delta_percentage_points": delta, "guardrail_pass": guardrail, "n_baseline": len(b), "n_skein": len(s)}


def evaluate(root: Path, config: EvaluationConfig | None = None) -> dict[str, Any]:
    config = config or EvaluationConfig()
    pairs = _paired_rows(root.resolve())
    metrics = {
        "context_tokens": _paired_metric(pairs, ["input_tokens", "context_tokens", "total_tokens"], ["input_tokens", "context_tokens", "total_tokens"], config=config),
        "cost_usd": _paired_metric(pairs, ["cost_usd", "estimated_cost_usd"], ["cost_usd", "estimated_cost_usd"], config=config),
        "latency_ms": _paired_metric(pairs, ["latency_ms"], ["latency_ms"], config=config),
        "rework": _paired_metric(pairs, ["rework", "rework_count"], ["rework", "rework_count"], config=config),
        "handoff_loss": _paired_metric(pairs, ["handoff_loss", "handoff_loss_rate"], ["handoff_loss", "handoff_loss_rate"], config=config),
    }
    # Reinterpret success separately because it is higher-is-better.
    success = _success_metric(pairs, config)
    supported = [k for k, v in metrics.items() if v["statistically_supported"]]
    grade = "A" if len(pairs) >= 30 and supported and success["guardrail_pass"] else "B" if len(pairs) >= 10 and supported and success["guardrail_pass"] else "C" if pairs else "D"
    return {
        "schema_version": SCHEMA_VERSION, "config": config.to_dict(), "paired_tasks": len(pairs),
        "metrics": metrics, "success": success, "supported_improvements": supported,
        "evidence_grade": grade,
        "claim_status": "SUPPORTED" if supported and success["guardrail_pass"] else "INSUFFICIENT_EVIDENCE",
        "limitations": ["Results are observational unless task assignment is randomized.", "Bootstrap intervals quantify uncertainty in paired deltas; they do not establish causal attribution."] if pairs else ["No matched baseline/Skein tasks were found."],
    }


def write_result(root: Path, result: dict[str, Any]) -> Path:
    path = root / RESULT_NAME; path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"); return path


def render_report(result: dict[str, Any]) -> str:
    lines = ["# Skein v0.5 Evaluation Report", "", f"**Evidence grade:** {result['evidence_grade']}", f"**Claim status:** {result['claim_status']}", f"**Matched tasks:** {result['paired_tasks']}", "", "## Metrics", "", "| Metric | Baseline mean | Skein mean | Improvement | 95% bootstrap CI | Supported |", "|---|---:|---:|---:|---:|---|"]
    for name, m in result["metrics"].items():
        ci = m.get("bootstrap_ci")
        lines.append(f"| {name} | {m.get('baseline_mean')} | {m.get('skein_mean')} | {m.get('improvement_pct')}% | {ci} | {'YES' if m.get('statistically_supported') else 'NO'} |")
    s = result["success"]
    lines += ["", "## Success Guardrail", f"Baseline: {s['baseline_rate']}", f"Skein: {s['skein_rate']}", f"Delta: {s['delta_percentage_points']} percentage points", f"Guardrail: {'PASS' if s['guardrail_pass'] else 'FAIL'}", "", "## Interpretation", "Skein only reports statistically supported improvements when the configured sample-size threshold is met and the bootstrap interval is above zero. Missing evidence remains explicitly unmeasured.", "", "## Limitations", *[f"- {x}" for x in result["limitations"]]]
    return "\n".join(lines) + "\n"


def write_report(root: Path, result: dict[str, Any]) -> Path:
    path = root / REPORT_NAME; path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_report(result), encoding="utf-8"); return path

CONFIG_NAME = ".skein/evaluation.json"

def init_evaluation(root: Path) -> Path:
    path = root / CONFIG_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(EvaluationConfig().to_dict(), indent=2) + "\n", encoding="utf-8")
    return path
