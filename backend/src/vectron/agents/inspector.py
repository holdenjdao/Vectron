"""Inspector: the factory's quality gate. Any FAIL check stops the build before packaging."""

from __future__ import annotations

import ast

from vectron.codegen.files import GeneratedFile
from vectron.codegen.python.generator import md_cell
from vectron.domain.airframe import prop_clearance_mm
from vectron.domain.jobs import (
    ArtifactKind,
    CheckStatus,
    InspectionCheck,
    InspectionReport,
    JobRecord,
)
from vectron.domain.spec import SystemSpec
from vectron.orchestration import Agent, AgentError, AgentResult, RunContext

PASS, WARN, FAIL = CheckStatus.PASS, CheckStatus.WARN, CheckStatus.FAIL


class InspectorAgent(Agent):
    role = "inspector"
    display_name = "Inspector"
    description = "Statically verifies code, interfaces and physical design rules."

    async def run(self, ctx: RunContext) -> AgentResult:
        spec, record = ctx.spec, ctx.job.record
        report = InspectionReport(
            checks=[
                *_syntax_checks(ctx),
                *_coverage_checks(spec, record),
                *_isolation_checks(ctx, spec, record),
                *_interface_checks(spec),
                *_provenance_checks(record),
                *_airframe_checks(spec),
            ]
        )
        record.inspection = report
        ctx.save(_report_markdown(spec, report))
        counts = report.counts
        summary = f"{counts['pass']} pass, {counts['warn']} warn, {counts['fail']} fail"
        if not report.passed:
            raise AgentError(f"quality gate failed ({summary})")
        return AgentResult(summary=summary)


def _syntax_checks(ctx: RunContext) -> list[InspectionCheck]:
    python = [a for a in ctx.job.record.artifacts if a.media_type == "text/x-python"]
    broken = []
    for artifact in python:
        try:
            ast.parse(ctx.job.workspace.read(artifact.path))
        except SyntaxError as exc:
            broken.append(f"{artifact.path}: {exc.msg} (line {exc.lineno})")
    if broken:
        return [
            InspectionCheck(
                id="syntax", title="Python syntax", status=FAIL, detail="; ".join(broken)
            )
        ]
    return [
        InspectionCheck(
            id="syntax",
            title="Python syntax",
            status=PASS,
            detail=f"{len(python)} files parse cleanly",
        )
    ]


def _coverage_checks(spec: SystemSpec, record: JobRecord) -> list[InspectionCheck]:
    kinds: dict[str | None, set[ArtifactKind]] = {}
    for artifact in record.artifacts:
        kinds.setdefault(artifact.module_id, set()).add(artifact.kind)
    missing = [
        module.id
        for _, module in spec.iter_modules()
        if {ArtifactKind.SOURCE, ArtifactKind.TEST} - kinds.get(module.id, set())
    ]
    if missing:
        return [
            InspectionCheck(
                id="coverage",
                title="Every module has source and tests",
                status=FAIL,
                detail=f"missing: {', '.join(missing)}",
            )
        ]
    return [
        InspectionCheck(
            id="coverage",
            title="Every module has source and tests",
            status=PASS,
            detail=f"{spec.module_count} modules covered",
        )
    ]


def _isolation_checks(
    ctx: RunContext, spec: SystemSpec, record: JobRecord
) -> list[InspectionCheck]:
    """Modules may import the stdlib and ``..core`` only, never each other."""
    offenders = []
    for build in record.modules:
        tree = ast.parse(ctx.job.workspace.read(build.path))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ImportFrom)
                and node.level
                and not (node.module or "").startswith("core")
            ):
                offenders.append(f"{build.id} imports ..{node.module}")
            elif isinstance(node, ast.ImportFrom | ast.Import):
                names = (
                    [node.module]
                    if isinstance(node, ast.ImportFrom)
                    else [a.name for a in node.names]
                )
                if any((n or "").split(".")[0] == spec.package for n in names):
                    offenders.append(f"{build.id} imports the package directly")
    status = FAIL if offenders else PASS
    detail = "; ".join(offenders) or "modules depend only on the core runtime"
    return [InspectionCheck(id="isolation", title="Module isolation", status=status, detail=detail)]


def _interface_checks(spec: SystemSpec) -> list[InspectionCheck]:
    checks = []
    for topic in spec.topics:
        if topic.external or spec.publishers(topic.name):
            continue
        consumers = ", ".join(spec.subscribers(topic.name)) or "nobody"
        checks.append(
            InspectionCheck(
                id=f"producer:{topic.name}",
                title="Topic has no producer",
                status=WARN,
                detail=f"consumed by {consumers}; add a producing module or mark it external",
                target=topic.name,
            )
        )
    outputs = [t.name for t in spec.topics if not spec.subscribers(t.name)]
    checks.append(
        InspectionCheck(
            id="interfaces",
            title="Interface closure",
            status=PASS,
            detail=f"{len(spec.topics)} topics; system outputs: {', '.join(outputs) or 'none'}",
        )
    )
    return checks


def _provenance_checks(record: JobRecord) -> list[InspectionCheck]:
    stubs = [b.id for b in record.modules if b.provenance == "stub"]
    llm = [b.id for b in record.modules if b.provenance.startswith("llm:")]
    parts = [b.id for b in record.modules if b.provenance.startswith("part:")]
    checks = [
        InspectionCheck(
            id="parts",
            title="Certified parts",
            status=PASS,
            detail=f"{len(parts)} modules from the parts library",
        )
    ]
    if stubs:
        checks.append(
            InspectionCheck(
                id="stubs",
                title="Stubs awaiting implementation",
                status=WARN,
                detail=f"{', '.join(stubs)} (search for TODO(vectron))",
            )
        )
    if llm:
        checks.append(
            InspectionCheck(
                id="llm-review",
                title="LLM-fabricated code needs human review",
                status=WARN,
                detail=f"{', '.join(llm)} passed static vetting; run and review their tests",
            )
        )
    return checks


def _airframe_checks(spec: SystemSpec) -> list[InspectionCheck]:
    if spec.airframe is None:
        return []
    clearance = prop_clearance_mm(spec.airframe)
    if clearance < 0:
        status, detail = (
            WARN,
            (
                f"propeller discs overlap by {-clearance:.0f} mm: lengthen the arms or use "
                "smaller propellers"
            ),
        )
    elif clearance < 10:
        status, detail = WARN, f"only {clearance:.0f} mm tip clearance between propellers"
    else:
        status, detail = PASS, f"{clearance:.0f} mm tip clearance between propellers"
    return [
        InspectionCheck(
            id="prop-clearance",
            title="Propeller clearance",
            status=status,
            detail=detail,
            target="airframe",
        )
    ]


def _report_markdown(spec: SystemSpec, report: InspectionReport) -> GeneratedFile:
    icons = {PASS: "PASS", WARN: "WARN", FAIL: "FAIL"}
    counts = report.counts
    lines = [
        f"# Inspection report: {spec.name} ({spec.designation})",
        "",
        f"**{'PASSED' if report.passed else 'FAILED'}**: {counts['pass']} pass, "
        f"{counts['warn']} warn, {counts['fail']} fail. Checks are static: generated code "
        "is never executed by the factory; run `pytest` to exercise it.",
        "",
        "| Result | Check | Target | Detail |",
        "|---|---|---|---|",
    ]
    for check in report.checks:
        lines.append(
            f"| {icons[check.status]} | {md_cell(check.title)} | {md_cell(check.target or '')} | "
            f"{md_cell(check.detail)} |"
        )
    return GeneratedFile(
        "INSPECTION.md",
        "\n".join(lines) + "\n",
        ArtifactKind.DOC,
        "text/markdown",
        "Inspection report",
        "The Inspector's quality-gate results.",
    )
