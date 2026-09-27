"""System specification: the single source of truth for a build.

Everything Vectron produces (diagrams, code, interface documents) is rendered
from a validated :class:`SystemSpec`. Agents, including LLM-backed ones, only
ever *edit the spec*; the renderers that turn it into artifacts are
deterministic. That keeps diagrams and code from drifting apart, and it means
untrusted model output is validated here before it can reach generated code.
"""

from __future__ import annotations

import keyword
from collections.abc import Iterator
from typing import Annotated, Any, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

from .values import FieldType, ScalarType, coerce


def _not_keyword(value: str) -> str:
    if keyword.iskeyword(value):
        raise ValueError(f"{value!r} is a reserved word")
    return value


Identifier = Annotated[
    str,
    StringConstraints(pattern=r"^[a-z][a-z0-9_]*$", max_length=48),
    AfterValidator(_not_keyword),
]
"""snake_case name usable as a Python identifier, file name or C symbol."""

ClassName = Annotated[str, StringConstraints(pattern=r"^[A-Z][A-Za-z0-9]*$", max_length=48)]
TopicName = Annotated[
    str, StringConstraints(pattern=r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$", max_length=64)
]
Symbol = Annotated[str, StringConstraints(pattern=r"^[A-Z][A-Z0-9_]*$", max_length=48)]
"""UPPER_SNAKE name for states and triggers."""
Slug = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9-]*$", max_length=64)]
Text = Annotated[str, StringConstraints(max_length=2000)]

RESERVED_CLASS_NAMES = frozenset({"Module", "MessageBus", "Config"})
RESERVED_SUBSYSTEM_IDS = frozenset({"core", "app", "sim", "tests"})


class SpecModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FieldSpec(SpecModel):
    name: Identifier
    type: FieldType
    unit: str = ""
    doc: Text = ""
    default: Any = None

    @model_validator(mode="after")
    def _coerce_default(self) -> FieldSpec:
        if self.default is not None:
            self.default = coerce(self.type, self.default)
        return self


class MessageSpec(SpecModel):
    """A typed, immutable message exchanged between modules."""

    name: ClassName
    doc: Text = ""
    fields: list[FieldSpec] = Field(default_factory=list)

    @model_validator(mode="after")
    def _ensure_timestamp(self) -> MessageSpec:
        if self.name in RESERVED_CLASS_NAMES:
            raise ValueError(f"message name {self.name!r} is reserved")
        _unique([f.name for f in self.fields], f"field in message {self.name}")
        if not any(f.name == "t" for f in self.fields):
            stamp = FieldSpec(name="t", type="float", unit="s", doc="Timestamp, seconds.")
            self.fields.insert(0, stamp)
        return self

    def field(self, name: str) -> FieldSpec:
        for spec in self.fields:
            if spec.name == name:
                return spec
        raise KeyError(f"message {self.name} has no field {name!r}")


class TopicSpec(SpecModel):
    """A named channel carrying one message type."""

    name: TopicName
    message: ClassName
    doc: Text = ""
    external: bool = False
    """True when produced outside the system boundary (sensors, operators)."""


class ConfigParam(SpecModel):
    name: Identifier
    type: ScalarType
    default: Any
    unit: str = ""
    doc: Text = ""

    @model_validator(mode="after")
    def _coerce_default(self) -> ConfigParam:
        self.default = coerce(self.type, self.default)
        return self


class ModuleSpec(SpecModel):
    """An independently buildable unit of behaviour."""

    id: Identifier
    name: str
    responsibility: Text
    subscribes: list[TopicName] = Field(default_factory=list)
    publishes: list[TopicName] = Field(default_factory=list)
    config: list[ConfigParam] = Field(default_factory=list)
    part: str | None = None
    """Parts-library implementation to use; ``None`` generates a stub."""
    state_machine: Identifier | None = None
    rate_hz: float | None = Field(default=None, gt=0, le=1000)

    @property
    def class_name(self) -> str:
        return "".join(chunk.capitalize() for chunk in self.id.split("_") if chunk)

    @model_validator(mode="after")
    def _check_lists(self) -> ModuleSpec:
        _unique(self.subscribes, f"subscription in module {self.id}")
        _unique(self.publishes, f"publication in module {self.id}")
        _unique([p.name for p in self.config], f"config param in module {self.id}")
        return self


class SubsystemSpec(SpecModel):
    id: Identifier
    name: str
    description: Text = ""
    modules: list[ModuleSpec] = Field(default_factory=list)


class StateSpec(SpecModel):
    name: Symbol
    doc: Text = ""


class TransitionSpec(SpecModel):
    source: Symbol
    target: Symbol
    trigger: Symbol
    doc: Text = ""


class StateMachineSpec(SpecModel):
    id: Identifier
    title: str
    initial: Symbol
    states: list[StateSpec]
    transitions: list[TransitionSpec]

    @model_validator(mode="after")
    def _check_graph(self) -> StateMachineSpec:
        names = [s.name for s in self.states]
        _unique(names, f"state in {self.id}")
        if self.initial not in names:
            raise ValueError(f"initial state {self.initial!r} is not declared in {self.id}")
        seen: set[tuple[str, str]] = set()
        for tr in self.transitions:
            for end in (tr.source, tr.target):
                if end not in names:
                    raise ValueError(f"transition references unknown state {end!r} in {self.id}")
            key = (tr.source, tr.trigger)
            if key in seen:
                raise ValueError(f"{self.id}: {tr.trigger} from {tr.source} is ambiguous")
            seen.add(key)
        return self

    @property
    def triggers(self) -> list[str]:
        return sorted({t.trigger for t in self.transitions})


class Participant(SpecModel):
    id: Identifier
    label: str
    kind: Literal["module", "actor"] = "module"


class SequenceStep(SpecModel):
    source: Identifier
    target: Identifier
    message: str
    note: Text = ""
    kind: Literal["sync", "async", "reply"] = "async"


class SequenceSpec(SpecModel):
    id: Identifier
    title: str
    participants: list[Participant]
    steps: list[SequenceStep]

    @model_validator(mode="after")
    def _check_steps(self) -> SequenceSpec:
        ids = [p.id for p in self.participants]
        _unique(ids, f"participant in {self.id}")
        for step in self.steps:
            for end in (step.source, step.target):
                if end not in ids:
                    raise ValueError(f"sequence {self.id} references unknown participant {end!r}")
        return self


class ComponentSpec(SpecModel):
    """A labelled component placed on the airframe body (x forward, y right, mm)."""

    id: Identifier
    label: str
    x_mm: float = 0.0
    y_mm: float = 0.0
    w_mm: float = Field(default=30.0, gt=0, le=1000)
    h_mm: float = Field(default=20.0, gt=0, le=1000)
    shape: Literal["rect", "circle"] = "rect"


class AirframeSpec(SpecModel):
    """Physical parameters for multirotor air vehicles."""

    layout: Literal["quad-x", "quad-plus", "hex-x", "octo-x"] = "quad-x"
    arm_length_mm: float = Field(default=225.0, ge=50, le=2000)
    prop_diameter_in: float = Field(default=10.0, ge=2, le=40)
    body_length_mm: float = Field(default=170.0, ge=20, le=2000)
    body_width_mm: float = Field(default=110.0, ge=20, le=2000)
    mass_kg: float = Field(default=1.6, gt=0, le=150)
    components: list[ComponentSpec] = Field(default_factory=list)


class SimulationInput(SpecModel):
    """Sample input injected by the generated smoke simulation."""

    topic: TopicName
    fields: dict[str, Any] = Field(default_factory=dict)
    at_s: float | None = Field(default=None, ge=0)
    """Publish once at this simulation time."""
    rate_hz: float | None = Field(default=None, gt=0, le=1000)
    """Publish periodically. When neither is set the input is published every step."""


class SystemSpec(SpecModel):
    id: Slug
    name: str
    designation: str
    package: Identifier
    summary: Text
    description: Text = ""
    brief: Text = ""
    messages: list[MessageSpec]
    topics: list[TopicSpec]
    subsystems: list[SubsystemSpec]
    state_machines: list[StateMachineSpec] = Field(default_factory=list)
    sequences: list[SequenceSpec] = Field(default_factory=list)
    airframe: AirframeSpec | None = None
    simulation: list[SimulationInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_references(self) -> SystemSpec:
        messages = {m.name for m in self.messages}
        _unique([m.name for m in self.messages], "message")
        _unique([t.name for t in self.topics], "topic")
        _unique([s.id for s in self.subsystems], "subsystem")
        _unique([m.id for _, m in self.iter_modules()], "module")
        _unique([m.class_name for _, m in self.iter_modules()], "module class name")
        _unique([sm.id for sm in self.state_machines], "state machine")
        _unique([sq.id for sq in self.sequences], "sequence")

        topics = {t.name: t for t in self.topics}
        for topic in self.topics:
            if topic.message not in messages:
                raise ValueError(f"topic {topic.name} uses unknown message {topic.message!r}")
        for subsystem in self.subsystems:
            if subsystem.id in RESERVED_SUBSYSTEM_IDS:
                raise ValueError(f"subsystem id {subsystem.id!r} is reserved")
        machines = {sm.id for sm in self.state_machines}
        for _, module in self.iter_modules():
            if module.class_name in messages:
                raise ValueError(f"module {module.id} class name clashes with a message")
            for topic in (*module.subscribes, *module.publishes):
                if topic not in topics:
                    raise ValueError(f"module {module.id} references unknown topic {topic!r}")
            for topic in module.publishes:
                if topics[topic].external:
                    raise ValueError(f"module {module.id} publishes external topic {topic!r}")
            if module.state_machine and module.state_machine not in machines:
                raise ValueError(
                    f"module {module.id} references unknown state machine {module.state_machine!r}"
                )
        for sample in self.simulation:
            if sample.topic not in topics:
                raise ValueError(f"simulation input references unknown topic {sample.topic!r}")
            message = self.message(topics[sample.topic].message)
            types = {f.name: f.type for f in message.fields}
            for name, value in list(sample.fields.items()):
                if name not in types:
                    raise ValueError(f"simulation input sets unknown field {message.name}.{name}")
                sample.fields[name] = coerce(types[name], value)
        return self

    # -- lookups ---------------------------------------------------------

    def iter_modules(self) -> Iterator[tuple[SubsystemSpec, ModuleSpec]]:
        for subsystem in self.subsystems:
            for module in subsystem.modules:
                yield subsystem, module

    def module(self, module_id: str) -> tuple[SubsystemSpec, ModuleSpec]:
        for subsystem, module in self.iter_modules():
            if module.id == module_id:
                return subsystem, module
        raise KeyError(f"unknown module {module_id!r}")

    def message(self, name: str) -> MessageSpec:
        for message in self.messages:
            if message.name == name:
                return message
        raise KeyError(f"unknown message {name!r}")

    def topic(self, name: str) -> TopicSpec:
        for topic in self.topics:
            if topic.name == name:
                return topic
        raise KeyError(f"unknown topic {name!r}")

    def state_machine(self, machine_id: str) -> StateMachineSpec:
        for machine in self.state_machines:
            if machine.id == machine_id:
                return machine
        raise KeyError(f"unknown state machine {machine_id!r}")

    def publishers(self, topic: str) -> list[str]:
        return [m.id for _, m in self.iter_modules() if topic in m.publishes]

    def subscribers(self, topic: str) -> list[str]:
        return [m.id for _, m in self.iter_modules() if topic in m.subscribes]

    @property
    def module_count(self) -> int:
        return sum(len(s.modules) for s in self.subsystems)


def _unique(values: list[str], what: str) -> None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"duplicate {what}: {value!r}")
        seen.add(value)
