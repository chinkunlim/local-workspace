import os
import re

count = 0
for root, dirs, files in os.walk("skills"):
    if "manifest.py" in files:
        path = os.path.join(root, "manifest.py")
        with open(path, encoding="utf-8") as f:
            content = f.read()

        # Regex to remove phases=... up to the closing bracket and comma
        new_content = re.sub(r"\s*phases=\[.*?\],", "", content, flags=re.DOTALL)

        if new_content != content:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)
            count += 1
            print(f"Fixed {path}")

print(f"Total fixed: {count}")
