from __future__ import annotations
from datetime import date
from enum import StrEnum
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class SpecTier(StrEnum):
    A = "A"
    B = "B"
    C = "C"

class SpecOrigin(StrEnum):
    BROWNFIELD = "brownfield"
    GREENFIELD = "greenfield"

class EvidenceStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"

class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: str = Field(min_length=1)
    ref: str | None = None
    status: EvidenceStatus | None = None

class SpecClause(BaseModel):
    """Machine-readable SDD clause following the Spec Factory trust model."""
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    statement: str = Field(min_length=1)
    origin: SpecOrigin
    tier: SpecTier
    evidence: list[Evidence] = Field(default_factory=list)
    review_date: date | None = None
    owner: str = Field(min_length=1)
    test_ref: str | None = None
    success_metric: str | None = None
    validation_plan: str | None = None
    status: Literal["active", "quarantined"] = "active"
    spec_version: str = "1.0.0"
