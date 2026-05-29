import os
import re
import shutil

src_dir = "data/smart_highlighter/input"
dst_dir = "data/audio_transcriber/output/03_merged"

print("開始復原 audio_transcriber 合併輸出...")

restored_count = 0
for subj in os.listdir(src_dir):
    subj_dir = os.path.join(src_dir, subj)
    if not os.path.isdir(subj_dir) or subj == "Default":
        continue
    for fname in os.listdir(subj_dir):
        if not fname.endswith(".md"):
            continue
        src_path = os.path.join(subj_dir, fname)
        dst_subj_dir = os.path.join(dst_dir, subj)
        os.makedirs(dst_subj_dir, exist_ok=True)
        dst_path = os.path.join(dst_subj_dir, fname)

        with open(src_path, encoding="utf-8") as f:
            content = f.read()

        match = re.search(r"<Original>\n?(.*?)\n?</Original>", content, flags=re.DOTALL)
        if match:
            with open(dst_path, "w", encoding="utf-8") as f:
                f.write(match.group(1).strip())
            restored_count += 1
            print(f"✅ 已還原: {subj}/{fname}")
        else:
            print(f"⚠️ 警告: 找不到 <Original> 區塊於 {src_path}")

print(f"\n共成功還原 {restored_count} 份 audio_transcriber 輸出檔案！")

print("\n開始清理後續管線的污染檔案...")
for d in ["data/smart_highlighter/input", "data/proofreader/output"]:
    if os.path.exists(d):
        for root, dirs, files in os.walk(d, topdown=False):
            for name in files:
                if name != ".DS_Store" and name != "dummy.md":
                    os.remove(os.path.join(root, name))
        print(f"🧹 已淨空 {d}")

print("\n🎉 系統狀態已成功還原為乾淨的原始狀態！")
