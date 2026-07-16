from app.agents.supervisor import make_service_node

chat_subgraph = make_service_node("chat")

__all__ = ["chat_subgraph"]
