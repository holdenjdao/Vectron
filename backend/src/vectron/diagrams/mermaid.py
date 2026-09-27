"""Mermaid renderers. Each function turns part of a SystemSpec into diagram source.

Diagrams are rendered from the spec (never written by an LLM), so they always
match the generated code. Styling uses stroke colours and translucent fills that
read well on both light and dark backgrounds (GitHub, the Vectron UI).
"""

from __future__ import annotations

from vectron.domain.spec import SequenceSpec, StateMachineSpec, SystemSpec

CLASS_DEFS = (
    "  classDef part stroke:#1f9d6f,stroke-width:2px,fill:#1f9d6f1f",
    "  classDef stub stroke:#c98a0a,stroke-width:2px,stroke-dasharray:5 3,fill:#c98a0a14",
    "  classDef ext stroke:#2b8fd6,stroke-width:1.5px,fill:#2b8fd61a",
    "  classDef topic stroke:#7b8ea3,stroke-width:1px,fill:#7b8ea314",
)


def text(value: str) -> str:
    """Escape free text for use inside Mermaid labels."""
    value = " ".join(str(value).split())
    for char, code in (("#", "#35;"), ('"', "#quot;"), ("<", "#lt;"), (">", "#gt;"), (";", "#59;")):
        value = value.replace(char, code)
    return value


def _module_node(module_id: str) -> str:
    return f"m_{module_id}"


def _topic_node(topic: str) -> str:
    return "t_" + topic.replace(".", "_")


def system_architecture(spec: SystemSpec) -> str:
    """Subsystems as groups, modules as nodes, edges wherever a topic connects two modules."""
    lines = ["flowchart LR", *CLASS_DEFS]
    externals = [t for t in spec.topics if t.external]
    if externals:
        lines.append('  subgraph external["External sources"]')
        for topic in externals:
            label = f"{text(topic.name)}<br/><small>{text(topic.message)}</small>"
            lines.append(f'    {_topic_node(topic.name)}[/"{label}"/]:::ext')
        lines.append("  end")
    for subsystem in spec.subsystems:
        lines.append(f'  subgraph {subsystem.id}["{text(subsystem.name)}"]')
        for module in subsystem.modules:
            style = "part" if module.part else "stub"
            lines.append(f'    {_module_node(module.id)}["{text(module.name)}"]:::{style}')
        lines.append("  end")
    edges: list[str] = []
    for topic in spec.topics:
        sources = (
            [_topic_node(topic.name)]
            if topic.external
            else [_module_node(m) for m in spec.publishers(topic.name)]
        )
        for source in sources:
            for target in spec.subscribers(topic.name):
                edge = f"  {source} --> {_module_node(target)}"
                if edge not in edges:
                    edges.append(edge)
    return "\n".join(lines + edges) + "\n"


def data_flow(spec: SystemSpec) -> str:
    """Interface view: every topic as a node between its producers and consumers."""
    lines = ["flowchart LR", *CLASS_DEFS]
    for topic in spec.topics:
        style = "ext" if topic.external else "topic"
        label = f"{text(topic.name)}<br/><small>{text(topic.message)}</small>"
        lines.append(f'  {_topic_node(topic.name)}(["{label}"]):::{style}')
    for _, module in spec.iter_modules():
        style = "part" if module.part else "stub"
        lines.append(f'  {_module_node(module.id)}["{text(module.name)}"]:::{style}')
    for topic in spec.topics:
        node = _topic_node(topic.name)
        for publisher in spec.publishers(topic.name):
            lines.append(f"  {_module_node(publisher)} --> {node}")
        for subscriber in spec.subscribers(topic.name):
            lines.append(f"  {node} --> {_module_node(subscriber)}")
    return "\n".join(lines) + "\n"


def state_machine(machine: StateMachineSpec) -> str:
    lines = ["stateDiagram-v2", f"  [*] --> {machine.initial}"]
    for transition in machine.transitions:
        lines.append(f"  {transition.source} --> {transition.target} : {text(transition.trigger)}")
    return "\n".join(lines) + "\n"


def sequence(seq: SequenceSpec) -> str:
    arrows = {"sync": "->>", "async": "-)", "reply": "-->>"}
    lines = ["sequenceDiagram", "  autonumber"]
    for participant in seq.participants:
        keyword = "actor" if participant.kind == "actor" else "participant"
        lines.append(f"  {keyword} {participant.id} as {text(participant.label)}")
    for step in seq.steps:
        lines.append(f"  {step.source}{arrows[step.kind]}{step.target}: {text(step.message)}")
        if step.note:
            span = step.source if step.source == step.target else f"{step.source},{step.target}"
            lines.append(f"  Note over {span}: {text(step.note)}")
    return "\n".join(lines) + "\n"


def product_breakdown(spec: SystemSpec) -> str:
    """Product breakdown structure (system > subsystems > modules) as a mindmap."""

    def label(value: str) -> str:
        return text(value).replace("(", "").replace(")", "").replace("[", "").replace("]", "")

    lines = ["mindmap", f"  root(({label(spec.designation)} {label(spec.name)}))"]
    for subsystem in spec.subsystems:
        lines.append(f"    {subsystem.id}[{label(subsystem.name)}]")
        for module in subsystem.modules:
            lines.append(f"      {_module_node(module.id)}({label(module.name)})")
    return "\n".join(lines) + "\n"
