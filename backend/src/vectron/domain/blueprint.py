"""Blueprints: catalog entries that seed a SystemSpec.

A blueprint is a parameterized spec document plus catalog metadata. Options
declared by the blueprint are written into the spec document at dotted paths
(``applies_to``) before validation, so one blueprint can yield many variants
(e.g. quad vs. hex frame) without any code changes.
"""

from __future__ import annotations

import copy
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .spec import Identifier, Slug, SystemSpec
from .values import SpecValueError, coerce

Category = Literal["air", "ground", "maritime", "sensor", "c2", "space"]


class OptionChoice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: str
    label: str


class BlueprintOption(BaseModel):
    """A user-tunable build parameter."""

    model_config = ConfigDict(extra="forbid")

    key: Identifier
    label: str
    type: Literal["choice", "number", "boolean"]
    default: Any
    help: str = ""
    unit: str = ""
    choices: list[OptionChoice] = Field(default_factory=list)
    min: float | None = None
    max: float | None = None
    step: float | None = None
    applies_to: list[str] = Field(min_length=1)
    """Dotted paths into the spec document. List items are matched by ``id`` or ``name``."""

    @model_validator(mode="after")
    def _check(self) -> BlueprintOption:
        if self.type == "choice" and not self.choices:
            raise ValueError(f"option {self.key} needs choices")
        self.default = self.coerce(self.default)
        return self

    def coerce(self, value: Any) -> Any:
        if self.type == "choice":
            allowed = {c.value for c in self.choices}
            if value not in allowed:
                raise SpecValueError(f"{self.key} must be one of {sorted(allowed)}")
            return value
        if self.type == "boolean":
            return coerce("bool", value)
        number = coerce("float", value)
        if self.min is not None and number < self.min:
            raise SpecValueError(f"{self.key} must be >= {self.min}")
        if self.max is not None and number > self.max:
            raise SpecValueError(f"{self.key} must be <= {self.max}")
        if number.is_integer() and (self.step is None or float(self.step).is_integer()):
            return int(number)  # keep counts like battery cells integral
        return number


class Blueprint(BaseModel):
    """A catalog entry: metadata, options and the seed spec document."""

    model_config = ConfigDict(extra="forbid")

    id: Slug
    name: str
    designation: str
    category: Category
    summary: str
    keywords: list[str] = Field(default_factory=list)
    options: list[BlueprintOption] = Field(default_factory=list)
    spec: dict[str, Any]

    def resolve_options(self, requested: dict[str, Any]) -> dict[str, Any]:
        """Merge requested values over defaults, validating each one."""
        known = {o.key: o for o in self.options}
        unknown = set(requested) - set(known)
        if unknown:
            raise SpecValueError(f"unknown option(s) for {self.id}: {sorted(unknown)}")
        return {
            key: option.coerce(requested[key]) if key in requested else option.default
            for key, option in known.items()
        }

    def instantiate(self, options: dict[str, Any] | None = None, brief: str = "") -> SystemSpec:
        """Produce a validated SystemSpec for the given option values."""
        values = self.resolve_options(options or {})
        document = copy.deepcopy(self.spec)
        for option in self.options:
            for path in option.applies_to:
                _set_path(document, path, values[option.key])
        document.update(
            id=self.id,
            name=self.name,
            designation=self.designation,
            summary=self.summary,
            brief=brief,
        )
        return SystemSpec.model_validate(document)

    @property
    def stats(self) -> dict[str, int]:
        subsystems = self.spec.get("subsystems", [])
        return {
            "subsystems": len(subsystems),
            "modules": sum(len(s.get("modules", [])) for s in subsystems),
        }


def _set_path(document: dict[str, Any], path: str, value: Any) -> None:
    """Set ``value`` at a dotted path; list segments match items by ``id``/``name``."""
    node: Any = document
    parts = path.split(".")
    for index, part in enumerate(parts):
        last = index == len(parts) - 1
        if isinstance(node, list):
            match = next(
                (
                    item
                    for item in node
                    if isinstance(item, dict) and part in (item.get("id"), item.get("name"))
                ),
                None,
            )
            if match is None:
                raise KeyError(f"option path {path!r}: no list item named {part!r}")
            if last:
                raise KeyError(f"option path {path!r} must end at a field, not a list item")
            node = match
        elif isinstance(node, dict):
            if last:
                node[part] = value
                return
            if part not in node:
                node[part] = {}
            node = node[part]
        else:
            raise KeyError(f"option path {path!r}: cannot descend into {part!r}")
