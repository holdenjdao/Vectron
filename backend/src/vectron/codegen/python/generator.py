"""Python target: renders a SystemSpec into an installable, tested Python package.

Rendering is deterministic: the same spec always yields byte-identical files.
Every Python file goes through isort and black, which normalises formatting and
doubles as a syntax check. Templates live next to this module in ``templates/``.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import black
import isort
from jinja2 import Environment, PackageLoader, StrictUndefined

from vectron import __version__
from vectron.codegen.files import CodegenError, GeneratedFile
from vectron.codegen.python.parts import Part, get_part, merged_config
from vectron.domain.jobs import ArtifactKind
from vectron.domain.spec import (
    ConfigParam,
    FieldSpec,
    ModuleSpec,
    SubsystemSpec,
    SystemSpec,
)
from vectron.domain.values import default_for

LINE_LENGTH = 100
PYTHON_MEDIA_TYPE = "text/x-python"

PY_TYPES = {
    "float": "float",
    "int": "int",
    "bool": "bool",
    "str": "str",
    "bytes": "bytes",
    "vec3": "tuple[float, float, float]",
    "float[]": "tuple[float, ...]",
    "int[]": "tuple[int, ...]",
    "str[]": "tuple[str, ...]",
}


@dataclass(frozen=True)
class ModuleSource:
    """Rendered source and test for one module."""

    module_id: str
    source: str
    test: str
    provenance: str


# -- literal and text helpers -------------------------------------------


def py_literal(value: Any) -> str:
    """Render an already-validated spec value as Python source."""
    if value is None or isinstance(value, bool):
        return repr(value)
    if isinstance(value, int | float | bytes):
        return repr(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, tuple | list):
        items = [py_literal(item) for item in value]
        return f"({items[0]},)" if len(items) == 1 else f"({', '.join(items)})"
    raise CodegenError(f"cannot render {type(value).__name__} as a Python literal")


def clean_text(text: str) -> str:
    """Single-line text that is safe inside docstrings and comments."""
    return " ".join(str(text).replace("\\", "/").replace('"', "'").split())


def wrap_words(text: str, first_width: int, cont_width: int) -> list[str]:
    """Greedy word wrap with a different width for the first line."""
    lines: list[str] = []
    current, limit = "", first_width
    for word in clean_text(text).split(" "):
        candidate = f"{current} {word}" if current else word
        if current and len(candidate) > limit:
            lines.append(current)
            current, limit = word, cont_width
        else:
            current = candidate
    lines.append(current)
    return lines


def docwrap(text: str, first_col: int, cont_col: int | None = None, width: int = 96) -> str:
    """Word-wrap ``text`` whose first line starts at column ``first_col``."""
    cont_col = first_col if cont_col is None else cont_col
    lines = wrap_words(text, width - first_col, width - cont_col)
    return ("\n" + " " * cont_col).join(lines)


def commentwrap(text: str, indent: int) -> str:
    """Wrap ``text`` into ``#`` comments; the template supplies the first line's indent."""
    lines = wrap_words(text, width := 96 - indent - 2, width)
    return ("\n" + " " * indent).join(f"# {line}" for line in lines)


def message_call(sample: dict[str, Any]) -> str:
    """``Message(t=t, field=value, ...)`` for a simulation input."""
    args = ["t=t"] + [f"{k}={py_literal(v)}" for k, v in sample["fields"].items() if k != "t"]
    return f"{sample['message']}({', '.join(args)})"


def provenance_badge(provenance: str) -> str:
    kind, _, detail = provenance.partition(":")
    return f"**{kind}** `{detail}`" if detail else f"**{kind}**"


def md_cell(text: Any) -> str:
    return clean_text(str(text)).replace("|", "\\|")


def topic_attr(topic: str) -> str:
    return topic.replace(".", "_")


def field_doc(field: FieldSpec) -> str:
    unit = f" [{field.unit}]" if field.unit else ""
    doc = field.doc or field.name.replace("_", " ").capitalize() + "."
    return f"{field.name}: {doc}{unit}"


def param_doc(param: ConfigParam) -> str:
    unit = f" [{param.unit}]" if param.unit else ""
    doc = param.doc or param.name.replace("_", " ").capitalize() + "."
    return f"{param.name}: {doc}{unit}"


def polish_python(source: str, package: str, path: str) -> str:
    """Sort imports and format; raises CodegenError if the source does not parse."""
    try:
        sorted_source = isort.code(
            source, profile="black", line_length=LINE_LENGTH, known_first_party=[package]
        )
        return black.format_str(sorted_source, mode=black.Mode(line_length=LINE_LENGTH))
    except Exception as exc:  # black raises several parse error types
        raise CodegenError(f"{path}: generated Python is invalid: {exc}") from exc


# -- the target -----------------------------------------------------------


class PythonTarget:
    """Renders scaffold (core runtime, wiring, docs) and module files."""

    language = "python"

    def __init__(self) -> None:
        env = Environment(
            loader=PackageLoader("vectron.codegen.python", "templates"),
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
            autoescape=False,
        )
        env.filters.update(
            py=py_literal,
            pytype=lambda field_type: PY_TYPES[field_type],
            docwrap=docwrap,
            commentwrap=commentwrap,
            md=md_cell,
        )
        env.globals.update(
            version=__version__,
            field_doc=field_doc,
            param_doc=param_doc,
            field_default=lambda f: py_literal(
                f.default if f.default is not None else default_for(f.type)
            ),
            topic_attr=topic_attr,
            message_call=message_call,
            provenance_badge=provenance_badge,
        )
        self.env = env

    # paths ---------------------------------------------------------------

    @staticmethod
    def module_path(spec: SystemSpec, subsystem: SubsystemSpec, module: ModuleSpec) -> str:
        return f"src/{spec.package}/{subsystem.id}/{module.id}.py"

    @staticmethod
    def test_path(module: ModuleSpec) -> str:
        return f"tests/test_{module.id}.py"

    # scaffold --------------------------------------------------------------

    def scaffold(self, spec: SystemSpec) -> list[GeneratedFile]:
        """Everything except the per-module sources: core runtime, wiring, docs."""
        pkg = f"src/{spec.package}"
        ctx = self._base_context(spec)
        files = [
            self._py(f"{pkg}/__init__.py", "project/package_init.py.j2", ctx, "Package root"),
            self._py(f"{pkg}/__main__.py", "project/main.py.j2", ctx, "Entry point"),
            self._py(
                f"{pkg}/app.py",
                "project/app.py.j2",
                ctx,
                "Composition root",
                "Instantiates every module on one bus and runs the scheduler.",
            ),
            self._py(
                f"{pkg}/sim.py",
                "project/sim.py.j2",
                ctx,
                "Smoke-test input feed",
                "Publishes the spec's sample inputs; replace with drivers or a simulator.",
            ),
            self._py(f"{pkg}/core/__init__.py", "core/__init__.py.j2", ctx, "Core runtime"),
            self._py(
                f"{pkg}/core/bus.py",
                "core/bus.py.j2",
                ctx,
                "Message bus",
                "In-process publish/subscribe bus shared by all modules.",
            ),
            self._py(
                f"{pkg}/core/module.py",
                "core/module.py.j2",
                ctx,
                "Module base class",
                "Lifecycle and interface-contract enforcement for modules.",
            ),
            self._py(
                f"{pkg}/core/messages.py",
                "core/messages.py.j2",
                ctx,
                "Message types",
                "Immutable dataclasses for every message in the ICD.",
            ),
            self._py(f"{pkg}/core/topics.py", "core/topics.py.j2", ctx, "Topic registry"),
            self._py(f"{pkg}/core/geo.py", "core/geo.py.j2", ctx, "Geodesy helpers"),
            self._py(
                "tests/test_app.py",
                "project/test_app.py.j2",
                ctx,
                "Integration test",
                "Builds the whole system and runs the smoke simulation.",
                ArtifactKind.TEST,
            ),
        ]
        for subsystem in spec.subsystems:
            sub_ctx = {**ctx, "subsystem": subsystem}
            files.append(
                self._py(
                    f"{pkg}/{subsystem.id}/__init__.py",
                    "project/subsystem_init.py.j2",
                    sub_ctx,
                    f"{subsystem.name} package",
                )
            )
        files += [
            self._text(
                "pyproject.toml",
                "project/pyproject.toml.j2",
                ctx,
                ArtifactKind.CONFIG,
                "application/toml",
                "Project metadata",
                "Packaging, pytest and ruff config.",
            ),
            self._text(
                ".gitignore",
                "project/gitignore.j2",
                ctx,
                ArtifactKind.CONFIG,
                "text/plain",
                "Git ignore rules",
            ),
            self._text(
                "ICD.md",
                "project/ICD.md.j2",
                ctx,
                ArtifactKind.DOC,
                "text/markdown",
                "Interface Control Document",
                "Every topic, message and field, with producers and consumers.",
            ),
        ]
        return files

    def readme(self, spec: SystemSpec, **extra: Any) -> GeneratedFile:
        ctx = {**self._base_context(spec), **extra}
        return self._text(
            "README.md",
            "project/README.md.j2",
            ctx,
            ArtifactKind.DOC,
            "text/markdown",
            "README",
            "Overview, quick start and module index.",
        )

    def module_readme(self, spec: SystemSpec, module_id: str, **extra: Any) -> str:
        subsystem, module = spec.module(module_id)
        ctx = {**self._base_context(spec), "subsystem": subsystem, "module": module, **extra}
        return self.env.get_template("project/MODULE.md.j2").render(ctx)

    # modules ---------------------------------------------------------------

    def part_for(self, spec: SystemSpec, module_id: str) -> Part | None:
        """The module's library part, or None when it should be stubbed."""
        _, module = spec.module(module_id)
        if not module.part:
            return None
        part = get_part(module.part)
        problems = part.check(spec, module)
        if problems:
            raise CodegenError(f"module {module_id}: " + "; ".join(problems))
        return part

    def render_module(self, spec: SystemSpec, module_id: str) -> ModuleSource:
        """Render from the parts library when the module names a part, else a stub."""
        subsystem, module = spec.module(module_id)
        part = self.part_for(spec, module_id)
        if part is None:
            ctx = self._module_context(spec, subsystem, module, None, "stub")
            source = self._render("module/stub.py.j2", ctx)
            test = self._render("module/stub_test.py.j2", ctx)
            provenance = "stub"
        else:
            provenance = f"part:{part.id}"
            ctx = self._module_context(spec, subsystem, module, part, provenance)
            source = self._render(part.template, ctx)
            test = self._render(part.test_template, ctx)
        return ModuleSource(
            module_id=module.id,
            source=polish_python(source, spec.package, self.module_path(spec, subsystem, module)),
            test=polish_python(test, spec.package, self.test_path(module)),
            provenance=provenance,
        )

    def module_files(self, spec: SystemSpec, rendered: ModuleSource) -> list[GeneratedFile]:
        subsystem, module = spec.module(rendered.module_id)
        return [
            GeneratedFile(
                path=self.module_path(spec, subsystem, module),
                content=rendered.source,
                kind=ArtifactKind.SOURCE,
                media_type=PYTHON_MEDIA_TYPE,
                title=f"{module.name} ({module.class_name})",
                description=module.responsibility,
                module_id=module.id,
            ),
            GeneratedFile(
                path=self.test_path(module),
                content=rendered.test,
                kind=ArtifactKind.TEST,
                media_type=PYTHON_MEDIA_TYPE,
                title=f"Tests for {module.class_name}",
                description=f"pytest suite for {module.name}.",
                module_id=module.id,
            ),
        ]

    def stub_source(self, spec: SystemSpec, module_id: str) -> str:
        """The stub rendering of a module (used as the starting point for LLM agents)."""
        subsystem, module = spec.module(module_id)
        ctx = self._module_context(spec, subsystem, module, None, "stub")
        return polish_python(
            self._render("module/stub.py.j2", ctx),
            spec.package,
            self.module_path(spec, subsystem, module),
        )

    def render_core(self, spec: SystemSpec, name: str) -> str:
        """Polished source of one core runtime file (``messages``, ``module``, ``geo``...)."""
        path = f"src/{spec.package}/core/{name}.py"
        return polish_python(
            self._render(f"core/{name}.py.j2", self._base_context(spec)), spec.package, path
        )

    def module_context_messages(self, spec: SystemSpec, module_id: str) -> list[str]:
        """Message type names a module touches (for prompts and bundles)."""
        _, module = spec.module(module_id)
        return sorted({spec.topic(t).message for t in (*module.subscribes, *module.publishes)})

    # internals -------------------------------------------------------------

    def _base_context(self, spec: SystemSpec) -> dict[str, Any]:
        modules = list(spec.iter_modules())
        used_in_sim = sorted({spec.topic(s.topic).message for s in spec.simulation})
        return {
            "spec": spec,
            "package": spec.package,
            "modules": modules,
            "topic_messages": sorted({t.message for t in spec.topics}),
            "external_topics": sorted(t.name for t in spec.topics if t.external),
            "sim_messages": used_in_sim,
            "sim_inputs": [
                {
                    "index": index,
                    "topic": sample.topic,
                    "message": spec.topic(sample.topic).message,
                    "fields": sample.fields,
                    "at_s": sample.at_s,
                    "period": (1.0 / sample.rate_hz) if sample.rate_hz else None,
                }
                for index, sample in enumerate(spec.simulation)
            ],
        }

    def _module_context(
        self,
        spec: SystemSpec,
        subsystem: SubsystemSpec,
        module: ModuleSpec,
        part: Part | None,
        provenance: str,
    ) -> dict[str, Any]:
        carried = {t: spec.topic(t).message for t in (*module.subscribes, *module.publishes)}

        def finder(topics: list[str], direction: str) -> Callable[[str], str]:
            def find(message: str) -> str:
                matches = [t for t in topics if carried[t] == message]
                if len(matches) != 1:
                    raise CodegenError(
                        f"module {module.id} must {direction} exactly one {message} topic"
                    )
                return matches[0]

            return find

        std_imports = {"from dataclasses import dataclass"}
        if module.subscribes:
            std_imports |= {
                "from collections.abc import Callable, Mapping",
                "from typing import Any",
            }
        if part:
            std_imports |= {s if s.startswith("from ") else f"import {s}" for s in part.stdlib}
        core_imports = [
            "from ..core.bus import MessageBus",
            "from ..core.module import Module",
        ]
        if carried:
            core_imports.append(
                f"from ..core.messages import {', '.join(sorted(set(carried.values())))}"
            )
        if part and part.geo:
            core_imports.append(f"from ..core.geo import {', '.join(sorted(part.geo))}")

        width = max((len(t) for t in carried), default=0)
        interface_lines = [
            f"{direction:<4} {topic:<{width}}  {carried[topic]}"
            for direction, topics in (("in", module.subscribes), ("out", module.publishes))
            for topic in topics
        ] or ["(none)"]
        labels = {
            "stub": "stub (scaffold only; behaviour not implemented yet)",
        }
        ctx: dict[str, Any] = {
            **self._base_context(spec),
            "subsystem": subsystem,
            "module": module,
            "part": part,
            "class_name": module.class_name,
            "config_class": f"{module.class_name}Config",
            "config": merged_config(part, module),
            "provenance": provenance,
            "provenance_label": labels.get(provenance, f"{provenance} (Vectron parts library)"),
            "std_imports": sorted(std_imports),
            "core_imports": sorted(core_imports),
            "interface_lines": interface_lines,
            "msgtype": lambda topic: carried[topic],
            "sub": finder(module.subscribes, "subscribe to"),
            "pub": finder(module.publishes, "publish"),
            "topic_map": lambda topics: (
                "{" + ", ".join(f"{py_literal(t)}: {carried[t]}" for t in topics) + "}"
            ),
            "test_messages": sorted({carried[t] for t in module.subscribes}),
        }
        if part and part.context:
            ctx.update(part.context(spec, module))
        return ctx

    def _render(self, template: str, ctx: dict[str, Any]) -> str:
        return self.env.get_template(template).render(ctx)

    def _py(
        self,
        path: str,
        template: str,
        ctx: dict[str, Any],
        title: str,
        description: str = "",
        kind: ArtifactKind = ArtifactKind.SOURCE,
    ) -> GeneratedFile:
        source = polish_python(self._render(template, ctx), ctx["package"], path)
        return GeneratedFile(path, source, kind, PYTHON_MEDIA_TYPE, title, description)

    def _text(
        self,
        path: str,
        template: str,
        ctx: dict[str, Any],
        kind: ArtifactKind,
        media_type: str,
        title: str,
        description: str = "",
    ) -> GeneratedFile:
        return GeneratedFile(
            path, self._render(template, ctx), kind, media_type, title, description
        )
