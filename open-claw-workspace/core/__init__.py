# -*- coding: utf-8 -*-
"""
OpenClaw Shared Core Framework
================================
Shared by all skills (voice-memo, pdf-knowledge, and future skills).

Usage:
    from core.pipeline_base import PipelineBase
    from core.state_manager import StateManager
    from core.llm_client import OllamaClient
    from core.security_manager import SecurityManager, SecurityViolationError
    from core.resume_manager import ResumeManager
"""

from .pipeline_base import PipelineBase
from .state_manager import StateManager
from .llm_client import OllamaClient
from .security_manager import SecurityManager, SecurityViolationError
from .resume_manager import ResumeManager

__all__ = [
    "PipelineBase",
    "StateManager",
    "OllamaClient",
    "SecurityManager",
    "SecurityViolationError",
    "ResumeManager",
]
