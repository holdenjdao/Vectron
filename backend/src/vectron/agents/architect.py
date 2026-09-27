"""Architect: builds the system spec, adapts it to the brief, and dispatches the crew."""

from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from vectron.codegen.files import GeneratedFile
from vectron.codegen.python.parts import get_part
from vectron.domain.blueprint import Blueprint
from vectron.domain.jobs import ArtifactKind
from vectron.domain.spec import SystemSpec
from vectron.domain.values import FIELD_TYPES
from vectron.llm.base import LLMError
from vectron.orchestration import Agent, AgentError, AgentResult, RunContext, TaskSpec

from .designer import design_spec
from .prompts import load_prompt

MAX_NEW_MODULES = 3
MAX_NEW_MESSAGES = 4
MAX_NEW_TOPICS = 6

_STR = {"type": "string"}
PATCH_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "rationale": _STR,
        "config_overrides": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"module_id": _STR, "param": _STR, "value": _STR},
                "required": ["module_id", "param", "value"],
                "additionalProperties": False,
            },
        },
        "new_messages": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": _STR,
                    "doc": _STR,
                    "fields": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": _STR,
                                "type": {"type": "string", "enum": list(FIELD_TYPES)},
                                "unit": _STR,
                                "doc": _STR,
                            },
                            "required": ["name", "type", "unit", "doc"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["name", "doc", "fields"],
                "additionalProperties": False,
            },
        },
        "new_topics": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"name": _STR, "message": _STR, "doc": _STR},
                "required": ["name", "message", "doc"],
                "additionalProperties": False,
            },
        },
        "new_modules": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "subsystem_id": _STR,
                    "id": _STR,
                    "name": _STR,
                    "responsibility": _STR,
                    "subscribes": {"type": "array", "items": _STR},
                    "publishes": {"type": "array", "items": _STR},
                },
                "required": [
                    "subsystem_id",
                    "id",
                    "name",
                    "responsibility",
                    "subscribes",
                    "publishes",
                ],
                "additionalProperties": False,
            },
        },
    },
    "required": ["rationale", "config_overrides", "new_messages", "new_topics", "new_modules"],
    "additionalProperties": False,
}


class ArchitectAgent(Agent):
    role = "architect"
    display_name = "Architect"
    description = (
        "Derives the system spec (subsystems, modules, interfaces) and dispatches the crew."
    )

    async def run(self, ctx: RunContext) -> AgentResult:
        board = ctx.job.board
        brief = ctx.job.record.request.brief
        if board.design_from_brief:
            spec, board.architect_notes = await design_spec(ctx, brief)
            ctx.job.record.title = f"{spec.name} ({spec.designation})"
            ctx.log(f"Designed {spec.designation} {spec.name} from the brief")
        elif board.blueprint is None:
            raise AgentError("no blueprint selected")
        else:
            spec = await self._from_blueprint(ctx, board.blueprint, brief)
        board.spec = spec
        return self._dispatch(ctx, spec)

    async def _from_blueprint(
        self, ctx: RunContext, blueprint: Blueprint, brief: str
    ) -> SystemSpec:
        board = ctx.job.board
        try:
            spec = blueprint.instantiate(board.options, brief=brief)
        except (ValidationError, ValueError) as exc:
            raise AgentError(f"blueprint {blueprint.id} produced an invalid spec: {exc}") from exc
        if brief and ctx.llm.enabled:
            try:
                spec, notes, changes = await self._refine(ctx, spec, brief)
                board.architect_notes = notes
                ctx.log(f"Adapted spec to the brief: {', '.join(changes) or 'no changes needed'}")
            except (LLMError, ValidationError, ValueError, KeyError) as exc:
                ctx.log(f"Keeping the blueprint spec; proposed patch rejected: {exc}")
        return spec

    def _dispatch(self, ctx: RunContext, spec: SystemSpec) -> AgentResult:
        ctx.save(
            GeneratedFile(
                "vectron.spec.json",
                spec.model_dump_json(indent=2) + "\n",
                ArtifactKind.CONFIG,
                "application/json",
                "System spec",
                "The single source of truth every diagram and source file was rendered from.",
            )
        )
        engineers = [
            TaskSpec(
                f"engineer:{module.id}",
                "engineer",
                f"Fabricate {subsystem.name} / {module.name}",
                params={"module_id": module.id},
            )
            for subsystem, module in spec.iter_modules()
        ]
        crew = [
            TaskSpec("draft", "draftsman", "Draft the system diagrams"),
            TaskSpec("integrate", "integrator", "Fabricate core runtime, wiring and ICD"),
            *engineers,
        ]
        gates = [
            TaskSpec(
                "inspect", "inspector", "Inspect the build", depends_on=tuple(t.id for t in crew)
            ),
            TaskSpec(
                "package", "packager", "Package, document and manifest", depends_on=("inspect",)
            ),
        ]
        return AgentResult(
            summary=(
                f"{len(spec.subsystems)} subsystems, {spec.module_count} modules, "
                f"{len(spec.topics)} topics; dispatched {len(crew)} agents"
            ),
            spawn=(*crew, *gates),
        )

    async def _refine(
        self, ctx: RunContext, spec: SystemSpec, brief: str
    ) -> tuple[SystemSpec, str, list[str]]:
        document = spec.model_dump(mode="json", exclude={"simulation", "brief"})
        result = await ctx.ask_llm(
            purpose="adapt the spec to the mission brief",
            system=load_prompt("architect"),
            prompt=(
                f"<spec>\n{json.dumps(document, indent=1)}\n</spec>\n\n<brief>\n{brief}\n</brief>"
            ),
            schema=PATCH_SCHEMA,
        )
        patched, changes = apply_patch(spec, result.data)
        return patched, str(result.data.get("rationale", "")).strip(), changes


def apply_patch(spec: SystemSpec, patch: dict[str, Any]) -> tuple[SystemSpec, list[str]]:
    """Apply an Architect patch atomically; the result is fully re-validated."""
    doc = spec.model_dump(mode="json")
    changes: list[str] = []
    for message in patch.get("new_messages", [])[:MAX_NEW_MESSAGES]:
        doc["messages"].append(
            {"name": message["name"], "doc": message["doc"], "fields": message["fields"]}
        )
        changes.append(f"+message {message['name']}")
    for topic in patch.get("new_topics", [])[:MAX_NEW_TOPICS]:
        doc["topics"].append({**topic, "external": False})
        changes.append(f"+topic {topic['name']}")
    subsystems = {s["id"]: s for s in doc["subsystems"]}
    for module in patch.get("new_modules", [])[:MAX_NEW_MODULES]:
        subsystem_id = module["subsystem_id"]
        if subsystem_id not in subsystems:
            subsystems[subsystem_id] = {
                "id": subsystem_id,
                "name": subsystem_id.replace("_", " ").title(),
                "description": "Added by the Architect for this mission.",
                "modules": [],
            }
            doc["subsystems"].append(subsystems[subsystem_id])
        subsystems[subsystem_id]["modules"].append(
            {k: module[k] for k in ("id", "name", "responsibility", "subscribes", "publishes")}
        )
        changes.append(f"+module {module['id']}")
    modules = {m["id"]: m for s in doc["subsystems"] for m in s["modules"]}
    for override in patch.get("config_overrides", []):
        module = modules[override["module_id"]]
        params = {p["name"]: p for p in module["config"]}
        name = override["param"]
        if name not in params:
            defaults = (
                {p.name: p for p in get_part(module["part"]).config} if module.get("part") else {}
            )
            if name not in defaults:
                raise KeyError(f"{module['id']} has no config parameter {name!r}")
            params[name] = defaults[name].model_dump(mode="json")
            module["config"].append(params[name])
        params[name]["default"] = override["value"]
        changes.append(f"{module['id']}.{name}={override['value']}")
    return SystemSpec.model_validate(doc), changes
