from app.agents.supervisor import make_service_node

sheets_subgraph = make_service_node("sheets")

__all__ = ["sheets_subgraph"]
