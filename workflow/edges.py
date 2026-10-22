from langgraph.graph import END
from workflow.state import GreenReadyState


def route_approval(state: GreenReadyState) -> str:
    """
    Checks if the SME owner replied YES on WhatsApp.
    If yes, routes to marketplace. If no/pending, halts the graph.
    """

    if state.get("human_approved"): # approved
        return "publish_to_marketplace"

    if state.state.get("human_approved") == "REJECTED":
        pass

    if state.state.get("human_approved") == "NEEDS_MANUAL_REVIEW":
        pass

    return END