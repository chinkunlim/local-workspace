# -*- coding: utf-8 -*-
import sys, os
# Add scripts directory to sys.path so 'core' can be imported when running standalone
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import os, signal, psutil, logging, hashlib, glob, time, sys
from datetime import datetime

# --- 0. 強制設定系統時區為台灣時間 (Asia/Taipei) ---
os.environ['TZ'] = 'Asia/Taipei'
if hasattr(time, 'tzset'):
    time.tzset()

# --- 全局路徑設定 ---
SKILL_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
# 預設指向 open-claw-workspace 目錄 (向外推四層: utils -> scripts -> voice-memo -> skills -> workspace)
DEFAULT_WORKSPACE = os.path.abspath(os.path.join(SKILL_SCRIPTS_DIR, "../../../.."))
WORKSPACE_ROOT = os.environ.get("WORKSPACE_DIR", DEFAULT_WORKSPACE)

BASE_DIR = os.path.join(WORKSPACE_ROOT, "data", "voice-memo")
RAW_DATA_DIR = os.path.join(BASE_DIR, "raw_data")
TRANSCRIPT_DIR = os.path.join(BASE_DIR, "transcript")
PROOFREAD_DIR = os.path.join(BASE_DIR, "proofread")
NOTION_DIR = os.path.join(BASE_DIR, "notion_synthesis")
LOG_FILE = os.path.join(BASE_DIR, "system.log")
PROMPT_FILE = os.path.join(SKILL_SCRIPTS_DIR, "..", "prompt.md")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
GLOBAL_CHECKLIST = os.path.join(BASE_DIR, "checklist.md")
OLLAMA_API = "http://host.docker.internal:11434/api/generate"

# --- 1. 統一日誌系統 ---
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    encoding='utf-8'
)

def log_msg(msg, level="info"):
    print(msg)
    if level == "info": logging.info(msg)
    elif level == "warn": logging.warning(msg)
    elif level == "error": logging.error(msg, exc_info=(level == "error"))

# --- 2. 雙層中斷與全方位資源防禦 ---
stop_requested = False

def handle_interrupt(signum, frame):
    global stop_requested
    if stop_requested:
        # 連續兩次中斷 -> Force Close
        log_msg("\n🚨 [緊急中斷] 偵測到連續兩次中斷指令，執行強制停機 (Force Close)！", "error")
        os._exit(1) # 強制終止
    else:
        # 單次中斷 -> 優雅停機
        log_msg("\n🛑 收到中斷指令 (SIGINT)，將在處理完當前檔案後優雅停機... (再按一次強制退出)", "warn")
        stop_requested = True

signal.signal(signal.SIGINT, handle_interrupt)

def check_system_health(warning_mb=4000, critical_mb=2048, warning_temp=85, critical_temp=95):
    """整合 RAM, CPU, 溫度, 電量, 磁碟監控"""
    global stop_requested
    
    available_ram = psutil.virtual_memory().available / (1024 * 1024)
    cpu_usage = psutil.cpu_percent(interval=0.1)
    disk_free = psutil.disk_usage(BASE_DIR).free / (1024 * 1024)
    
    battery = psutil.sensors_battery()
    bat_percent = battery.percent if battery else 100
    power_plugged = battery.power_plugged if battery else True

    current_temp = None
    if hasattr(psutil, "sensors_temperatures"):
        temps = psutil.sensors_temperatures()
        if temps:
            core_temps = [e.current for name, es in temps.items() for e in es]
            if core_temps: current_temp = max(core_temps)

    # === 🚨 紅燈：極限崩潰防禦 (Force Close) ===
    if available_ram < critical_mb:
        log_msg(f"💥 [RAM 耗盡] 可用僅 {available_ram:.0f}MB！強制停機！", "error")
        os._exit(1)
    elif disk_free < 200:
        log_msg(f"💾 [空間耗盡] 磁碟空間剩餘 {disk_free:.0f}MB！強制停機！", "error")
        os._exit(1)
    elif not power_plugged and bat_percent < 5:
        log_msg(f"🪫 [電力極低] 電量僅 {bat_percent}% 且未充電！強制停機！", "error")
        os._exit(1)
    elif current_temp and current_temp >= critical_temp:
        log_msg(f"🔥 [高溫危險] 溫度 {current_temp}°C！強制停機！", "error")
        os._exit(1)

    # === 🟡 黃燈：優雅預警 (Graceful Shutdown) ===
    elif available_ram < warning_mb or (not power_plugged and bat_percent < 15):
        if not stop_requested:
            reason = "RAM 偏低" if available_ram < warning_mb else "電力不足"
            log_msg(f"🚨 [資源預警] 偵測到 {reason}，啟動優雅停機...", "warn")
            stop_requested = True
    elif current_temp and current_temp >= warning_temp:
        if not stop_requested:
            log_msg(f"🌡️ [高溫預警] 溫度 {current_temp}°C，啟動優雅停機...", "warn")
            stop_requested = True
    elif current_temp is None and cpu_usage >= 98:
        # Docker 盲測保護
        if not stop_requested:
            log_msg(f"⚙️ [CPU 滿載] 負載 {cpu_usage}% (溫度未知)。啟動優雅停機...", "warn")
            stop_requested = True

    return stop_requested

# --- 3. 配置讀取與互動 ---
def get_prompt_from_md(section_title):
    """從 prompt.md 解析特定段落指令"""
    if not os.path.exists(PROMPT_FILE):
        return "請校對以下內容："
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    prompt_lines = []
    capture = False
    for line in lines:
        if line.startswith(f"## {section_title}"):
            capture = True
            continue
        elif line.startswith("## Phase ") and capture:
            break
            
        if capture:
            prompt_lines.append(line)
            
    return "".join(prompt_lines).strip()

def ask_reprocess(subject, filename, phase_key):
    """交互詢問是否重新處理已標記為 ✅ 的項目"""
    dir_map = {
        "P1": TRANSCRIPT_DIR,
        "P2": PROOFREAD_DIR,
        "P3": NOTION_DIR
    }
    
    if phase_key in dir_map:
        base_name = os.path.splitext(filename)[0]
        ext = ".md"
        # 計算實際目標檔案目錄與名稱
        target_dir = dir_map[phase_key]
        target_path = os.path.join(target_dir, subject, f"{base_name}{ext}")
        # 取專案目錄的相對路徑顯示，如 "notion_synthesis/生理心理學/lecture_06.md"
        display_path = os.path.relpath(target_path, BASE_DIR)
    else:
        display_path = f"[{subject}] {filename}"

    print(f"\n❓ 偵測到 {display_path} 已完成 {phase_key}。")
    choice = input(f"   是否重新處理並覆寫？(y/N): ").strip().lower()
    return choice == 'y'

import json
def get_model_config(phase_name):
    """從 config.json 讀取指定階段的模型與參數設定"""
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        try:
            config_data = json.load(f)
        except json.JSONDecodeError:
            log_msg("❌ config.json 格式錯誤", "error")
            return {}
            
    phase_config = config_data.get(phase_name.lower().replace(" ", ""), {})
    active_profile = phase_config.get("active_profile", "default")
    return phase_config.get("profiles", {}).get(active_profile, {})

import requests
def call_ollama(model, prompt, options=None):
    """封裝對 Ollama 的呼叫，增加 Timeout 機制與錯誤重試 (Retry)"""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    if options:
        payload["options"] = options
        
    retries = 3
    for attempt in range(retries):
        try:
            res = requests.post(OLLAMA_API, json=payload, timeout=600)  # 10 minutes timeout for heavy inference
            res.raise_for_status()
            return res.json().get('response', '')
        except requests.exceptions.RequestException as e:
            if attempt < retries - 1:
                log_msg(f"⚠️ Ollama 請求失敗 ({e})，正在進行第 {attempt + 2} 次重試...", "warn")
                time.sleep(5)
            else:
                log_msg(f"❌ Ollama 請求徹底失敗: {e}", "error")
                raise

def should_process_task(task, current_phase_key, previous_phase_key=None, force=False):
    """
    判斷任務是否該在此階段被處理：
    1. 檢查前一階段是否完成。
    2. 檢查本階段是否已完成，若完成則依據 force 或互動詢問決定是否重新處理。
    回傳：True (須處理) 或 False (跳過)
    """
    if previous_phase_key and task["status"].get(previous_phase_key) != "✅":
        return False
        
    if task["status"].get(current_phase_key) == "✅":
        if force:
            return True
        else:
            return ask_reprocess(task["subject"], task["filename"], current_phase_key.upper())
    return True

def get_target_path(base_dir, subj, fname, new_ext=".md"):
    """統一檔名轉換邏輯"""
    base_name = os.path.splitext(fname)[0]
    return os.path.join(base_dir, subj, f"{base_name}{new_ext}")

# --- 4. 稽核與同步邏輯 ---
def get_file_hash(filepath):
    if not os.path.exists(filepath): return ""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for block in iter(lambda: f.read(4096), b""):
            sha256.update(block)
    return sha256.hexdigest()

def get_global_checklist_data():
    """解析全域 checklist.md"""
    all_data = {}
    if not os.path.exists(GLOBAL_CHECKLIST):
        return all_data
        
    current_subj = None
    with open(GLOBAL_CHECKLIST, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("## "):
                current_subj = line[3:].strip()
                all_data[current_subj] = {}
            elif current_subj and "|" in line and "檔案名稱" not in line and "---" not in line:
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 8:
                    all_data[current_subj][parts[1]] = {
                        "p1": parts[2], "p2": parts[3], "p3": parts[4],
                        "hash": parts[5], "date": parts[6], "note": parts[7]
                    }
    return all_data

def write_global_checklist_data(all_data):
    """將 all_data 寫回全域 checklist.md"""
    with open(GLOBAL_CHECKLIST, "w", encoding="utf-8") as f:
        f.write("# 學習進度 (總表)\n\n")
        f.write("> 本檔案由系統自動維護，請勿手動修改 hash 等欄位\n\n")
        for subj in sorted(all_data.keys()):
            f.write(f"## {subj}\n\n")
            f.write("| 檔案名稱 | P1 (轉錄) | P2 (校對) | P3 (Notion) | SHA-256 指紋 | 最後修改日期 | 備註 |\n")
            f.write("| :--- | :---: | :---: | :---: | :--- | :--- | :--- |\n")
            for fname in sorted(all_data[subj].keys()):
                v = all_data[subj][fname]
                f.write(f"| {fname} | {v['p1']} | {v['p2']} | {v['p3']} | {v['hash']} | {v['date']} | {v['note']} |\n")
            f.write("\n")

def sync_all_checklists():
    """掃描所有實體檔案並與全域 checklist 基準比對"""
    all_data = get_global_checklist_data()
    
    if not os.path.exists(RAW_DATA_DIR): return all_data
    subjects = [d for d in os.listdir(RAW_DATA_DIR) if os.path.isdir(os.path.join(RAW_DATA_DIR, d))]
    
    for subj in subjects:
        if subj not in all_data:
            all_data[subj] = {}
            
        subj_audio = os.path.join(RAW_DATA_DIR, subj)
        for d in [TRANSCRIPT_DIR, PROOFREAD_DIR, NOTION_DIR]:
            os.makedirs(os.path.join(d, subj), exist_ok=True)
            
        physical_files = glob.glob(os.path.join(subj_audio, "*.m4a"))
        for pf in physical_files:
            fname = os.path.basename(pf)
            fhash = get_file_hash(pf)
            mtime = datetime.fromtimestamp(os.path.getmtime(pf)).strftime('%Y-%m-%d')
            
            if fname in all_data[subj] and all_data[subj][fname]["hash"] == fhash:
                continue
            all_data[subj][fname] = {"p1": "⏳", "p2": "⏳", "p3": "⏳", "hash": fhash, "date": mtime, "note": "更新/新增"}
                
    write_global_checklist_data(all_data)
    return all_data

def get_all_tasks():
    """獲取所有任務清單"""
    all_data = sync_all_checklists()
    tasks = []
    for subj, records in all_data.items():
        for fname, data in records.items():
            tasks.append({"subject": subj, "filename": fname, "status": data})
    return tasks

def update_task_status(subject, filename, phase_key, status="✅"):
    """確實更新狀態並寫入全域檔案"""
    all_data = get_global_checklist_data()
    if subject in all_data and filename in all_data[subject]:
        all_data[subject][filename][phase_key] = status
        write_global_checklist_data(all_data)
        log_msg(f"✅ 狀態已寫入：[{subject}] {filename} 的 {phase_key} 標記為 {status}")
