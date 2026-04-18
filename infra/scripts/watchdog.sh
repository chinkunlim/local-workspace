#!/bin/bash

# --- 基礎設定 ---
WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export WORKSPACE_DIR
export PYTHONPATH="${WORKSPACE_DIR}:${WORKSPACE_DIR}/open-claw-workspace:${PYTHONPATH}"

LOG_DIR="${WORKSPACE_DIR}/logs"
mkdir -p "$LOG_DIR"
LOG="${LOG_DIR}/ram_watchdog.log" # 統一收納至 logs 目錄

exec >> "$LOG" 2>&1

CRITICAL_MB=1500
WARNING_MB=2500

# 攔截停止信號優雅退出
trap 'echo "[$(date +'\''%H:%M:%S'\'')] 🛑 Watchdog stopped."; exit 0' SIGINT SIGTERM

log() { 
    echo "[$(date +'%H:%M:%S')] $1"
}

# 獲取 Mac 可用記憶體：Free + Inactive + Speculative (更符合活動監視器指標)
get_free_mb() {
    vm_stat | awk '
        /Pages free/ {sub(/\./, "", $3); f=$3}
        /Pages inactive/ {sub(/\./, "", $3); i=$3}
        /Pages speculative/ {sub(/\./, "", $3); s=$3}
        END {printf "%.0f\n", (f+i+s)*4096/1048576}'
}

# 獲取所有執行中的 Ollama 模型列表 (支援多重卸載)
get_models() { 
    ollama ps 2>/dev/null | awk 'NR>1 {print $1}'
}

# 卸載模型以釋放顯存/記憶體
evict() { 
    local model_name="$1"
    local free_ram="$2"
    log "⚠️ EVICTING $model_name — Only ${free_ram}MB RAM free"
    
    # 優先使用官方原生指令 ollama stop，若太舊版則 fallback 到 API 調用
    if ollama stop "$model_name" >/dev/null 2>&1; then
        log "✅ Unloaded $model_name via CLI"
    else
        curl -s -X POST http://localhost:11434/api/generate -d "{\"model\":\"$model_name\",\"keep_alive\":0}" >/dev/null
        log "✅ Unloaded $model_name via API fallback"
    fi
}

log "🚀 RAM Watchdog started. DANGER: ${CRITICAL_MB}MB | WARN: ${WARNING_MB}MB"

while true; do
    F=$(get_free_mb)
    
    # 記憶體過低 -> 尋找並卸載 Ollama 佔用
    if [ "$F" -lt "$CRITICAL_MB" ]; then
        MODELS=$(get_models)
        if [ -n "$MODELS" ]; then
            # 遍歷所有執行中模型強制卸載
            for M in $MODELS; do
                evict "$M" "$F"
            done
        else
            log "🆘 CRITICAL ${F}MB — No Ollama models running. Check Chrome/Other apps!"
        fi
    
    # 觸發警告線
    elif [ "$F" -lt "$WARNING_MB" ]; then 
        log "⚠️ Low RAM Warning: ${F}MB free."
    fi
    
    sleep 30
done
