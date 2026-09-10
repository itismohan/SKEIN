#!/usr/bin/env python3
"""CI gate for Skein's machine-readable specification."""
from pathlib import Path
import sys

ROOT_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_REPO))
from skein.sdd import load_clauses, validate_clauses, SpecValidationError

ROOT = Path(__file__).resolve().parents[1] / "spec" / "clauses"
try:
    clauses = load_clauses(ROOT)
    validate_clauses(clauses)
except SpecValidationError as exc:
    print(str(exc))
    sys.exit(1)
print(f"Spec drift check passed: {len(clauses)} clauses verified.")
