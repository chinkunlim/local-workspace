from core.orchestration.skill_registry import SkillManifest


def _run(**kw):
    from scripts.run_all import AcademicLibraryOrchestrator

    AcademicLibraryOrchestrator().run(**kw)


MANIFEST = SkillManifest(
    skill_name="academic_library_agent",
    description="Crosses paywalls and uses institutional login to fetch high-quality literature.",
    phases=["p01_search_literature"],
    cli_entry="scripts/run_all.py",
    run_fn=_run,
    file_types=[".txt", ".json", ".md"],
    tags=["research", "scraper", "playwright"],
)
