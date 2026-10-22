from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from workflow.state import GraphState
from workflow.nodes import (
    node_extract_data,
    node_calculate_impact,
    node_publish_to_marketplace
)
from workflow.edges import route_approval


def build_graph():
    """Constructs and compiles the orchestrator."""
    workflow = StateGraph(GreenReadyState)

    # Add Nodes
    workflow.add_node("extract_data", node_extract_data)
    workflow.add_node("calculate_impact", node_calculate_impact)
    workflow.add_node("publish_to_marketplace", node_publish_to_marketplace)

    # Wire the primary execution path
    workflow.add_edge(START, "extract_data")
    workflow.add_edge("extract_data", "calculate_impact")

    # Inject the Human-in-the-Loop Interrupt Point
    # Halts execution here to wait for WhatsApp owner approval
    workflow.add_conditional_edges(
        "calculate_impact",
        route_approval,
        {
            "publish_to_marketplace": "publish_to_marketplace",
            END: END
        }
    )

    # 4. Final step
    workflow.add_edge("publish_to_marketplace", END)

    # Compile with memory so state survives the webhook sleep cycle
    memory = MemorySaver()
    return workflow.compile(
        checkpointer=memory,
        interrupt_after=["calculate_impact"]
    )


# Export the initialized agent for the FastAPI router to use
greenready_graph = build_graph()