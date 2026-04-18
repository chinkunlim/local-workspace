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
from .config_manager import ConfigManager
from .path_builder import PathBuilder
from .atomic_writer import AtomicWriter
from .config_validation import ConfigValidator, ConfigValidationError
from .error_classifier import ErrorCategory, ClassifiedError, classify_exception
from .log_manager import build_logger, log_exception
from .cli import build_skill_parser
from .data_layout import DataLayoutManager, DataLayoutPlan
from .diff_engine import DiffEngine, AuditEngine
from .inbox_daemon import SystemInboxDaemon
from .cli_config_wizard import main as run_config_wizard
from .bootstrap import ensure_core_path
from .session_state import SessionState, write_session_state, read_session_state

__all__ = [
    "PipelineBase",
    "StateManager",
    "OllamaClient",
    "SecurityManager",
    "SecurityViolationError",
    "ResumeManager",
    "ConfigManager",
    "PathBuilder",
    "AtomicWriter",
    "ConfigValidator",
    "ConfigValidationError",
    "ErrorCategory",
    "ClassifiedError",
    "classify_exception",
    "build_logger",
    "log_exception",
    "build_skill_parser",
    "DataLayoutManager",
    "DataLayoutPlan",
    "DiffEngine",
    "AuditEngine",
    "SystemInboxDaemon",
    "run_config_wizard",
    "ensure_core_path",
    "SessionState",
    "write_session_state",
    "read_session_state",
]
