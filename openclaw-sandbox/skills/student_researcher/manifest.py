from core.orchestration.skill_registry import SkillManifest


def _run(**kw):
    from scripts.run_all import StudentResearcherOrchestrator

    StudentResearcherOrchestrator().run(**kw)


MANIFEST = SkillManifest(
    skill_name="student_researcher",
    description="Synthesizes final notes and applies APA format and Obsidian metadata.",
    phases=["p01_claim_extraction", "p02_synthesis"],
    cli_entry="scripts/run_all.py",
    run_fn=_run,
    file_types=[".md", ".json"],
    tags=["synthesis", "obsidian", "apa"],
)
