from __future__ import annotations

from flowweaver.protocols.base import StrictModel


class WorkflowValidationIssue(StrictModel):
    code: str
    path: str
    message: str


class WorkflowValidationResult(StrictModel):
    valid: bool
    errors: list[WorkflowValidationIssue] = []
    warnings: list[WorkflowValidationIssue] = []
