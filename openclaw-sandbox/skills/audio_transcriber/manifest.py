"""
skills/audio_transcriber/manifest.py — SkillManifest for Plugin Discovery (#17)
=================================================================================
This file is auto-discovered by core.SkillRegistry at startup.
No changes to core code are needed when adding new Skills.

To add a new Skill:
  1. Create skills/<skill-name>/manifest.py
  2. Define a MANIFEST variable of type SkillManifest
  3. Restart the system — SkillRegistry.discover() will auto-register it
"""

import os
import sys

# Ensure core is importable from the manifest context
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from core.orchestration.skill_registry import SkillManifest


def _run(**kwargs):
    """Lazy import to avoid loading heavy Phase modules at discovery time."""
    from scripts.run_all import VoiceMemoOrchestrator

    orch = VoiceMemoOrchestrator()
    orch.run(**kwargs)


MANIFEST = SkillManifest(
    skill_name="audio_transcriber",
    description=(
        "Transcribes audio files (m4a/mp3/wav) using Whisper with "
        "triple-layer anti-hallucination defence. Includes glossary "
        "generation, proofreading with feedback loop, and multi-file merge."
    ),
    phases=[
        "p0_glossary",
        "p1_transcribe",
        "p2_proofread",
        "p3_merge",
    ],
    cli_entry="scripts/run_all.py",
    run_fn=_run,
    file_types=[".m4a", ".mp3", ".wav"],
    tags=["audio", "transcription", "whisper", "proofread"],
)
