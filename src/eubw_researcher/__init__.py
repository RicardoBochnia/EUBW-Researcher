"""EUBW Researcher prototype."""

from .agent_runtime import AGENT_RUNTIME_CONTRACT_VERSION, AgentRuntimeFacade
from .pipeline import ResearchPipeline

__all__ = [
    "AGENT_RUNTIME_CONTRACT_VERSION",
    "AgentRuntimeFacade",
    "ResearchPipeline",
]
