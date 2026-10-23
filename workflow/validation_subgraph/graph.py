from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from .nodes import (
    check_attachment_format,
    check_content_legitimacy,
    check_corrupted_attachments,
    finalize_validation,
)
from .state import AttachmentValidation, ValidationResult, ValidationState


def build_validation_subgraph():
    workflow = StateGraph(ValidationState)
    workflow.add_node("check_corrupted_attachments", check_corrupted_attachments)
    workflow.add_node("check_attachment_format", check_attachment_format)
    workflow.add_node("check_content_legitimacy", check_content_legitimacy)
    workflow.add_node("finalize_validation", finalize_validation)

    workflow.add_edge(START, "check_corrupted_attachments")
    workflow.add_edge("check_corrupted_attachments", "check_attachment_format")
    workflow.add_edge("check_attachment_format", "check_content_legitimacy")
    workflow.add_edge("check_content_legitimacy", "finalize_validation")
    workflow.add_edge("finalize_validation", END)
    return workflow.compile()


__all__ = ["AttachmentValidation", "ValidationResult", "ValidationState", "build_validation_subgraph"]
