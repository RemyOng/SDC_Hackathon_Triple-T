from typing import Any, Dict, Optional
from typing_extensions import TypedDict


class GraphState(TypedDict):
    """The shared memory payload moving between graph nodes."""
    sme_id: str
    document_id: str
    document_url: str
    filename: str

    extracted_data: Optional[Dict[str, Any]]
    audit_metrics: Optional[Dict[str, Any]]

    human_approved: bool