from scripts.run_all import StudentResearcherOrchestrator

from core.orchestration.skill_registry import SkillManifest

MANIFEST = SkillManifest(
    skill_name="student_researcher",
    description="Synthesizes final notes and applies APA format and Obsidian metadata.",
    phases=["p01_claim_extraction", "p02_synthesis"],
    cli_entry="scripts/run_all.py",
    run_fn=lambda **kw: StudentResearcherOrchestrator().run(**kw),
    file_types=[".md", ".json"],
    tags=["synthesis", "obsidian", "apa"],
)
