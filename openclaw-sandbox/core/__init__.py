"""
OpenClaw Shared Core Framework
================================
Shared by all skills (audio_transcriber, doc_parser, and future skills).

Usage:
    from core.orchestration.pipeline_base import PipelineBase
    from core.state.state_manager import StateManager
    from core.ai.llm_client import OllamaClient
    from core.services.security_manager import SecurityManager, SecurityViolationError
    from core.state.resume_manager import ResumeManager
"""

from core.ai.llm_client import OllamaClient
from core.cli.cli import build_skill_parser
from core.cli.cli_config_wizard import main as run_config_wizard
from core.config.config_manager import ConfigManager
from core.config.config_validation import ConfigValidationError, ConfigValidator
from core.orchestration.pipeline_base import PipelineBase
from core.services.inbox_daemon import SystemInboxDaemon
from core.services.security_manager import SecurityManager, SecurityViolationError
from core.state.resume_manager import ResumeManager
from core.state.session_state import SessionState, read_session_state, write_session_state
from core.state.state_manager import StateManager
from core.utils.atomic_writer import AtomicWriter
from core.utils.bootstrap import ensure_core_path
from core.utils.data_layout import DataLayoutManager, DataLayoutPlan
from core.utils.diff_engine import AuditEngine, DiffEngine
from core.utils.error_classifier import ClassifiedError, ErrorCategory, classify_exception
from core.utils.log_manager import build_logger, log_exception
from core.utils.path_builder import PathBuilder

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
