# -*- coding: utf-8 -*-
"""
Orchestrator: Full 5-Phase Pipeline Runner (+ Phase 0 Glossary)
V7.0 OOP Architecture — with Checkpoint Resume, Sorted Tasks, Batch Reprocess UI
"""
import os
import sys

# --- Boundary-Safe Initialization ---
# scripts/run_all.py → scripts → skills/voice-memo → open-claw-workspace → local-workspace
_script_dir = os.path.dirname(os.path.abspath(__file__))
_skill_root = os.path.dirname(os.path.dirname(_script_dir))  # skills/voice-memo
_openclawed_root = os.path.dirname(_skill_root)  # open-claw-workspace
_core_dir = os.path.abspath(os.path.join(_openclawed_root, "core"))
_workspace_root = os.environ.get(
    "WORKSPACE_DIR",
    os.path.dirname(_openclawed_root)  # local-workspace
)

# Enforce sandbox boundary: only core and this skill
sys.path = [_core_dir, _script_dir]

workspace_root = _workspace_root
base_dir = os.path.join(_openclawed_root, "data", "voice-memo")

# --- Import Core and Phases ---
from core import StateManager
from phases.phase0_glossary import Phase0Glossary
from phases.phase1_transcribe import Phase1Transcribe
from phases.phase2_proofread import Phase2Proofread
from phases.phase3_merge import Phase3Merge
from phases.phase4_highlight import Phase4Highlight
from phases.phase5_synthesis import Phase5NotionSynthesis
from core import ConfigManager, build_skill_parser

_runtime_config = ConfigManager(_openclawed_root, "voice-memo")

def print_status_dashboard(state_mgr: StateManager):
    """Print the DAG / Cache status."""
    counters = {f"p{i}": {"done": 0, "total": 0} for i in range(1, 6)}

    for subj_data in state_mgr.state.values():
        for fname, record in subj_data.items():
            for key in counters:
                counters[key]["total"] += 1
                if record.get(key) == "✅":
                    counters[key]["done"] += 1

    labels = {
        "p1": "P1 轉錄",
        "p2": "P2 校對",
        "p3": "P3 合併",
        "p4": "P4 重點",
        "p5": "P5 筆記",
    }
    print("\n" + "=" * 36)
    print("     📊 V7.0 狀態與 DAG 追蹤面板")
    print("=" * 36)
    for key, label in labels.items():
        done = counters[key]["done"]
        total = counters[key]["total"]
        if done == total and total > 0:
            status_icon = "✅"
        elif done > 0:
            status_icon = "⏳"
        else:
            status_icon = "❌"
        print(f"  [{label}]: {status_icon} {done}/{total}")
    print("=" * 36 + "\n")

def preflight_check():
    import requests
    print("=" * 50)
    print("✈️  進行啟動前置檢查 (Preflight Check)...")
    fail = False

    raw_dir = os.path.join(base_dir, "raw_data")
    if not os.path.exists(raw_dir) or not any(f.endswith(".m4a") for r, d, fl in os.walk(raw_dir) for f in fl):
        print("❌ 錯誤：找不到任何 .m4a 來源。")
        fail = True

    try:
        ollama_cfg = _runtime_config.get_section("runtime", {}).get("ollama", {})
        api_url = ollama_cfg.get("api_url")
        if not api_url:
            raise RuntimeError("voice-memo runtime.ollama.api_url is missing")
        tags_url = api_url.replace("/generate", "/tags")
        requests.get(tags_url, timeout=3).raise_for_status()
    except Exception:
        print("❌ 錯誤：無法連線至 Ollama (`ollama serve`)。")
        fail = True

    try:
        import tqdm, pypdf, mlx_whisper
    except ImportError as e:
        print(f"❌ 錯誤：缺少必要套件 {e.name}")
        fail = True

    if fail:
        sys.exit(1)
    print("✅ 檢查通過。")

def check_and_resume(sm: StateManager) -> dict:
    """
    啟動時偵測是否有未完成的 checkpoint。
    若有，詢問使用者是否從上次暫停點繼續。
    回傳 checkpoint dict 或 None。
    """
    cp = sm.load_checkpoint()
    if not cp:
        return None

    saved_at = cp.get("saved_at", "不明")
    print("\n" + "═" * 56)
    print("📌 偵測到上次暫停的斷點 (Checkpoint)")
    print(f"   時間：{saved_at}")
    print(f"   科目：{cp.get('subject', '?')}")
    print(f"   檔案：{cp.get('filename', '?')}")
    print(f"   Phase：{cp.get('phase_key', '?').upper()}")
    print("═" * 56)
    print("請選擇：")
    print("  [C] Continue — 從上次斷點繼續")
    print("  [N] New       — 全新開始（清除 Checkpoint）")

    try:
        choice = input("請輸入 (C/N) [Enter = C]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\n已選擇全新開始。")
        sm.clear_checkpoint()
        return None

    if choice == "n":
        sm.clear_checkpoint()
        print("🗑️  Checkpoint 已清除，全新開始。")
        return None
    else:
        print("➩️  從斷點繼續。")
        return cp

def main():
    preflight_check()
    parser = build_skill_parser(
        "V7.0 Voice Memo Pipeline 五階段處理",
        include_subject=True,
        include_force=True,
        include_resume=True,
        include_interactive=True,
        include_start_phase=True,
    )
    parser.add_argument("--glossary", action="store_true")
    parser.add_argument("--glossary-merge", action="store_true")
    parser.add_argument("--glossary-force", action="store_true")
    args = parser.parse_args()

    sm = StateManager(base_dir)
    sm.sync_physical_files()

    # --- Checkpoint Resume 偵測 ---
    resume_from = None
    if args.resume:
        # --resume flag：強制從 checkpoint 繼續
        resume_from = sm.load_checkpoint()
        if resume_from:
            print(f"➩️  [強制斷點續傳] {resume_from.get('subject')} / {resume_from.get('filename')} @ {resume_from.get('phase_key', '').upper()}")
        else:
            print("❗  --resume 指定但尚無 Checkpoint，將從頭開始。")
    elif not args.force:
        # 非 force 模式下，自動偵測暫停斷點並詢問
        resume_from = check_and_resume(sm)

    print_status_dashboard(sm)

    if args.glossary:
        print("\n" + "=" * 50)
        print("📚 Phase 0: 詞庫自動生成...")
        print("=" * 50)
        Phase0Glossary().run(force=args.glossary_force, merge=args.glossary_merge, subject=args.subject)

    phases = {
        1: Phase1Transcribe(),
        2: Phase2Proofread(),
        3: Phase3Merge(),
        4: Phase4Highlight(),
        5: Phase5NotionSynthesis(),
    }

    try:
        for p_num in range(args.start_phase, 6):
            if p_num not in phases:
                continue
            print(f"\n{'=' * 50}")
            print(f"🚀 開始執行 Phase {p_num}...")
            print(f"{'=' * 50}")

            p_obj = phases[p_num]
            if p_obj.stop_requested:
                break

            # 斷點續傳：將 resume_from 傳進各 Phase
            # 只有當前 Phase 的 phase_key 符合 checkpoint 時才啟動跳迈邏輯
            phase_resume = None
            if resume_from:
                cp_phase = resume_from.get("phase_key", "")
                if cp_phase == p_obj.phase_key:
                    phase_resume = resume_from
                # 若 checkpoint 是更早的 phase，本 Phase 全量執行

            p_obj.run(force=args.force, subject=args.subject, resume_from=phase_resume)

            # Phase 完成後重置 resume_from，防止下一 Phase 誤用 checkpoint
            resume_from = None

            # 偵測使用者是否選擇暫停（由 SIGINT handler 設定 pause_requested）
            if p_obj.stop_requested:
                if p_obj.pause_requested:
                    print("💾 Pipeline 已暫停並儲存進度，下次執行自動從斷點繼續。")
                else:
                    sm.clear_checkpoint()
                    print("🛑 Pipeline 已停止（不儲存進度）。")
                break

            # Reload state mgr references
            sm = StateManager(base_dir)
            print_status_dashboard(sm)

            if args.interactive and p_num < 5:
                if sys.stdin.isatty():
                    print(f"✋ Phase {p_num} 已完成。請按 [Enter] 繼續...")
                    input()

    except SystemExit:
        pass
    except Exception as e:
        print(f"💥 未預期錯誤: {e}")

    # 正常完成後清除 checkpoint
    if not any(p.stop_requested for p in phases.values()):
        sm.clear_checkpoint()

    print("🏁 Pipeline 執行完畢。")
    try:
        import subprocess
        subprocess.run(
            ['osascript', '-e', 'display notification "V7.0 Pipeline 執行完畢" with title "Open-Claw"'],
            check=False
        )
    except Exception:
        pass

if __name__ == "__main__":
    main()
