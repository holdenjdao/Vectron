"""Commander: turns a request into a concrete blueprint + options, then hands off."""

from __future__ import annotations

import json
from typing import Any

from vectron.domain.blueprint import Blueprint
from vectron.llm.base import LLMError
from vectron.orchestration import Agent, AgentError, AgentResult, RunContext, TaskSpec

from .prompts import load_prompt


class PlannerAgent(Agent):
    role = "planner"
    display_name = "Commander"
    description = "Interprets the request, selects a blueprint and options, and plans the build."

    async def run(self, ctx: RunContext) -> AgentResult:
        request = ctx.job.record.request
        if request.blueprint_id:
            try:
                blueprint = ctx.catalog.get(request.blueprint_id)
            except KeyError as exc:
                raise AgentError(str(exc)) from exc
            options, how = dict(request.options), "requested directly"
        else:
            selection = await self._from_brief(ctx, request.brief)
            if selection is None:
                return self._design_new(ctx)
            blueprint, suggested, how = selection
            options = {**suggested, **request.options}  # explicit options win

        try:
            resolved = blueprint.resolve_options(options)
        except ValueError as exc:
            raise AgentError(f"invalid options for {blueprint.id}: {exc}") from exc
        board = ctx.job.board
        board.blueprint, board.options = blueprint, resolved
        ctx.job.record.blueprint_id = blueprint.id
        ctx.job.record.title = f"{blueprint.name} ({blueprint.designation})"
        changed = {k: v for k, v in resolved.items() if options.get(k) is not None}
        ctx.log(f"Blueprint {blueprint.id} {how}; options {changed or 'default'}")
        return AgentResult(
            summary=f"{blueprint.designation} {blueprint.name}: {how}",
            spawn=(TaskSpec("architect", "architect", "Derive the system specification"),),
        )

    def _design_new(self, ctx: RunContext) -> AgentResult:
        ctx.job.board.design_from_brief = True
        ctx.job.record.title = "New system (designing from brief)"
        ctx.log("No blueprint fits the brief; the Architect will design a new system")
        return AgentResult(
            summary=f"no blueprint fits; new design ordered ({ctx.job.board.design_reason})",
            spawn=(TaskSpec("architect", "architect", "Design a new system from the brief"),),
        )

    async def _from_brief(
        self, ctx: RunContext, brief: str
    ) -> tuple[Blueprint, dict[str, Any], str] | None:
        """A catalog blueprint for the brief, or None when a new design is needed."""
        if ctx.llm.enabled:
            try:
                return await self._llm_select(ctx, brief)
            except (LLMError, KeyError, ValueError) as exc:
                ctx.log(f"LLM planning unavailable ({exc}); using keyword matching")
        ranked = ctx.catalog.match(brief)
        if not ranked:
            names = ", ".join(b.name for b in ctx.catalog.list())
            raise AgentError(f"could not match the brief to a blueprint (available: {names})")
        blueprint, score = ranked[0]
        return blueprint, {}, f"matched from the brief ({score} keyword hit{'s' * (score != 1)})"

    async def _llm_select(
        self, ctx: RunContext, brief: str
    ) -> tuple[Blueprint, dict[str, Any], str] | None:
        catalog = [
            {
                "id": b.id,
                "name": b.name,
                "summary": b.summary,
                "options": [
                    {
                        "key": o.key,
                        "type": o.type,
                        "choices": [c.value for c in o.choices],
                        "min": o.min,
                        "max": o.max,
                        "default": o.default,
                    }
                    for o in b.options
                ],
            }
            for b in ctx.catalog.list()
        ]
        schema = {
            "type": "object",
            "properties": {
                "blueprint_id": {"type": "string", "enum": [*(b["id"] for b in catalog), "none"]},
                "options": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {"key": {"type": "string"}, "value": {"type": "string"}},
                        "required": ["key", "value"],
                        "additionalProperties": False,
                    },
                },
                "rationale": {"type": "string"},
            },
            "required": ["blueprint_id", "options", "rationale"],
            "additionalProperties": False,
        }
        result = await ctx.ask_llm(
            purpose="select a blueprint for the mission brief",
            system=load_prompt("planner"),
            prompt=f"<catalog>\n{json.dumps(catalog, indent=2)}\n</catalog>\n\n"
            f"<brief>\n{brief}\n</brief>",
            schema=schema,
            effort="low",
        )
        rationale = str(result.data.get("rationale", "")).strip()
        if result.data["blueprint_id"] == "none":
            ctx.job.board.design_reason = rationale[:200]
            return None
        blueprint = ctx.catalog.get(result.data["blueprint_id"])
        options: dict[str, Any] = {}
        known = {o.key: o for o in blueprint.options}
        for item in result.data.get("options", []):
            option = known.get(item.get("key"))
            if option is None:
                continue
            try:
                options[option.key] = option.coerce(item.get("value"))
            except ValueError as exc:
                ctx.log(f"Ignoring suggested option {option.key}: {exc}")
        return blueprint, options, f"selected by {result.model}: {rationale}"[:300]
