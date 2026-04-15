"""
Open WebUI Pipeline: Gemini Cost Guard (API 額度守衛)

功能說明：
自動追蹤並限制每日 Gemini API 的呼叫次數（針對免費層次 API 限制設計）。
當日使用次數達到設定的上限（預設 270 次）時，若使用者再次請求 Gemini 模型，
系統將攔截請求並自動轉發給本地的替換模型（預設為 qwen-coder），
避免產生非預期的 API 收費或觸發 429 Too Many Requests 錯誤。

資料存儲：
配額使用紀錄將以 JSON 格式，統一儲存於工作區目錄下。
"""

import json
import datetime
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field

class Pipeline:
    """
    核心管線類別。
    注意：Open WebUI 強制要求主類別必須命名為 'Pipeline'。
    """
    class Valves(BaseModel):
        daily_limit: int = Field(default=270, description='每日 Gemini API 請求上限')
        fallback_model: str = Field(default='qwen-coder', description='額度用盡時的替換模型')
        quota_file: str = Field(
            default=str(Path.home() / 'Desktop/local-workspace/gemini_quota.json'),
            description='配額追蹤 JSON 檔案路徑'
        )

    def __init__(self):
        self.valves: self.Valves = self.Valves()
        self.name = 'Gemini Cost Guard'

    def _get_count(self) -> int:
        """讀取當日的 API 使用次數，若跨日或檔案不存在則回傳 0"""
        today = datetime.date.today().isoformat()
        path = Path(self.valves.quota_file)
        try:
            if not path.exists(): 
                return 0
            data = json.loads(path.read_text())
            return data['count'] if data.get('date') == today else 0
        except Exception:
            return 0

    def _add_count(self):
        """將當日的使用次數 +1 並寫入 JSON 檔案"""
        count = self._get_count() + 1
        path = Path(self.valves.quota_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({'date': datetime.date.today().isoformat(), 'count': count}))

    def inlet(self, body: dict, user: Optional[dict] = None) -> dict:
        if 'gemini' in body.get('model', '').lower():
            current_count = self._get_count()
            
            if current_count >= self.valves.daily_limit:
                body['model'] = self.valves.fallback_model
                body['cost_guard_triggered'] = f'Quota reached ({current_count}) — Switched to local'
            else:
                self._add_count()
                
        return body
