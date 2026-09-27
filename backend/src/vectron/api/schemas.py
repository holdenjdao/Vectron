"""API response shapes that are not domain records (see frontend/src/api/types.ts)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from vectron.domain.blueprint import Blueprint, OptionChoice


class LLMStatus(BaseModel):
    provider: str
    model: str | None
    enabled: bool
    detail: str


class HealthInfo(BaseModel):
    status: str = "ok"
    version: str
    banner: str
    llm: LLMStatus


class OptionOut(BaseModel):
    key: str
    label: str
    type: str
    default: Any
    help: str
    unit: str
    choices: list[OptionChoice]
    min: float | None
    max: float | None
    step: float | None


class BlueprintSummary(BaseModel):
    id: str
    name: str
    designation: str
    category: str
    summary: str
    keywords: list[str]
    stats: dict[str, int]
    options: list[OptionOut]

    @classmethod
    def of(cls, blueprint: Blueprint) -> BlueprintSummary:
        return cls(
            id=blueprint.id,
            name=blueprint.name,
            designation=blueprint.designation,
            category=blueprint.category,
            summary=blueprint.summary,
            keywords=blueprint.keywords,
            stats=blueprint.stats,
            options=[OptionOut.model_validate(o.model_dump()) for o in blueprint.options],
        )


class ModuleOut(BaseModel):
    id: str
    name: str
    responsibility: str
    part: str | None


class SubsystemOut(BaseModel):
    id: str
    name: str
    description: str
    modules: list[ModuleOut]


class BlueprintDetail(BlueprintSummary):
    subsystems: list[SubsystemOut]

    @classmethod
    def of(cls, blueprint: Blueprint) -> BlueprintDetail:
        spec = blueprint.instantiate()
        subsystems = [
            SubsystemOut(
                id=s.id,
                name=s.name,
                description=s.description,
                modules=[
                    ModuleOut(id=m.id, name=m.name, responsibility=m.responsibility, part=m.part)
                    for m in s.modules
                ],
            )
            for s in spec.subsystems
        ]
        return cls(**BlueprintSummary.of(blueprint).model_dump(), subsystems=subsystems)
