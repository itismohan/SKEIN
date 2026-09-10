from datetime import date
from pathlib import Path
import pytest
from skein.sdd import load_clauses, validate_clauses, SpecValidationError, SpecClause

ROOT = Path(__file__).parents[2] / "spec" / "clauses"

def test_repo_spec_is_valid():
    clauses = load_clauses(ROOT)
    validate_clauses(clauses, today=date(2026, 9, 10))
    assert {c.id for c in clauses} == {"SKN-001", "SKN-002", "SKN-003", "SKN-004", "SKN-005", "SKN-006", "SKN-007", "SKN-008"}

def test_tier_a_requires_test_reference():
    clause = SpecClause(id="X", statement="must work", origin="greenfield", tier="A", owner="x", evidence=[{"type":"test"}])
    with pytest.raises(SpecValidationError, match="requires test_ref"):
        validate_clauses([clause], today=date(2026, 9, 10))

def test_tier_b_requires_time_box_and_validation_contract():
    clause = SpecClause(id="X", statement="hypothesis", origin="greenfield", tier="B", owner="x")
    with pytest.raises(SpecValidationError, match="review_date"):
        validate_clauses([clause], today=date(2026, 9, 10))
