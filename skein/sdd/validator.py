from __future__ import annotations
from datetime import date
from pathlib import Path
from typing import Iterable
import yaml
from pydantic import ValidationError
from .models import SpecClause, SpecTier

class SpecValidationError(ValueError):
    pass

def load_clauses(root: Path) -> list[SpecClause]:
    clauses: list[SpecClause] = []
    for path in sorted(root.glob("*.yaml")):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            clause = SpecClause.model_validate(data)
        except (OSError, ValidationError, yaml.YAMLError) as exc:
            raise SpecValidationError(f"{path}: invalid spec clause: {exc}") from exc
        clauses.append(clause)
    return clauses

def validate_clauses(clauses: Iterable[SpecClause], *, today: date | None = None) -> None:
    today = today or date.today()
    errors: list[str] = []
    seen: set[str] = set()
    for clause in clauses:
        if clause.id in seen:
            errors.append(f"{clause.id}: duplicate clause id")
        seen.add(clause.id)
        if clause.status != "active":
            errors.append(f"{clause.id}: non-active clause cannot live in spec/clauses")
        if clause.tier == SpecTier.A:
            if not clause.test_ref:
                errors.append(f"{clause.id}: Tier A clause requires test_ref")
            if not clause.evidence:
                errors.append(f"{clause.id}: Tier A clause requires evidence")
        elif clause.tier == SpecTier.B:
            if not clause.review_date:
                errors.append(f"{clause.id}: Tier B clause requires review_date")
            elif clause.review_date < today:
                errors.append(f"{clause.id}: Tier B hypothesis overdue for review ({clause.review_date})")
            if not clause.success_metric:
                errors.append(f"{clause.id}: Tier B clause requires success_metric")
            if not clause.validation_plan:
                errors.append(f"{clause.id}: Tier B clause requires validation_plan")
        elif clause.tier == SpecTier.C:
            errors.append(f"{clause.id}: Tier C clause must be quarantined, not active")
    if errors:
        raise SpecValidationError("Spec validation failed:\n" + "\n".join(f"  - {e}" for e in errors))
