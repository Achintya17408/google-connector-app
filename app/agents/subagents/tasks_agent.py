from app.agents.supervisor import make_service_node

tasks_subgraph = make_service_node("tasks")

__all__ = ["tasks_subgraph"]
