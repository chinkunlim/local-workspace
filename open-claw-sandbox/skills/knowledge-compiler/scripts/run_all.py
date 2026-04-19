# -*- coding: utf-8 -*-
"""
knowledge-compiler — Open Claw Skill
====================================
Transforms raw markdown into structured wiki entries with bidirectional links.
"""

import os
import sys

# Core Bootstrap
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from core.bootstrap import ensure_core_path as _bootstrap
_bootstrap(__file__)

from core import PipelineBase, build_skill_parser, StateManager, SessionState
from phases.p01_compile import Phase1Compile

class CompilerOrchestrator(PipelineBase):
    def __init__(self):
        super().__init__(
            phase_key="orchestrator",
            phase_name="Knowledge Compiler 管線協調器",
            skill_name="knowledge-compiler"
        )
        self._state_manager = StateManager(self.base_dir, skill_name="knowledge-compiler")
        
    def run(self, args):
        self._state_manager.sync_physical_files()
        
        p1 = Phase1Compile()
        
        if p1.stop_requested:
            return
            
        p1.run(
            force=args.force,
            subject=args.subject,
            file_filter=args.file,
            single_mode=args.single
        )
        
        if p1.stop_requested:
            if p1.pause_requested:
                self._write_session_state(SessionState.PAUSED)
            else:
                self._write_session_state(SessionState.STOPPED)
        else:
            self._write_session_state(SessionState.COMPLETED)
            
        print("🏁 Knowledge Compiler 執行完畢。")

def main():
    parser = build_skill_parser("Knowledge Compiler", include_subject=True, include_force=True)
    args = parser.parse_args()
    CompilerOrchestrator().run(args)

if __name__ == "__main__":
    main()
