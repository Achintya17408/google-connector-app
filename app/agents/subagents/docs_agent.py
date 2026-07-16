from app.agents.supervisor import make_service_node

docs_subgraph = make_service_node("docs")

__all__ = ["docs_subgraph"]
