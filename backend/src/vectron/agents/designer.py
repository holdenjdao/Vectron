"""New-system design: the Architect's path when no catalog blueprint fits the brief.

Claude proposes a complete architecture as structured JSON; it is converted into
a SystemSpec and fully validated. If validation fails, the errors are sent back
once for a corrected design. The result feeds the same deterministic renderers
and Engineers as any blueprint.
"""

from __future__ import annotations

import json
import keyword
import re
from typing import Any

from pydantic import ValidationError

from vectron.domain.spec import SystemSpec
from vectron.domain.values import FIELD_TYPES
from vectron.llm.base import LLMError
from vectron.orchestration import AgentError, RunContext

from .prompts import load_prompt

MAX_ATTEMPTS = 2

_S = {"type": "string"}
_SYMBOLS = {"type": "array", "items": _S}


def _obj(properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


DESIGN_SCHEMA = _obj(
    {
        "name": _S,
        "designation": _S,
        "package": _S,
        "summary": _S,
        "description": _S,
        "rationale": _S,
        "messages": {
            "type": "array",
            "items": _obj(
                {
                    "name": _S,
                    "doc": _S,
                    "fields": {
                        "type": "array",
                        "items": _obj(
                            {
                                "name": _S,
                                "type": {"type": "string", "enum": list(FIELD_TYPES)},
                                "unit": _S,
                                "doc": _S,
                            }
                        ),
                    },
                }
            ),
        },
        "topics": {
            "type": "array",
            "items": _obj({"name": _S, "message": _S, "doc": _S, "external": {"type": "boolean"}}),
        },
        "subsystems": {
            "type": "array",
            "items": _obj(
                {
                    "id": _S,
                    "name": _S,
                    "description": _S,
                    "modules": {
                        "type": "array",
                        "items": _obj(
                            {
                                "id": _S,
                                "name": _S,
                                "responsibility": _S,
                                "subscribes": _SYMBOLS,
                                "publishes": _SYMBOLS,
                            }
                        ),
                    },
                }
            ),
        },
        "state_machines": {
            "type": "array",
            "items": _obj(
                {
                    "id": _S,
                    "title": _S,
                    "initial": _S,
                    "states": {"type": "array", "items": _obj({"name": _S, "doc": _S})},
                    "transitions": {
                        "type": "array",
                        "items": _obj({"source": _S, "trigger": _S, "target": _S}),
                    },
                }
            ),
        },
        "sequences": {
            "type": "array",
            "items": _obj(
                {
                    "id": _S,
                    "title": _S,
                    "participants": {
                        "type": "array",
                        "items": _obj(
                            {
                                "id": _S,
                                "label": _S,
                                "kind": {"type": "string", "enum": ["module", "actor"]},
                            }
                        ),
                    },
                    "steps": {
                        "type": "array",
                        "items": _obj({"source": _S, "target": _S, "message": _S, "note": _S}),
                    },
                }
            ),
        },
    }
)


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug if slug[:1].isalpha() else f"system-{slug}".strip("-")


def _package(text: str, name: str) -> str:
    package = re.sub(r"[^a-z0-9_]+", "_", (text or name).lower()).strip("_")[:40]
    if not package[:1].isalpha() or keyword.iskeyword(package):
        package = f"sys_{package}".rstrip("_")
    return package


def to_spec(design: dict[str, Any], brief: str) -> SystemSpec:
    """Convert the designer's JSON into a validated SystemSpec (raises ValidationError)."""
    name = str(design.get("name") or "New System").strip()
    return SystemSpec.model_validate(
        {
            "id": _slug(name)[:64],
            "name": name,
            "designation": str(design.get("designation") or "VX-NEW1").strip()[:32],
            "package": _package(str(design.get("package", "")), name),
            "summary": design.get("summary", ""),
            "description": design.get("description", ""),
            "brief": brief,
            "messages": design.get("messages", []),
            "topics": design.get("topics", []),
            "subsystems": design.get("subsystems", []),
            "state_machines": design.get("state_machines", []),
            "sequences": design.get("sequences", []),
        }
    )


async def design_spec(ctx: RunContext, brief: str) -> tuple[SystemSpec, str]:
    """Ask the model for a new architecture, retrying once with validation feedback."""
    if not ctx.llm.enabled:
        raise AgentError(
            "no catalog blueprint fits this brief and designing a new system needs Claude; "
            "start Vectron with the Claude engine or pick a blueprint"
        )
    prompt = f"<brief>\n{brief}\n</brief>\n\nDesign the system."
    problem = ""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            result = await ctx.ask_llm(
                purpose="design a new system architecture from the brief",
                system=load_prompt("designer"),
                prompt=prompt,
                schema=DESIGN_SCHEMA,
                effort="high",
            )
        except LLMError as exc:
            raise AgentError(f"new-system design failed: {exc}") from exc
        try:
            return to_spec(result.data, brief), str(result.data.get("rationale", "")).strip()
        except (ValidationError, ValueError) as exc:
            problem = str(exc)[:2000]
            ctx.log(f"Design attempt {attempt} did not validate; requesting a correction")
            prompt = (
                f"<brief>\n{brief}\n</brief>\n\n<previous_design>\n"
                f"{json.dumps(result.data)}\n</previous_design>\n\n<validation_errors>\n"
                f"{problem}\n</validation_errors>\n\nReturn a corrected, complete design."
            )
    raise AgentError(f"the proposed design did not validate: {problem[:400]}")
