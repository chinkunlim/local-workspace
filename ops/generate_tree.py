import os
from pathlib import Path

def generate_tree(dir_path: Path, prefix: str = ""):
    """
    遞迴生成目錄的樹狀結構，並自動過濾龐大的環境資料夾。
    """
    # 🚫 黑名單：這些資料夾會被忽略，確保輸出乾淨
    IGNORE_DIRS = {
        '.git', '.venv', 'venv', 'node_modules', '__pycache__', 
        '.DS_Store', 'data', '.open-webui'
    }
    
    # 過濾不需要的隱藏檔或快取檔
    IGNORE_FILES = {'.DS_Store'}

    if not dir_path.exists() or not dir_path.is_dir():
        print(f"❌ 錯誤：找不到目錄 {dir_path}")
        return

    # 取得目錄內容，先列出資料夾，再列出檔案，並按字母排序
    try:
        contents = list(dir_path.iterdir())
    except PermissionError:
        print(prefix + "└── [權限不足，無法讀取]")
        return

    contents.sort(key=lambda x: (not x.is_dir(), x.name.lower()))
    
    # 濾除黑名單
    contents = [
        c for c in contents 
        if c.name not in IGNORE_DIRS and c.name not in IGNORE_FILES
    ]

    # 設定樹狀分支的符號
    pointers = ["├── "] * (len(contents) - 1) + ["└── "] if contents else []
    
    for pointer, path_obj in zip(pointers, contents):
        print(prefix + pointer + path_obj.name)
        
        # 如果是資料夾，繼續往下遞迴
        if path_obj.is_dir():
            extension = "│   " if pointer == "├── " else "    "
            generate_tree(path_obj, prefix + extension)

if __name__ == "__main__":
    # 自動抓取你 Mac 上的 local-workspace 路徑
    workspace_path = Path(os.path.expanduser("~/Desktop/local-workspace"))
    
    print(f"\n📂 掃描目錄：{workspace_path}")
    print("=" * 50)
    print(workspace_path.name)
    generate_tree(workspace_path)
    print("=" * 50)
    print("✅ 掃描完成！\n")