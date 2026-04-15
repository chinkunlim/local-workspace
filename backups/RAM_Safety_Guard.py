"""
Open WebUI Pipeline: RAM Safety Guard (記憶體安全守衛)

功能說明：
在每次發送對話請求前，自動檢查 Mac 的可用實體記憶體 (RAM)。
如果可用 RAM 低於設定的警戒值，且使用者選擇了高耗能的「重型模型」（如 14b, 32b, 70b 等），
系統將自動攔截該請求，並強制替換為輕量級的安全模型（預設為 qwen-coder），
以防止系統因 Swap 過高而卡死。

環境依賴：
- 需在 pipelines 的虛擬環境中安裝 psutil (uv pip install psutil)
"""

import psutil
from typing import Optional
from pydantic import BaseModel, Field

class Pipeline:
    """
    核心管線類別。
    注意：Open WebUI 強制要求主類別必須命名為 'Pipeline'，不可使用 'Filter'。
    """
    class Valves(BaseModel):
        ram_threshold_mb: int = Field(default=3000, description='低記憶體警戒值 (MB)')
        safety_model: str = Field(default='qwen-coder', description='觸發警戒時的替換模型')

    def __init__(self):
        self.valves: self.Valves = self.Valves()
        self.name = 'RAM Safety Guard'

    def inlet(self, body: dict, user: Optional[dict] = None) -> dict:
        free_mb = psutil.virtual_memory().available / 1024 / 1024
        model = body.get('model', '').lower()
        HEAVY_KEYWORDS = ['deepseek-v3', 'deepseek-r1', '14b', '32b', '70b', 'gemma3:12b', 'phi-4']
        
        is_heavy = any(kw in model for kw in HEAVY_KEYWORDS)
        
        if free_mb < self.valves.ram_threshold_mb and is_heavy:
            body['model'] = self.valves.safety_model
            body['ram_guard_triggered'] = f'Switched: only {free_mb:.0f}MB free'
            
        return body
