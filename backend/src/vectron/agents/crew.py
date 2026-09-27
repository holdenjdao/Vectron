"""Draftsman and Integrator: deterministic renderers wrapped as agents."""

from __future__ import annotations

from vectron.codegen.files import CodegenError
from vectron.diagrams import diagrams_markdown, render_diagrams
from vectron.orchestration import Agent, AgentError, AgentResult, RunContext


class DraftsmanAgent(Agent):
    role = "draftsman"
    display_name = "Draftsman"
    description = "Renders architecture, interface, behaviour and physical diagrams from the spec."

    async def run(self, ctx: RunContext) -> AgentResult:
        diagrams = render_diagrams(ctx.spec)
        for diagram in diagrams:
            ctx.save(diagram)
        ctx.save(diagrams_markdown(ctx.spec, diagrams))
        svg = sum(1 for d in diagrams if d.media_type == "image/svg+xml")
        return AgentResult(
            summary=f"{len(diagrams)} diagrams ({len(diagrams) - svg} Mermaid, {svg} SVG drawing)"
        )


class IntegratorAgent(Agent):
    role = "integrator"
    display_name = "Integrator"
    description = "Fabricates the shared core runtime, composition root, sim feed and ICD."

    async def run(self, ctx: RunContext) -> AgentResult:
        try:
            files = ctx.target.scaffold(ctx.spec)
        except CodegenError as exc:
            raise AgentError(str(exc)) from exc
        for file in files:
            ctx.save(file)
        return AgentResult(
            summary=f"{len(files)} files: core runtime, composition root, sim feed, ICD"
        )
