"""The blueprint catalog: YAML files shipped in ``blueprints/data``.

Adding a system to the factory is a data change, not a code change: drop a new
YAML file in the data directory (or point ``VECTRON_BLUEPRINT_DIRS`` at another
directory) and it appears in the catalog and the UI.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from importlib import resources
from pathlib import Path

import yaml

from vectron.domain.blueprint import Blueprint

_CATEGORY_ORDER = {"air": 0, "ground": 1, "maritime": 2, "sensor": 3, "c2": 4, "space": 5}


class BlueprintError(ValueError):
    """A blueprint file failed to load or validate."""


class BlueprintCatalog:
    def __init__(self, blueprints: Iterable[Blueprint]) -> None:
        ordered = sorted(blueprints, key=lambda b: (_CATEGORY_ORDER[b.category], b.name))
        self._by_id = {b.id: b for b in ordered}
        if len(self._by_id) != len(ordered):
            raise BlueprintError("duplicate blueprint ids in catalog")

    @classmethod
    def load(cls, extra_dirs: Iterable[Path] = ()) -> BlueprintCatalog:
        """Load the built-in blueprints plus any YAML files in ``extra_dirs``."""
        sources: list[tuple[str, str]] = []
        data = resources.files("vectron.blueprints") / "data"
        for entry in sorted(data.iterdir(), key=lambda e: e.name):
            if entry.name.endswith((".yaml", ".yml")):
                sources.append((entry.name, entry.read_text(encoding="utf-8")))
        for directory in extra_dirs:
            for path in sorted(Path(directory).glob("*.y*ml")):
                sources.append((str(path), path.read_text(encoding="utf-8")))
        return cls(parse_blueprint(text, name) for name, text in sources)

    def list(self) -> list[Blueprint]:
        return list(self._by_id.values())

    def get(self, blueprint_id: str) -> Blueprint:
        try:
            return self._by_id[blueprint_id]
        except KeyError:
            raise KeyError(f"unknown blueprint {blueprint_id!r}") from None

    def match(self, brief: str) -> list[tuple[Blueprint, int]]:
        """Rank blueprints by keyword hits in a free-text brief (offline intent matching)."""
        words = set(re.findall(r"[a-z0-9]+", brief.lower()))
        scored = []
        for blueprint in self._by_id.values():
            vocabulary = {k.lower() for k in blueprint.keywords}
            vocabulary |= set(re.findall(r"[a-z0-9]+", blueprint.name.lower()))
            score = len(words & vocabulary)
            if score:
                scored.append((blueprint, score))
        return sorted(scored, key=lambda item: -item[1])


def parse_blueprint(text: str, source: str = "<string>") -> Blueprint:
    """Parse and fully validate one blueprint document (including its default spec)."""
    try:
        blueprint = Blueprint.model_validate(yaml.safe_load(text))
        blueprint.instantiate()
    except Exception as exc:
        raise BlueprintError(f"{source}: {exc}") from exc
    return blueprint
