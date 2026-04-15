# -*- coding: utf-8 -*-
import sys, os
# Add scripts directory to sys.path so 'core' can be imported when running standalone
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import json
import os
import sys

# 預期路徑：跟其他 scripts 同目錄，config.json 在其上一層
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_FILE = os.path.join(SKILL_DIR, "..", "..", "data", "voice-memo", "config.json")

def load_config():
    if not os.path.exists(CONFIG_FILE):
        print(f"❌ 找不到 config.json。預期路徑：{CONFIG_FILE}")
        sys.exit(1)
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    print("✅ 設定已成功儲存！您現在可以使用 `python3 run_all.py` 來執行 Pipeline。")

def prompt_choice(phase_key, profiles, current_active):
    print(f"\n{'-'*50}")
    print(f"⚙️  {phase_key.upper()} 模型設定")
    print(f"{'-'*50}")
    options = list(profiles.keys())
    
    for i, p in enumerate(options, 1):
        note = profiles[p].get("_note", "")
        # highlight current active
        marker = "✨(目前設定)" if p == current_active else ""
        print(f"[{i}] {p} {marker}")
        if note:
            # 讓備註稍微縮排
            print(f"    └─ {note}")
            
    while True:
        try:
            choice = input(f"\n👉 請輸入欲使用的模型編號 (直接按 Enter 保留目前設定 [{current_active}]): ").strip()
            if not choice:
                return current_active
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                return options[idx]
            print("⚠️ 無效的選項，請重新輸入。")
        except ValueError:
            print("⚠️ 請輸入數字。")

def main():
    print("=" * 60)
    print("  ✨ Open-Claw Voice-Memo Pipeline 快速設定精靈 ✨")
    print("=" * 60)
    print("本精靈將協助您選擇每個階段要使用的 AI 模型與相關參數。")
    print("設定結果將會自動寫入 config.json 中。")
    
    config = load_config()
    
    for phase in ["phase0", "phase1", "phase2", "phase3", "phase4", "phase5"]:
        if phase not in config:
            continue
            
        phase_config = config[phase]
        profiles = phase_config.get("profiles", {})
        if not profiles:
            continue
            
        current = phase_config.get("active_profile", "default")
        new_active = prompt_choice(phase, profiles, current)
        config[phase]["active_profile"] = new_active

    print("\n" + "=" * 60)
    save_config(config)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 設定精靈已取消。未儲存任何變更。")
        sys.exit(0)
