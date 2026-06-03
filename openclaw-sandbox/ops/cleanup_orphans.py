#!/usr/bin/env python3
import json
import os
import shutil
import sys

# Ensure core can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.state.global_registry import GlobalRegistry


def cleanup_skill(skill_name: str, input_dir: str):
    state_file = f"data/{skill_name}/state/.pipeline_state.json"
    output_base = f"data/{skill_name}/output"

    if not os.path.exists(state_file):
        return

    with open(state_file) as f:
        state = json.load(f)

    registry = GlobalRegistry(os.getcwd())
    registry_data = registry._load()

    orphans_to_delete = []
    cleaned_count = 0

    # Identify orphans
    for subj in list(state.keys()):
        if subj == "_checkpoint":
            continue

        subj_input_dir = os.path.join(input_dir, subj)
        physical_files = []
        if os.path.exists(subj_input_dir):
            physical_files = os.listdir(subj_input_dir)

        for fname in list(state[subj].keys()):
            if fname not in physical_files:
                orphans_to_delete.append((subj, fname))

    if not orphans_to_delete:
        print(f"ℹ️  {skill_name} 沒有發現孤立的檔案。")
        return

    print(f"\n⚠️  發現 {len(orphans_to_delete)} 個孤立的 {skill_name} 檔案與記錄:")
    for subj, fname in orphans_to_delete:
        print(f"   - {subj} / {fname}")

    ans = input("\n❓ 確定要全部清除嗎？(y/N): ")
    if ans.lower() != "y":
        print("⏭️  已取消清理。")
        return

    for subj, fname in orphans_to_delete:
        # Determine prefix
        prefix = os.path.splitext(fname)[0]

        # 1. Delete from Output directories
        if os.path.exists(output_base):
            for phase_dir in os.listdir(output_base):
                phase_path = os.path.join(output_base, phase_dir, subj)
                if not os.path.exists(phase_path):
                    continue

                # Delete folders matching prefix (like doc_parser does)
                folder_path = os.path.join(phase_path, prefix)
                if os.path.isdir(folder_path):
                    shutil.rmtree(folder_path)
                    print(f"   Deleted Dir: {folder_path}")

                # Delete exact files matching prefix
                for out_f in os.listdir(phase_path):
                    if out_f.startswith(prefix) and os.path.isfile(os.path.join(phase_path, out_f)):
                        os.remove(os.path.join(phase_path, out_f))
                        print(f"   Deleted File: {os.path.join(phase_path, out_f)}")

        # 2. Remove from GlobalRegistry
        if subj in registry_data and prefix in registry_data[subj]:
            if skill_name in registry_data[subj][prefix]:
                del registry_data[subj][prefix][skill_name]
                if not registry_data[subj][prefix]:
                    del registry_data[subj][prefix]
                print("   Deleted from GlobalRegistry")

        # 3. Remove from State
        del state[subj][fname]
        cleaned_count += 1

    # Clean empty subjects
    for subj in list(state.keys()):
        if subj != "_checkpoint" and not state[subj]:
            del state[subj]

    # Save back
    if cleaned_count > 0:
        with open(state_file, "w") as f:
            json.dump(state, f, indent=4, ensure_ascii=False)
        registry._memory_cache = registry_data
        registry._save()
        print(f"✅ {skill_name} 清理完成！共刪除 {cleaned_count} 個無效記錄及其輸出檔。")


if __name__ == "__main__":
    print("🧹 開始執行 Garbage Collection ...")
    cleanup_skill("doc_parser", "data/doc_parser/input")
    cleanup_skill("audio_transcriber", "data/audio_transcriber/input")
    # proofreader reads from audio_transcriber output usually, or its own state.
    # For now, targeting the input-driven skills.
    cleanup_skill("proofreader", "data/audio_transcriber/output/03_merged")
    print("\n🎉 全部清理完畢！")
