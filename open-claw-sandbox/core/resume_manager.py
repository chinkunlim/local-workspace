# -*- coding: utf-8 -*-
"""
ResumeManager — OpenClaw Cross-Session Resume
=============================================
跨 Session 斷點續傳管理器。

設計原則（CLAUDE_v2.1.md D012）：
- 任何中斷（Ctrl+C、RAM 耗盡、程式崩潰）後重啟，自動從上次成功的狀態繼續
- resume_state.json 在每個 chunk 完成後立即寫入
- DAG cascade: chunk N 失敗 → chunk N+1 以後全部標記為 pending

與 audio-transcriber StateManager 的分工：
- StateManager: 管理「每個檔案在每個 Phase 的完成狀態」（已完成/處理中/待處理）
- ResumeManager: 管理「目前正在處理的 PDF 的 chunk-level 精細進度」

Usage:
    from core.resume_manager import ResumeManager

    rm = ResumeManager(base_dir="data/doc-parser")

    # 儲存 checkpoint
    rm.save_checkpoint(pdf_id="Psychology_Paper_05", phase="phase3", chunk_index=2)

    # 查詢是否可以恢復
    cp = rm.check_resumable(pdf_id="Psychology_Paper_05")
    if cp:
        print(f"Resume from phase={cp['phase']}, chunk={cp['chunk_index']}")

    # 完成後清除
    rm.clear_checkpoint(pdf_id="Psychology_Paper_05")
"""

import os
import json
import threading
from datetime import datetime
from typing import Optional, Dict, Any

from .atomic_writer import AtomicWriter


class ResumeManager:
    """
    Manages chunk-level resume state for PDF processing.

    Each PDF has its own resume_state.json stored in:
        data/doc-parser/state/resume/{pdf_id}/resume_state.json
    """

    def __init__(self, base_dir: str):
        """
        Args:
            base_dir: Root data directory for the skill (e.g. data/doc-parser).
        """
        self.base_dir = base_dir
        self.agent_core_dir = os.path.join(base_dir, "state", "resume")
        self._lock = threading.RLock()

    # ------------------------------------------------------------------ #
    #  Checkpoint Operations                                               #
    # ------------------------------------------------------------------ #

    def save_checkpoint(
        self,
        pdf_id: str,
        phase: str,
        chunk_index: int = 0,
        extra: Optional[Dict[str, Any]] = None,
    ):
        """
        Save a resume checkpoint for a PDF.

        Args:
            pdf_id: The PDF identifier (e.g. "Psychology_Paper_05").
            phase: Current pipeline phase (e.g. "phase1a", "phase3").
            chunk_index: If processing in chunks, the index of the NEXT chunk to process.
                         (i.e. chunks 0..chunk_index-1 are already complete)
            extra: Optional extra context to store (e.g. {"gem": "psychology_expert"}).
        """
        with self._lock:
            checkpoint_dir = os.path.join(self.agent_core_dir, pdf_id)
            os.makedirs(checkpoint_dir, exist_ok=True)
            checkpoint_path = os.path.join(checkpoint_dir, "resume_state.json")

            state = {
                "pdf_id": pdf_id,
                "phase": phase,
                "chunk_index": chunk_index,
                "saved_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                "status": "interrupted",
            }
            if extra:
                state.update(extra)

            AtomicWriter.write_json(checkpoint_path, state)

    def check_resumable(self, pdf_id: str) -> Optional[Dict[str, Any]]:
        """
        Check if a resume checkpoint exists for a PDF.

        Returns:
            The checkpoint dict if found and status is "interrupted", else None.
        """
        with self._lock:
            checkpoint_path = os.path.join(self.agent_core_dir, pdf_id, "resume_state.json")
            if not os.path.exists(checkpoint_path):
                return None
            try:
                with open(checkpoint_path, "r", encoding="utf-8") as f:
                    state = json.load(f)
                if state.get("status") == "interrupted":
                    return state
                return None
            except Exception:
                return None

    def clear_checkpoint(self, pdf_id: str):
        """
        Mark a PDF as fully completed (sets status to "completed").
        Keeps the file for audit purposes but removes the "interrupted" flag.
        """
        with self._lock:
            checkpoint_path = os.path.join(self.agent_core_dir, pdf_id, "resume_state.json")
            if not os.path.exists(checkpoint_path):
                return
            try:
                with open(checkpoint_path, "r", encoding="utf-8") as f:
                    state = json.load(f)
                state["status"] = "completed"
                state["completed_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                AtomicWriter.write_json(checkpoint_path, state)
            except Exception:
                pass

    def get_all_interrupted(self) -> Dict[str, Dict]:
        """
        Scan state/resume/ and return all PDFs with interrupted status.
        Used by main_app.py dashboard on startup.

        Returns:
            Dict mapping pdf_id → checkpoint dict
        """
        interrupted = {}
        with self._lock:
            if not os.path.exists(self.agent_core_dir):
                return interrupted

            for pdf_id in os.listdir(self.agent_core_dir):
                checkpoint = self.check_resumable(pdf_id)
                if checkpoint:
                    interrupted[pdf_id] = checkpoint
        return interrupted

    def resume_from(self, pdf_id: str) -> Optional[Dict[str, Any]]:
        """
        Convenience: load checkpoint and mark as "resuming".
        Returns checkpoint or None if not resumable.
        """
        with self._lock:
            checkpoint = self.check_resumable(pdf_id)
            if not checkpoint:
                return None

            # Mark as resuming
            checkpoint_path = os.path.join(self.agent_core_dir, pdf_id, "resume_state.json")
            try:
                with open(checkpoint_path, "r", encoding="utf-8") as f:
                    state = json.load(f)
                state["status"] = "resuming"
                state["resumed_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                AtomicWriter.write_json(checkpoint_path, state)
            except Exception:
                pass

            return checkpoint
