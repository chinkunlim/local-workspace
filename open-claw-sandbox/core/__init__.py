"""
OpenClaw Shared Core Framework
================================
Shared by all skills (audio-transcriber, doc-parser, and future skills).

Usage:
    from core.pipeline_base import PipelineBase
    from core.state_manager import StateManager
    from core.llm_client import OllamaClient
    from core.security_manager import SecurityManager, SecurityViolationError
    from core.resume_manager import ResumeManager
"""

from .atomic_writer import AtomicWriter
from .bootstrap import ensure_core_path
from .cli import build_skill_parser
from .cli_config_wizard import main as run_config_wizard
from .config_manager import ConfigManager
from .config_validation import ConfigValidationError, ConfigValidator
from .data_layout import DataLayoutManager, DataLayoutPlan
from .diff_engine import AuditEngine, DiffEngine
from .error_classifier import ClassifiedError, ErrorCategory, classify_exception
from .inbox_daemon import SystemInboxDaemon
from .llm_client import OllamaClient
from .log_manager import build_logger, log_exception
from .path_builder import PathBuilder
from .pipeline_base import PipelineBase
from .resume_manager import ResumeManager
from .security_manager import SecurityManager, SecurityViolationError
from .session_state import SessionState, read_session_state, write_session_state
from .state_manager import StateManager

__all__ = [
    "AtomicWriter",
    "AuditEngine",
    "ClassifiedError",
    "ConfigManager",
    "ConfigValidationError",
    "ConfigValidator",
    "DataLayoutManager",
    "DataLayoutPlan",
    "DiffEngine",
    "ErrorCategory",
    "OllamaClient",
    "PathBuilder",
    "PipelineBase",
    "ResumeManager",
    "SecurityManager",
    "SecurityViolationError",
    "SessionState",
    "StateManager",
    "SystemInboxDaemon",
    "build_logger",
    "build_skill_parser",
    "classify_exception",
    "ensure_core_path",
    "log_exception",
    "read_session_state",
    "run_config_wizard",
    "write_session_state",
]
