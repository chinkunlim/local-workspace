import os


def mass_replace(directory):
    replacements = [
        ("audio_transcriber", "audio_transcriber"),
        ("Audio Transcriber", "Audio Transcriber"),
        ("doc_parser", "doc_parser"),
        ("Doc Parser", "Doc Parser"),
        ("audio_transcriber", "audio_transcriber"),
        ("doc_parser", "doc_parser"),
        ("Audio-Transcriber", "Audio-Transcriber"),
        ("Doc-Parser", "Doc-Parser"),
    ]

    exclude_dirs = {".git", "models", "logs", "__pycache__", "data", "vector_db", "node_modules"}

    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for file in files:
            if file.endswith((".py", ".md", ".yaml", ".json", ".html", ".sh", ".txt")):
                path = os.path.join(root, file)
                try:
                    with open(path, encoding="utf-8") as f:
                        content = f.read()

                    new_content = content
                    for old, new in replacements:
                        new_content = new_content.replace(old, new)

                    if new_content != content:
                        with open(path, "w", encoding="utf-8") as f:
                            f.write(new_content)
                        print(f"Updated {path}")
                except Exception as e:
                    print(f"Error processing {path}: {e}")


if __name__ == "__main__":
    mass_replace("/Users/limchinkun/Desktop/local-workspace/open-claw-sandbox")
