from core.orchestration.skill_registry import SkillManifest

MANIFEST = SkillManifest(
    skill_name="feynman_simulator",
    description=(
        "Two-agent Feynman Technique simulator: StudentAgent (local Ollama) explains "
        "notes in plain language; TutorAgent (Gemini via Playwright) fires Socratic "
        "challenges for 3 rounds. Blind spots are extracted and injected back into "
        "the original note as enriched Obsidian Markdown."
    ),
    phases=["p01_feynman_debate", "p02_debate_synthesis"],
    cli_entry="scripts/run_all.py",
    file_types=[".md"],
    tags=["feynman", "debate", "gemini", "multiagent", "learning"],
)
