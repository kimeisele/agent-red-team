"""Pipeline phase types.

Each phase is a conceptual step in the audit pipeline.  Implementations
will connect these phases; for now they are documented contracts only.
"""
from __future__ import annotations

from enum import Enum


class PipelinePhase(Enum):
    """Ordered phases of the modular audit pipeline."""

    REQUEST_INTAKE = "request_intake"
    REQUEST_VALIDATION = "request_validation"
    AUTHORIZATION_GATE = "authorization_gate"
    AUDIT_PLANNING = "audit_planning"
    MODULE_EXECUTION = "module_execution"
    FINDING_NORMALIZATION = "finding_normalization"
    DISCLOSURE_CLASSIFICATION = "disclosure_classification"
    REPORT_RENDERING = "report_rendering"
    DELIVERY = "delivery"
