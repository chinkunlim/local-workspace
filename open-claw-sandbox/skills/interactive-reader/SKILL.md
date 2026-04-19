---
name: interactive-reader
description: "Interactive AI Reader. Allows users to write commands like `> [AI: ...]` inside Markdown files to get AI-generated inline context."
metadata:
  {
    "openclaw":
      {
        "emoji": "📖"
      }
  }
---

# Interactive Reader (互動式閱讀助手)

**Open Claw Skill**

## 角色與定位
Interactive Reader 是一個協助你在 Markdown 筆記中「原地與 AI 協作」的工具。
它會掃描檔案中特定的 AI 指令標籤，擷取周圍上下文，呼叫大語言模型生成回答（如總結、心智圖、解釋），並將結果自動安全地追加到該標籤下方。

## 觸發方式
透過 CLI 單檔執行，或透過 WebUI 排程。
```bash
python scripts/run_all.py --file "你的筆記.md"
```

## 標籤語法
在 Markdown 筆記中插入以下標籤：
`> [AI: 請幫我解釋這段話的意思]`

處理完成後，系統會將其標記為已處理，防止重複執行：
`> [AI-DONE: 請幫我解釋這段話的意思]`
