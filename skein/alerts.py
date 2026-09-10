"""Stage 5 anomaly detection hooks."""
from __future__ import annotations
from pathlib import Path
from .telemetry import TelemetryStore
from .compression.telemetry import CompressionTelemetry
from .versioning import VersionedGraphStore


def evaluate(root: Path, *, max_cost_usd: float = 1.0, max_fallback_rate: float = 0.20, max_conflicts: int = 5) -> list[dict[str, object]]:
    history = root / '.skein' / 'history'
    cost = TelemetryStore(history).aggregate()
    compression = CompressionTelemetry(history).health()
    conflicts = len(VersionedGraphStore(history).conflicts())
    alerts: list[dict[str, object]] = []
    total_cost = sum(float(v['cost_usd']) for v in cost['by_stage'].values())
    if total_cost > max_cost_usd:
        alerts.append({'type':'cost_spike','severity':'warning','value':total_cost,'threshold':max_cost_usd})
    if compression['fallback_rate'] > max_fallback_rate:
        alerts.append({'type':'compression_fallback_rate','severity':'critical','value':compression['fallback_rate'],'threshold':max_fallback_rate})
    if conflicts > max_conflicts:
        alerts.append({'type':'write_conflicts','severity':'warning','value':conflicts,'threshold':max_conflicts})
    return alerts
