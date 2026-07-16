from app.agents.supervisor import make_service_node

gmail_subgraph = make_service_node("gmail")

__all__ = ["gmail_subgraph"]
