from __future__ import annotations

import asyncio

import pytest

from vectron.domain.jobs import BuildRequest, JobStatus, TaskStatus
from vectron.orchestration import Agent, AgentError, AgentResult, RunContext, TaskSpec
from vectron.service import Factory


async def test_offline_build_runs_the_whole_crew(factory: Factory) -> None:
    job = await factory.build(BuildRequest(blueprint_id="recon-drone"))
    record = job.record
    assert record.status is JobStatus.SUCCEEDED, record.error
    tasks = {t.id: t for t in record.tasks}
    assert all(t.status is TaskStatus.SUCCEEDED for t in record.tasks)

    # Delegation tree: Commander -> Architect -> crew (one Engineer per module) -> gates.
    assert tasks["plan"].parent_id is None
    assert tasks["architect"].parent_id == "plan"
    engineers = [t for t in record.tasks if t.role == "engineer"]
    assert len(engineers) == 13 and all(t.parent_id == "architect" for t in engineers)
    assert set(tasks["inspect"].depends_on) >= {"draft", "integrate", *(t.id for t in engineers)}
    assert "inspect" in tasks["package"].depends_on

    # Every task started only after its dependencies finished.
    for task in record.tasks:
        for dep in task.depends_on:
            assert tasks[dep].finished_at <= task.started_at  # type: ignore[operator]

    assert record.bundle is not None and record.bundle.file_count == len(record.artifacts)
    assert record.inspection is not None and record.inspection.passed
    provenance = {m.id: m.provenance for m in record.modules}
    assert provenance["motor_mixer"] == "part:multirotor-mixer"
    assert provenance["guidance_controller"] == "stub"
    assert [m.id for m in record.modules][:2] == ["gnss_receiver", "state_estimator"]


async def test_events_tell_the_story_in_order(factory: Factory) -> None:
    job = await factory.build(BuildRequest(blueprint_id="perimeter-radar-node"))
    events = job.events.since(-1)
    assert [e.seq for e in events] == list(range(len(events)))
    types = [e.type for e in events]
    assert types[0] == "job.queued" and types[-1] == "job.succeeded"
    assert types.count("task.succeeded") == len(job.record.tasks)
    assert types.count("artifact.created") == len(job.record.artifacts)
    assert job.events.closed


async def test_brief_only_build_is_planned_from_keywords(factory: Factory) -> None:
    job = await factory.build(BuildRequest(brief="counter-intrusion radar for the FOB perimeter"))
    assert job.record.status is JobStatus.SUCCEEDED
    assert job.record.blueprint_id == "perimeter-radar-node"


async def test_unmatched_brief_fails_with_a_useful_error(factory: Factory) -> None:
    job = await factory.build(BuildRequest(brief="a sandwich"))
    assert job.record.status is JobStatus.FAILED
    assert "could not match the brief" in (job.record.error or "")
    assert [t.id for t in job.record.tasks] == ["plan"]


async def test_failure_skips_dependents_and_fails_the_job(factory: Factory) -> None:
    class BrokenDraftsman(Agent):
        role = "draftsman"
        display_name = "Draftsman"
        description = "always fails"

        async def run(self, ctx: RunContext) -> AgentResult:
            raise AgentError("ink ran out")

    factory.orchestrator.agents = {**factory.orchestrator.agents, "draftsman": BrokenDraftsman()}
    job = await factory.build(BuildRequest(blueprint_id="ground-control-station"))
    tasks = {t.id: t for t in job.record.tasks}
    assert job.record.status is JobStatus.FAILED
    assert job.record.error == "Draftsman: ink ran out"
    assert tasks["draft"].status is TaskStatus.FAILED
    assert tasks["inspect"].status is TaskStatus.SKIPPED
    assert tasks["package"].status is TaskStatus.SKIPPED
    assert tasks["integrate"].status is TaskStatus.SUCCEEDED  # independent work still ran
    assert job.record.bundle is None


async def test_concurrency_limit_is_respected(factory: Factory) -> None:
    active = peak = 0
    real_engineer = factory.orchestrator.agents["engineer"]

    class SlowEngineer(Agent):
        role = "engineer"
        display_name = "Engineer"
        description = "tracks concurrency"

        async def run(self, ctx: RunContext) -> AgentResult:
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            await asyncio.sleep(0.01)
            active -= 1
            return await real_engineer.run(ctx)

    factory.orchestrator.agents = {**factory.orchestrator.agents, "engineer": SlowEngineer()}
    job = await factory.build(BuildRequest(blueprint_id="recon-drone"))
    assert job.record.status is JobStatus.SUCCEEDED
    assert 1 < peak <= factory.settings.max_concurrency


async def test_duplicate_spawn_fails_the_spawning_task(factory: Factory) -> None:
    class Twins(Agent):
        role = "planner"
        display_name = "Commander"
        description = "spawns the same id twice"

        async def run(self, ctx: RunContext) -> AgentResult:
            twin = TaskSpec("twin", "draftsman", "Twin")
            return AgentResult(summary="twins", spawn=(twin, twin))

    factory.orchestrator.agents = {**factory.orchestrator.agents, "planner": Twins()}
    job = await factory.build(BuildRequest(blueprint_id="recon-drone"))
    assert job.record.status is JobStatus.FAILED
    assert "duplicate task id" in (job.record.error or "")


async def test_cancelling_a_running_job_marks_it_failed(factory: Factory) -> None:
    class Stalled(Agent):
        role = "planner"
        display_name = "Commander"
        description = "never finishes"

        async def run(self, ctx: RunContext) -> AgentResult:
            await asyncio.sleep(3600)
            raise AssertionError("unreachable")

    factory.orchestrator.agents = {**factory.orchestrator.agents, "planner": Stalled()}
    job = factory.submit(BuildRequest(blueprint_id="recon-drone"))
    await asyncio.sleep(0.05)
    await factory.shutdown()
    assert job.record.status is JobStatus.FAILED
    assert job.record.error == "cancelled"
    assert job.events.closed


def test_unknown_blueprint_is_rejected_before_a_job_exists(factory: Factory) -> None:
    with pytest.raises(KeyError):
        factory.create_job(BuildRequest(blueprint_id="warp-drive"))
    assert factory.jobs() == []
