"""Engineer: fabricates one module (source + tests). One Engineer runs per module, in parallel.

Order of preference: a certified part from the parts library, then an LLM
implementation that passes static vetting, then a stub with contract tests.
"""

from __future__ import annotations

import json

from vectron.codegen.files import CodegenError
from vectron.codegen.python.generator import ModuleSource, polish_python
from vectron.domain.jobs import ModuleBuild
from vectron.llm.base import LLMError
from vectron.orchestration import Agent, AgentError, AgentResult, RunContext

from .prompts import load_prompt
from .vetting import VettingError, vet_module_source, vet_test_source

SOURCE_SCHEMA = {
    "type": "object",
    "properties": {
        "module_source": {"type": "string"},
        "test_source": {"type": "string"},
        "notes": {"type": "string"},
    },
    "required": ["module_source", "test_source", "notes"],
    "additionalProperties": False,
}


class EngineerAgent(Agent):
    role = "engineer"
    display_name = "Engineer"
    description = "Fabricates one module and its tests from a part, an LLM, or a stub."

    async def run(self, ctx: RunContext) -> AgentResult:
        spec = ctx.spec
        module_id = ctx.params.get("module_id", "")
        try:
            subsystem, module = spec.module(module_id)
        except KeyError as exc:
            raise AgentError(str(exc)) from exc

        notes: list[str] = []
        rendered: ModuleSource | None = None
        if module.part is None and ctx.llm.enabled:
            try:
                rendered, llm_notes = await self._fabricate(ctx, module_id)
                if llm_notes:
                    notes.append(llm_notes[:500])
            except (LLMError, CodegenError, VettingError, KeyError) as exc:
                notes.append(f"LLM fabrication rejected, stub generated instead: {exc}")
                ctx.log(notes[-1])
        if rendered is None:
            try:
                rendered = ctx.target.render_module(spec, module_id)
            except CodegenError as exc:
                raise AgentError(str(exc)) from exc

        files = ctx.target.module_files(spec, rendered)
        for file in files:
            ctx.save(file)
        build = ModuleBuild(
            id=module.id,
            name=module.name,
            subsystem=subsystem.name,
            class_name=module.class_name,
            responsibility=module.responsibility,
            path=files[0].path,
            test_path=files[1].path,
            provenance=rendered.provenance,
            notes=notes,
        )
        order = [m.id for _, m in spec.iter_modules()]
        builds = [b for b in ctx.job.record.modules if b.id != module.id] + [build]
        ctx.job.record.modules[:] = sorted(builds, key=lambda b: order.index(b.id))
        return AgentResult(summary=f"{module.class_name} <- {rendered.provenance}")

    async def _fabricate(self, ctx: RunContext, module_id: str) -> tuple[ModuleSource, str]:
        spec, target = ctx.spec, ctx.target
        subsystem, module = spec.module(module_id)
        stub = target.stub_source(spec, module_id)
        stub_test = target.render_module(spec, module_id).test
        context = {
            "system": {"name": spec.name, "designation": spec.designation, "summary": spec.summary},
            "subsystem": subsystem.name,
            "module": module.model_dump(mode="json"),
        }
        prompt = "\n\n".join(
            [
                f"<system_context>\n{json.dumps(context, indent=1)}\n</system_context>",
                f"<mission_brief>\n{spec.brief or '(none)'}\n</mission_brief>",
                f"<messages>\n{target.render_core(spec, 'messages')}</messages>",
                f"<core_module_api>\n{target.render_core(spec, 'module')}</core_module_api>",
                f"<geo_helpers>\n{target.render_core(spec, 'geo')}</geo_helpers>",
                f'<stub path="{target.module_path(spec, subsystem, module)}">\n{stub}</stub>',
                f'<stub_test path="{target.test_path(module)}">\n{stub_test}</stub_test>',
                "Implement the module and its tests.",
            ]
        )
        result = await ctx.ask_llm(
            purpose=f"implement {module.class_name}",
            system=load_prompt("engineer"),
            prompt=prompt,
            schema=SOURCE_SCHEMA,
        )
        source, test = result.data["module_source"], result.data["test_source"]
        vet_module_source(source, module)
        vet_test_source(test, spec.package)
        rendered = ModuleSource(
            module_id=module.id,
            source=polish_python(source, spec.package, target.module_path(spec, subsystem, module)),
            test=polish_python(test, spec.package, target.test_path(module)),
            provenance=f"llm:{result.model}",
        )
        return rendered, str(result.data.get("notes", "")).strip()
