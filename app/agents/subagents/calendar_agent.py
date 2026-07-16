from app.agents.supervisor import make_service_node

calendar_subgraph = make_service_node("calendar")

__all__ = ["calendar_subgraph"]
