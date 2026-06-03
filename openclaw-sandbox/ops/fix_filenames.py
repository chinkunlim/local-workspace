#!/usr/bin/env python3
import os
import re


def fix_filenames():
    base_dirs = ["inbox", "data/doc_parser/input", "data/audio_transcriber/input"]
    count = 0

    for base_dir in base_dirs:
        if not os.path.exists(base_dir):
            continue

        for root, _, files in os.walk(base_dir):
            for f in files:
                # Regex matches e.g. "L13 Myths about suicide 2026.pdf" -> "L13 "
                if re.match(r"^L\d{2} ", f):
                    new_name = f[:3] + "_" + f[4:]
                    old_path = os.path.join(root, f)
                    new_path = os.path.join(root, new_name)
                    os.rename(old_path, new_path)
                    print(f"✅ Renamed: {f} -> {new_name}")
                    count += 1

    print(f"\n🎉 檔名修復完成！共修正了 {count} 個檔案。")


if __name__ == "__main__":
    print("🔍 掃描缺少底線 '_' 的檔案...")
    fix_filenames()
