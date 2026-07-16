from app.agents.supervisor import make_service_node

contacts_subgraph = make_service_node("contacts")

__all__ = ["contacts_subgraph"]
