from core.orchestration.skill_registry import SkillManifest


def _run(**kw):
    from scripts.run_all import GeminiVerifierOrchestrator

    GeminiVerifierOrchestrator().run(**kw)


MANIFEST = SkillManifest(
    skill_name="gemini_verifier_agent",
    description="Cross-verifies claims via simulated dialogue with Gemini over Playwright.",
    phases=["p01_ai_debate"],
    cli_entry="scripts/run_all.py",
    run_fn=_run,
    file_types=[".json"],
    tags=["verification", "gemini", "playwright"],
)
