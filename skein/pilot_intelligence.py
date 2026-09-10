"""Pilot Intelligence for matched baseline-vs-Skein design-partner experiments.

This module turns raw pilot evidence into paired engineering metrics. It deliberately
keeps provider telemetry optional: missing real-world signals are reported as NOT_MEASURED,
never inferred.
"""
from __future__ import annotations

import json
import statistics
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .telemetry import TelemetryStore

CONFIG_NAME = ".skein/pilot-intelligence.json"
RESULT_NAME = ".skein/pilot-intelligence-results.json"
REPORT_NAME = ".skein/pilot-intelligence-report.md"


@dataclass(frozen=True)
class IntelligenceConfig:
    pilot: str = "skein-v0.3-pilot"
    success_threshold: float = 0.90
    minimum_paired_scenarios: int = 1
    cost_target_reduction_pct: float = 20.0
    context_target_reduction_pct: float = 30.0
    latency_target_reduction_pct: float = 10.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def init_intelligence(root: Path, *, pilot: str = "skein-v0.3-pilot") -> Path:
    path = root / CONFIG_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(IntelligenceConfig(pilot=pilot).to_dict(), indent=2) + "\n", encoding="utf-8")
    return path


def load_config(root: Path) -> IntelligenceConfig:
    path = root / CONFIG_NAME
    if not path.exists():
        return IntelligenceConfig()
    data = json.loads(path.read_text(encoding="utf-8"))
    return IntelligenceConfig(
        pilot=str(data.get("pilot", "skein-v0.3-pilot")),
        success_threshold=float(data.get("success_threshold", 0.90)),
        minimum_paired_scenarios=max(1, int(data.get("minimum_paired_scenarios", 1))),
        cost_target_reduction_pct=float(data.get("cost_target_reduction_pct", 20.0)),
        context_target_reduction_pct=float(data.get("context_target_reduction_pct", 30.0)),
        latency_target_reduction_pct=float(data.get("latency_target_reduction_pct", 10.0)),
    )


def _pct_delta(baseline: float, skein: float) -> float | None:
    if baseline == 0:
        return 0.0 if skein == 0 else None
    return round((1.0 - skein / baseline) * 100.0, 4)


def _mean(values: list[float]) -> float | None:
    return statistics.mean(values) if values else None


def _median(values: list[float]) -> float | None:
    return statistics.median(values) if values else None


def _paired_scenarios(root: Path) -> list[dict[str, Any]]:
    path = root / ".skein" / "pilot-scenario-results.json"
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    grouped: dict[str, dict[str, dict[str, Any]]] = {}
    for row in payload.get("results", []):
        sid = str(row.get("scenario_id", "scenario"))
        mode = str(row.get("mode", ""))
        if mode in {"baseline", "skein"}:
            grouped.setdefault(sid, {})[mode] = row
    return [
        {"scenario_id": sid, "baseline": pair["baseline"], "skein": pair["skein"]}
        for sid, pair in sorted(grouped.items())
        if "baseline" in pair and "skein" in pair
    ]


def _scenario_metrics(pairs: list[dict[str, Any]]) -> dict[str, Any]:
    latency_b = [float(p["baseline"].get("latency_ms", 0)) for p in pairs]
    latency_s = [float(p["skein"].get("latency_ms", 0)) for p in pairs]
    out_b = [float(p["baseline"].get("stdout_tokens", 0)) for p in pairs]
    out_s = [float(p["skein"].get("stdout_tokens", 0)) for p in pairs]
    err_b = [float(p["baseline"].get("stderr_tokens", 0)) for p in pairs]
    err_s = [float(p["skein"].get("stderr_tokens", 0)) for p in pairs]
    return {
        "paired_scenarios": len(pairs),
        "latency_ms": {"baseline_mean": _mean(latency_b), "skein_mean": _mean(latency_s), "reduction_pct": _pct_delta(_mean(latency_b) or 0, _mean(latency_s) or 0)},
        "output_tokens_proxy": {"baseline_mean": _mean(out_b), "skein_mean": _mean(out_s), "reduction_pct": _pct_delta(_mean(out_b) or 0, _mean(out_s) or 0)},
        "error_tokens_proxy": {"baseline_mean": _mean(err_b), "skein_mean": _mean(err_s), "reduction_pct": _pct_delta(_mean(err_b) or 0, _mean(err_s) or 0)},
        "latency_median_ms": {"baseline": _median(latency_b), "skein": _median(latency_s)},
    }


def _telemetry_metrics(root: Path) -> dict[str, Any]:
    store = TelemetryStore(root / ".skein" / "history")
    events = store.events()
    baseline = [e for e in events if str((e.metadata or {}).get("experiment", "")) == "baseline"]
    skein = [e for e in events if str((e.metadata or {}).get("experiment", "")) == "skein"]

    def aggregate(rows: list[Any]) -> dict[str, float | int]:
        return {
            "calls": len(rows),
            "input_tokens": sum(e.input_tokens for e in rows),
            "output_tokens": sum(e.output_tokens for e in rows),
            "reasoning_tokens": sum(e.reasoning_tokens or 0 for e in rows),
            "cost_usd": sum(e.estimated_cost_usd or 0.0 for e in rows),
            "successes": sum(1 for e in rows if e.outcome == "success"),
            "errors": sum(1 for e in rows if e.outcome != "success"),
        }

    b = aggregate(baseline)
    s = aggregate(skein)
    total_b_tokens = int(b["input_tokens"]) + int(b["output_tokens"]) + int(b["reasoning_tokens"])
    total_s_tokens = int(s["input_tokens"]) + int(s["output_tokens"]) + int(s["reasoning_tokens"])
    return {
        "available": bool(events),
        "experiment_events": len(baseline) + len(skein),
        "baseline": b,
        "skein": s,
        "deltas": {
            "total_tokens_reduction_pct": _pct_delta(total_b_tokens, total_s_tokens) if baseline and skein else None,
            "cost_reduction_pct": _pct_delta(float(b["cost_usd"]), float(s["cost_usd"])) if baseline and skein else None,
            "success_rate_baseline": b["successes"] / b["calls"] if b["calls"] else None,
            "success_rate_skein": s["successes"] / s["calls"] if s["calls"] else None,
            "cost_per_successful_task_baseline": float(b["cost_usd"]) / b["successes"] if b["successes"] else None,
            "cost_per_successful_task_skein": float(s["cost_usd"]) / s["successes"] if s["successes"] else None,
            "cost_per_successful_task_reduction_pct": _pct_delta(
                float(b["cost_usd"]) / b["successes"] if b["successes"] else 0.0,
                float(s["cost_usd"]) / s["successes"] if s["successes"] else 0.0,
            ) if b["successes"] and s["successes"] else None,
        },
    }


def _explicit_experiment_metrics(root: Path) -> dict[str, Any]:
    path = root / ".skein" / "pilot-experiment-metrics.json"
    if not path.exists():
        return {"available": False, "metrics": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {"available": True, "metrics": data.get("metrics", {})}


def _traceability(root: Path) -> dict[str, Any]:
    path = root / ".skein" / "history" / "trace.jsonl"
    if not path.exists():
        return {"available": False, "records": 0}
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    relations = {}
    for row in records:
        relation = str(row.get("relation", "UNKNOWN"))
        relations[relation] = relations.get(relation, 0) + 1
    return {"available": bool(records), "records": len(records), "relations": relations}


def _governance(root: Path) -> dict[str, Any]:
    path = root / ".skein" / "history" / "proposals.jsonl"
    if not path.exists():
        return {"available": False, "proposals": 0, "blocked": 0, "committed": 0}
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    blocked = sum(1 for r in rows if str(r.get("status", "")).lower() in {"blocked", "rejected", "denied"})
    committed = sum(1 for r in rows if str(r.get("status", "")).lower() == "committed")
    return {"available": True, "proposals": len(rows), "blocked": blocked, "committed": committed}


def _quality_delta(baseline: Any, skein: Any, *, lower_is_better: bool = False) -> float | None:
    if not isinstance(baseline, (int, float)) or not isinstance(skein, (int, float)):
        return None
    if baseline == 0:
        return 0.0 if skein == 0 else None
    return round(((skein - baseline) / baseline) * 100.0 * (-1 if lower_is_better else 1), 4)


def _quality_signals(explicit: dict[str, Any], telemetry: dict[str, Any], pairs: list[dict[str, Any]]) -> dict[str, Any]:
    metrics = explicit.get("metrics", {})
    success = metrics.get("task_success_rate", {})
    rework = metrics.get("rework_per_task", {})
    handoff = metrics.get("handoff_loss_rate", {})
    return {
        "task_success_rate": success,
        "rework_per_task": rework,
        "handoff_loss_rate": handoff,
        "deltas_pct": {
            "task_success_rate": _quality_delta(success.get("baseline"), success.get("skein")),
            "rework_reduction": _quality_delta(rework.get("baseline"), rework.get("skein"), lower_is_better=True),
            "handoff_loss_reduction": _quality_delta(handoff.get("baseline"), handoff.get("skein"), lower_is_better=True),
        },
        "source": "pilot-experiment-metrics.json" if explicit.get("available") else "not_measured",
        "telemetry_success_rate": telemetry["deltas"],
        "paired_scenarios": len(pairs),
    }


def run_intelligence(root: Path) -> dict[str, Any]:
    root = root.resolve()
    config = load_config(root)
    pairs = _paired_scenarios(root)
    scenarios = _scenario_metrics(pairs)
    telemetry = _telemetry_metrics(root)
    explicit = _explicit_experiment_metrics(root)
    traceability = _traceability(root)
    governance = _governance(root)

    pilot_result_path = root / ".skein" / "pilot-results.json"
    pilot_result = json.loads(pilot_result_path.read_text(encoding="utf-8")) if pilot_result_path.exists() else {}
    structural_context_reduction = pilot_result.get("context_efficiency", {}).get("token_reduction_pct")
    structural_retrieval_f1 = pilot_result.get("retrieval", {}).get("f1")

    context_reduction = structural_context_reduction
    real_cost_reduction = telemetry["deltas"].get("cost_reduction_pct")
    real_token_reduction = telemetry["deltas"].get("total_tokens_reduction_pct")
    latency_reduction = scenarios["latency_ms"].get("reduction_pct")

    scorecard = {
        "context_efficiency": {
            "value_pct": context_reduction,
            "status": "MEASURED_STRUCTURAL" if context_reduction is not None else "NOT_MEASURED",
        },
        "provider_token_reduction": {
            "value_pct": real_token_reduction,
            "status": "MEASURED" if real_token_reduction is not None else "NOT_MEASURED",
        },
        "llm_cost_reduction": {
            "value_pct": real_cost_reduction,
            "status": "MEASURED" if real_cost_reduction is not None else "NOT_MEASURED",
        },
        "latency_reduction": {
            "value_pct": latency_reduction,
            "status": "MEASURED_SCENARIO" if latency_reduction is not None else "NOT_MEASURED",
        },
        "retrieval_f1": {
            "value": structural_retrieval_f1,
            "status": "MEASURED_STRUCTURAL" if structural_retrieval_f1 is not None else "NOT_MEASURED",
        },
        "task_success": {
            "value": explicit.get("metrics", {}).get("task_success_rate", {}).get("skein") if explicit.get("available") else None,
            "status": "MEASURED" if explicit.get("available") and "task_success_rate" in explicit.get("metrics", {}) else "NOT_MEASURED",
        },
        "rework": {
            "value": explicit.get("metrics", {}).get("rework_per_task", {}).get("skein") if explicit.get("available") else None,
            "status": "MEASURED" if explicit.get("available") and "rework_per_task" in explicit.get("metrics", {}) else "NOT_MEASURED",
        },
        "handoff_loss": {
            "value": explicit.get("metrics", {}).get("handoff_loss_rate", {}).get("skein") if explicit.get("available") else None,
            "status": "MEASURED" if explicit.get("available") and "handoff_loss_rate" in explicit.get("metrics", {}) else "NOT_MEASURED",
        },
    }

    target_checks = {
        "context_target": context_reduction is not None and context_reduction >= config.context_target_reduction_pct,
        "cost_target": real_cost_reduction is not None and real_cost_reduction >= config.cost_target_reduction_pct,
        "latency_target": latency_reduction is not None and latency_reduction >= config.latency_target_reduction_pct,
        "minimum_pairs": len(pairs) >= config.minimum_paired_scenarios,
    }
    measured_quality = scorecard["task_success"]["status"] == "MEASURED"
    if measured_quality:
        task_success = float(scorecard["task_success"]["value"])
        target_checks["success_target"] = task_success >= config.success_threshold
    else:
        target_checks["success_target"] = None

    result = {
        "schema_version": "0.3.0",
        "pilot": config.pilot,
        "generated_at_epoch": time.time(),
        "workspace": str(root),
        "scorecard": scorecard,
        "scenario_execution": scenarios,
        "provider_telemetry": telemetry,
        "quality_signals": _quality_signals(explicit, telemetry, pairs),
        "traceability": traceability,
        "governance": governance,
        "targets": {
            "configured": asdict(config),
            "checks": target_checks,
        },
        "evidence_quality": {
            "real_provider_telemetry": telemetry["available"] and telemetry["experiment_events"] > 0,
            "matched_scenarios": len(pairs),
            "production_quality_claim_allowed": bool(telemetry["available"] and measured_quality and len(pairs) >= config.minimum_paired_scenarios),
        },
        "limitations": [
            "Structural context and retrieval measurements are not substitutes for provider-token or task-quality measurements.",
            "Process exit codes do not establish task success; explicit human-reviewed success metrics are required.",
            "Cost is measured only when provider telemetry supplies estimated_cost_usd for baseline and Skein events.",
            "Rework and handoff loss remain NOT_MEASURED until pilot-experiment-metrics.json is populated from reviewed task outcomes.",
        ],
    }
    return result


def write_result(root: Path, result: dict[str, Any]) -> Path:
    path = root / RESULT_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def render_report(result: dict[str, Any]) -> str:
    s = result["scorecard"]
    targets = result["targets"]["checks"]
    def pct(item: dict[str, Any]) -> str:
        value = item.get("value_pct")
        return "NOT MEASURED" if value is None else f"{value:.2f}%"
    def val(item: dict[str, Any]) -> str:
        value = item.get("value")
        return "NOT MEASURED" if value is None else f"{value:.2%}" if 0 <= value <= 1 else str(value)
    lines = [
        "# Skein v0.3 Pilot Intelligence Report", "",
        f"**Pilot:** {result['pilot']}  ",
        "**Purpose:** matched baseline-vs-Skein evidence synthesis", "",
        "## Executive scorecard", "",
        "| Signal | Result | Evidence status |",
        "|---|---:|---|",
        f"| Structural context reduction | {pct(s['context_efficiency'])} | {s['context_efficiency']['status']} |",
        f"| Provider token reduction | {pct(s['provider_token_reduction'])} | {s['provider_token_reduction']['status']} |",
        f"| LLM cost reduction | {pct(s['llm_cost_reduction'])} | {s['llm_cost_reduction']['status']} |",
        f"| Scenario latency reduction | {pct(s['latency_reduction'])} | {s['latency_reduction']['status']} |",
        f"| Retrieval F1 | {val(s['retrieval_f1'])} | {s['retrieval_f1']['status']} |",
        f"| Task success | {val(s['task_success'])} | {s['task_success']['status']} |",
        f"| Rework / task | {val(s['rework'])} | {s['rework']['status']} |",
        f"| Handoff loss | {val(s['handoff_loss'])} | {s['handoff_loss']['status']} |",
        "",
        "## Target gates", "",
        "| Gate | Result |",
        "|---|---|",
    ]
    for name, passed in targets.items():
        lines.append(f"| {name.replace('_', ' ').title()} | {'PASS' if passed is True else 'FAIL' if passed is False else 'NOT MEASURED'} |")
    lines += [
        "",
        "## Scenario execution", "",
        f"Paired scenarios: **{result['scenario_execution']['paired_scenarios']}**",
        f"Mean latency baseline: **{result['scenario_execution']['latency_ms']['baseline_mean']} ms**",
        f"Mean latency Skein: **{result['scenario_execution']['latency_ms']['skein_mean']} ms**",
        "",
        "## Evidence boundary", "",
        f"Real provider telemetry available: **{result['evidence_quality']['real_provider_telemetry']}**  ",
        f"Production-quality claim allowed by this harness: **{result['evidence_quality']['production_quality_claim_allowed']}**",
        "",
        "The intelligence layer is intentionally conservative: a missing measurement is surfaced as `NOT MEASURED`, not converted into a favorable inference.",
        "",
        "## Limitations", "",
    ]
    lines.extend(f"- {x}" for x in result["limitations"])
    return "\n".join(lines) + "\n"


def write_report(root: Path, result: dict[str, Any]) -> Path:
    path = root / REPORT_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_report(result), encoding="utf-8")
    return path
