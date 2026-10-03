"""The factory crew. Each agent handles one role in the task graph.

Commander (planner) -> Architect -> Draftsman, Integrator, one Engineer per module
-> Inspector (quality gate) -> Quartermaster (packager).
"""

from __future__ import annotations

from vectron.orchestration import Agent

from .architect import ArchitectAgent
from .crew import DraftsmanAgent, IntegratorAgent
from .engineer import EngineerAgent
from .inspector import InspectorAgent
from .packager import PackagerAgent
from .planner import PlannerAgent

AGENT_TYPES: tuple[type[Agent], ...] = (
    PlannerAgent,
    ArchitectAgent,
    DraftsmanAgent,
    IntegratorAgent,
    EngineerAgent,
    InspectorAgent,
    PackagerAgent,
)


def default_agents() -> dict[str, Agent]:
    """Role -> agent instance. Agents are stateless, so one instance serves all jobs."""
    return {agent_type.role: agent_type() for agent_type in AGENT_TYPES}
