# SecureCodeAI Agent Package
# LangGraph-based agentic workflow for vulnerability detection and patching

from .state import AgentState

__all__ = ["create_workflow", "AgentState"]


def __getattr__(name):
    """Lazily resolve heavy exports to avoid import-time side effects."""
    if name == "create_workflow":
        from .graph import create_workflow
        return create_workflow
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
