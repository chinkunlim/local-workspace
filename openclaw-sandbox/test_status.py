import json
import os

from core.state.state_manager import StateManager

sm = StateManager("data/smart_highlighter", "smart_highlighter")
print(sm.get_dashboard_text())
