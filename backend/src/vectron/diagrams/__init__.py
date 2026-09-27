"""Diagram renderers: SystemSpec -> Mermaid sources and SVG drawings."""

from __future__ import annotations

from vectron import __version__
from vectron.codegen.files import GeneratedFile
from vectron.diagrams import mermaid
from vectron.diagrams.airframe_svg import render_airframe_svg
from vectron.domain.jobs import ArtifactKind
from vectron.domain.spec import SystemSpec

MERMAID = "text/vnd.mermaid"


def _slug(identifier: str) -> str:
    return identifier.replace("_", "-")


def render_diagrams(spec: SystemSpec) -> list[GeneratedFile]:
    """Every diagram the spec supports, most visual first."""
    files: list[GeneratedFile] = []

    def add(slug: str, title: str, description: str, source: str) -> None:
        path = f"diagrams/{slug}.mmd"
        files.append(GeneratedFile(path, source, ArtifactKind.DIAGRAM, MERMAID, title, description))

    if spec.airframe is not None:
        files.append(
            GeneratedFile(
                "diagrams/airframe-top.svg",
                render_airframe_svg(spec),
                ArtifactKind.DIAGRAM,
                "image/svg+xml",
                "Airframe, top view",
                "Dimensioned drawing: rotor geometry, spin directions and component placement.",
            )
        )
    add(
        "system-architecture",
        "System architecture",
        "Subsystems and modules, with an edge wherever a topic connects two modules.",
        mermaid.system_architecture(spec),
    )
    add(
        "data-flow",
        "Interface data flow",
        "Every topic between its producers and consumers; the visual form of ICD.md.",
        mermaid.data_flow(spec),
    )
    for machine in spec.state_machines:
        add(
            _slug(machine.id),
            f"{machine.title} (state machine)",
            "States and transitions, rendered from the same table as the generated code.",
            mermaid.state_machine(machine),
        )
    for sequence in spec.sequences:
        add(
            _slug(sequence.id),
            f"{sequence.title} (sequence)",
            "Message exchange between modules and actors for this scenario.",
            mermaid.sequence(sequence),
        )
    add(
        "product-breakdown",
        "Product breakdown structure",
        "System, subsystems and modules as a hierarchy.",
        mermaid.product_breakdown(spec),
    )
    return files


def diagrams_markdown(spec: SystemSpec, diagrams: list[GeneratedFile]) -> GeneratedFile:
    """DIAGRAMS.md: every diagram inline, so they render on GitHub and in IDEs."""
    parts = [
        f"# Diagrams: {spec.name} ({spec.designation})",
        "",
        f"Rendered by Vectron {__version__} from the system spec (`vectron.spec.json`).",
        "Regenerate rather than edit: the spec is the single source of truth.",
    ]
    for diagram in diagrams:
        parts += ["", f"## {diagram.title}", "", diagram.description, ""]
        if diagram.media_type == MERMAID:
            parts += ["```mermaid", str(diagram.content).rstrip("\n"), "```"]
        else:
            parts.append(f"![{diagram.title}]({diagram.path})")
    return GeneratedFile(
        "DIAGRAMS.md",
        "\n".join(parts) + "\n",
        ArtifactKind.DOC,
        "text/markdown",
        "Diagram index",
        "All diagrams in one Markdown file (Mermaid renders on GitHub).",
    )
