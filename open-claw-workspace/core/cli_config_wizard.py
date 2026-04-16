# -*- coding: utf-8 -*-
"""
cli_config_wizard.py — Open Claw Universal Config Wizard
========================================================
Interactive terminal wizard to select active AI profiles for any skill.
Reads from and writes to the target skill's `config.json` or `config.yaml`.
"""

import os
import sys
import json
import argparse

from core.bootstrap import ensure_core_path as _bootstrap
_bootstrap(__file__)

_workspace_root = os.environ.get(
    "WORKSPACE_DIR",
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from core.path_builder import PathBuilder

def load_config(config_file):
    if not os.path.exists(config_file):
        print(f"❌ 找不到設定檔：{config_file}")
        sys.exit(1)
    
    ext = os.path.splitext(config_file)[1].lower()
    if ext == ".yaml" or ext == ".yml":
        try:
            import yaml
            with open(config_file, "r", encoding="utf-8") as f:
                return yaml.safe_load(f), "yaml"
        except ImportError:
            print("❌ 缺少 PyYAML, 請執行 pip install pyyaml")
            sys.exit(1)
    else:
        with open(config_file, "r", encoding="utf-8") as f:
            return json.load(f), "json"

def save_config(config_file, config_data, format_type):
    if format_type == "yaml":
        import yaml
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f, allow_unicode=True, sort_keys=False)
    else:
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
    print(f"✅ 設定已成功儲存至 {config_file}！")

def prompt_choice(phase_key, profiles, current_active):
    print(f"\n{'-'*50}")
    print(f"⚙️  {phase_key.upper()} 模型/組態設定")
    print(f"{'-'*50}")
    options = list(profiles.keys())
    
    for i, p in enumerate(options, 1):
        note = profiles[p].get("_note", "") if isinstance(profiles[p], dict) else ""
        marker = "✨(目前設定)" if p == current_active else ""
        print(f"[{i}] {p} {marker}")
        if note:
            print(f"    └─ {note}")
            
    while True:
        try:
            choice = input(f"\n👉 請輸入欲使用的組態編號 (直接按 Enter 保留目前設定 [{current_active}]): ").strip()
            if not choice:
                return current_active
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                return options[idx]
            print("⚠️ 無效的選項，請重新輸入。")
        except ValueError:
            print("⚠️ 請輸入數字。")

def main():
    parser = argparse.ArgumentParser(description="Open Claw CLI Config Wizard")
    parser.add_argument("--skill", required=True, help="Target skill name (e.g. voice-memo, pdf-knowledge)")
    args = parser.parse_args()
    
    skill = args.skill
    print("=" * 60)
    print(f"  ✨ Open Claw 快速設定精靈 [{skill}] ✨")
    print("=" * 60)
    print("本精靈將協助您選擇每個階段要使用的 AI 模型與相關參數。")
    print("設定結果將會自動寫入該 Skill 的 config 檔案中。")
    
    pb = PathBuilder(_workspace_root, skill)
    # Prefer config.yaml over config.json
    yaml_config = os.path.join(pb.config_dir, "config.yaml")
    json_config = os.path.join(pb.canonical_dirs.get("input", pb.base_dir), "config.json") # fallback for older voice memo
    fallback_json = os.path.join(pb.base_dir, "config.json")
    
    config_file = None
    if os.path.exists(yaml_config):
        config_file = yaml_config
    elif os.path.exists(json_config):
        config_file = json_config
    elif os.path.exists(fallback_json):
        config_file = fallback_json
    else:
        print(f"❌ 找不到 {skill} 的任何設定檔。")
        sys.exit(1)
        
    config_data, fmt = load_config(config_file)
    
    # We heuristically find keys that have "profiles" and "active_profile" inside them
    changed = False
    for k, v in config_data.items():
        if isinstance(v, dict) and "profiles" in v:
            profiles = v.get("profiles", {})
            if not profiles: continue
            
            current = v.get("active_profile", "default")
            new_active = prompt_choice(k, profiles, current)
            if new_active != current:
                config_data[k]["active_profile"] = new_active
                changed = True
                
    if changed:
        print("\n" + "=" * 60)
        save_config(config_file, config_data, fmt)
    else:
        print("\n✅ 沒有變更任何設定。")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 設定精靈已取消。未儲存任何變更。")
        sys.exit(0)
