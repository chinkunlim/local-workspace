"""
Phase 1: High-Precision Audio Transcription
Refactored to V8.1 — Anti-Hallucination Triple Defence

V8.1 Changes (vs V7.0):
- Layer 0: mlx-whisper native decoding params (condition_on_previous_text,
           compression_ratio_threshold, hallucination_silence_threshold, etc.)
- Layer 1: VAD pre-processing via pydub.silence (silence stripping before Whisper)
- Layer 2: Segment-level repetition detection (N-gram + zlib) + local retry
- Split output strategy: pure_text silent drop / ts_text HALLUCINATION_DETECTED marker
- All defence parameters driven by config.yaml phase1.anti_hallucination
"""

# Group 1 — stdlib
import os
import sys
import zlib

# Group 2 — Internal Core Bootstrap
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))
from core.utils.bootstrap import ensure_core_path as _bootstrap

_bootstrap(__file__)

# Group 3 — Core imports
from core import AtomicWriter, PipelineBase

# ---------------------------------------------------------------------------
# Layer 1: VAD Pre-processing
# ---------------------------------------------------------------------------


def vad_preprocess(
    audio_path: str,
    tmp_dir: str,
    min_silence_len_ms: int = 1500,
    silence_thresh_dbfs: int = -35,
    padding_ms: int = 300,
    max_removal_ratio: float = 0.90,
    log_fn=None,
) -> str:
    """
    使用 pydub.silence 切除長靜音，輸出乾淨的 16kHz mono WAV 供 Whisper 使用。

    Args:
        audio_path:         原始 .m4a 路徑
        tmp_dir:            暫存輸出目錄
        min_silence_len_ms: 超過此長度的靜音才切除（ms）
        silence_thresh_dbfs: 靜音判斷閾值 dBFS（有背景噪音用 -35，安靜室內用 -40）
        padding_ms:         切除靜音時前後保留的 buffer（ms）
        max_removal_ratio:  VAD 移除上限比例（超過此值代表閾值設太高、誤判語音，
                            自動 fallback 回原始音檔）
        log_fn:             日誌回呼函數（可選）

    Returns:
        cleaned_wav_path: 去靜音後的 .wav 絕對路徑；若全靜音、過度移除或套件未安裝則回傳原路徑
    """

    def _log(msg):
        if log_fn:
            log_fn(msg)

    try:
        from pydub import AudioSegment
        from pydub.silence import detect_nonsilent
    except ImportError:
        _log("⚠️  pydub 未安裝，跳過 VAD 前處理。請執行: pip install pydub")
        return audio_path

    try:
        audio = AudioSegment.from_file(audio_path)
    except Exception as e:
        _log(f"⚠️  pydub 無法解碼音檔（{e}），跳過 VAD 前處理。")
        return audio_path

    # 標準化為 16kHz mono（Whisper 最佳格式）
    audio = audio.set_channels(1).set_frame_rate(16000)

    nonsilent_ranges = detect_nonsilent(
        audio,
        min_silence_len=min_silence_len_ms,
        silence_thresh=silence_thresh_dbfs,
        seek_step=10,
    )

    if not nonsilent_ranges:
        _log("⚠️  VAD：偵測到全靜音音檔，跳過前處理。")
        return audio_path

    # 拼接非靜音片段（前後各加 padding 避免截頭去尾）
    chunks = []
    for start, end in nonsilent_ranges:
        padded_start = max(0, start - padding_ms)
        padded_end = min(len(audio), end + padding_ms)
        chunks.append(audio[padded_start:padded_end])

    cleaned_audio = sum(chunks)

    original_duration = len(audio) / 1000
    cleaned_duration = len(cleaned_audio) / 1000
    silence_ratio = 1.0 - (cleaned_duration / original_duration)

    # ── 安全閥：移除率超過上限，代表閾值過高誤判語音，fallback 回原始音檔 ──
    if silence_ratio > max_removal_ratio:
        _log(
            f"⚠️  VAD 移除率 {silence_ratio:.1%} 超過上限 {max_removal_ratio:.0%}，"
            f"閾值可能過高（誤判語音為靜音）— fallback 回原始音檔。"
        )
        return audio_path

    _log(
        f"🔇 VAD 前處理完成：移除 {silence_ratio:.1%} 靜音，"
        f"{original_duration:.1f}s → {cleaned_duration:.1f}s"
    )

    os.makedirs(tmp_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(audio_path))[0]
    cleaned_path = os.path.join(tmp_dir, f"{base_name}_vad.wav")
    cleaned_audio.export(cleaned_path, format="wav")

    return cleaned_path


# ---------------------------------------------------------------------------
# Layer 2a: Segment-level Repetition Detection
# ---------------------------------------------------------------------------


def detect_repetition(
    text: str,
    ngram_size: int = 4,
    repetition_threshold: float = 0.45,
    compress_ratio_threshold: float = 0.3,
) -> bool:
    """
    偵測 Segment 文字是否陷入幻覺迴圈。

    Strategy 1 — N-gram 重複率：
        所有 N-gram 中「重複 N-gram 佔比」超過 threshold → 幻覺

    Strategy 2 — zlib 壓縮比啟發式（來自 OpenAI 官方 heuristic）：
        zlib 壓縮後大小 / 原始大小 < compress_ratio_threshold → 高重複度 → 幻覺

    Args:
        text:                     segment 的純文字
        ngram_size:               N-gram 視窗大小（預設 4-gram）
        repetition_threshold:     N-gram 重複率閾值（超過即觸發）
        compress_ratio_threshold: zlib 壓縮比閾值（低於即觸發）

    Returns:
        True  → 偵測到幻覺迴圈，需要重試
        False → 正常文字
    """
    # Strategy 2: zlib 壓縮比
    encoded = text.encode("utf-8")
    if not encoded:  # ← guard: empty segment → not a hallucination loop
        return False
    compressed = zlib.compress(encoded)
    compress_ratio = len(compressed) / len(encoded)
    if compress_ratio < compress_ratio_threshold:
        return True

    words = list(text.strip()) if " " not in text.strip() else text.strip().split()

    # 過短文字不處理（至少需要 2 個完整的 N-gram）
    if len(words) < ngram_size * 2:
        return False

    # Strategy 1: N-gram 重複率
    ngrams = [tuple(words[i : i + ngram_size]) for i in range(len(words) - ngram_size + 1)]
    unique_ngrams = set(ngrams)
    repetition_ratio = 1.0 - (len(unique_ngrams) / len(ngrams))
    if repetition_ratio > repetition_threshold:
        return True

    return False


# ---------------------------------------------------------------------------
# Layer 2b: Local Segment Retry
# ---------------------------------------------------------------------------


def retry_segment(
    audio_path: str,
    start_sec: float,
    end_sec: float,
    tmp_dir: str,
    engine: str,
    model,
    model_name: str,
    retry_temperature: float = 0.2,
    ngram_size: int = 4,
    repetition_threshold: float = 0.45,
    compress_ratio_threshold: float = 0.3,
    log_fn=None,
) -> str | None:
    """
    針對幻覺 Segment，切割局部音軌，以嚴格參數重新轉錄。

    Args:
        audio_path:       原始（VAD 後）音檔路徑
        start_sec:        異常 Segment 開始時間（秒）
        end_sec:          異常 Segment 結束時間（秒）
        tmp_dir:          暫存目錄
        engine:           "mlx-whisper" 或 "faster-whisper"
        model:            已載入的 Whisper model 物件（faster-whisper 用）
        model_name:       model 名稱（mlx-whisper 用）
        retry_temperature: 重試時的 temperature
        log_fn:           日誌回呼函數（可選）

    Returns:
        str   → 重新轉錄的文字（乾淨）
        None  → 重試後仍異常，由呼叫端決定輸出策略
    """

    def _log(msg):
        if log_fn:
            log_fn(msg)

    try:
        from pydub import AudioSegment
    except ImportError:
        _log("⚠️  pydub 未安裝，無法執行局部重試。")
        return None

    BUFFER_MS = 200
    try:
        audio = AudioSegment.from_file(audio_path)
        start_ms = max(0, int(start_sec * 1000) - BUFFER_MS)
        end_ms = min(len(audio), int(end_sec * 1000) + BUFFER_MS)
        clip = audio[start_ms:end_ms]
    except Exception as e:
        _log(f"⚠️  無法切割局部音軌: {e}")
        return None

    os.makedirs(tmp_dir, exist_ok=True)
    clip_path = os.path.join(tmp_dir, f"retry_{int(start_sec)}_{int(end_sec)}.wav")

    try:
        clip.export(clip_path, format="wav")

        retry_text = ""
        if engine == "mlx-whisper":
            import mlx_whisper

            result = mlx_whisper.transcribe(
                clip_path,
                path_or_hf_repo=model_name,
                condition_on_previous_text=False,
                temperature=retry_temperature,
                verbose=False,
            )
            retry_text = " ".join(s["text"].strip() for s in result.get("segments", []))
        elif engine == "faster-whisper":
            if model is None:
                _log("⚠️  faster-whisper 模型未載入，無法重試。")
                return None
            segments_gen, _ = model.transcribe(
                clip_path,
                condition_on_previous_text=False,
                temperature=retry_temperature,
                vad_filter=True,
            )
            retry_text = " ".join(s.text.strip() for s in segments_gen)

        # 驗證重試結果
        if detect_repetition(
            retry_text, ngram_size, repetition_threshold, compress_ratio_threshold
        ):
            _log(f"⚠️  Segment [{start_sec:.1f}s-{end_sec:.1f}s] 重試後仍異常，標記失敗。")
            return None

        return retry_text.strip() if retry_text.strip() else None

    except Exception as e:
        _log(f"❌ Segment 重試失敗: {e}")
        return None
    finally:
        if os.path.exists(clip_path):
            try:
                os.remove(clip_path)
            except OSError:
                pass


# ---------------------------------------------------------------------------
# Language Detection (before VAD) — multi-clip majority vote
# ---------------------------------------------------------------------------


def detect_audio_language(
    audio_path: str,
    engine: str,
    model,
    model_name: str,
    clip_duration_sec: float = 30.0,
    log_fn=None,
) -> str | None:
    """
    對原始音檔的多個時間窗口做語言偵測，取多數投票結果。
    必須在 VAD 前執行，避免 VAD fallback 後靜音干擾語言判斷。

    策略：在全音檔中平均取 3 個不重疊片段（前/中/後段）分別偵測，
    防止前 30 秒靜音導致誤判。

    Args:
        audio_path:        原始音檔路徑（VAD 前）
        engine:            "mlx-whisper" 或 "faster-whisper"
        model:             已載入的 faster-whisper model（mlx-whisper 傳 None）
        model_name:        model 名稱（mlx-whisper 用）
        clip_duration_sec: 每個片段的長度（預設 30s）
        log_fn:            日誌回呼函數

    Returns:
        語言代碼字串（如 'zh'、'en'）或 None（偵測失敗）
    """
    from collections import Counter
    import tempfile

    def _log(msg):
        if log_fn:
            log_fn(msg)

    try:
        from pydub import AudioSegment

        audio = AudioSegment.from_file(audio_path)
        total_ms = len(audio)
        clip_ms = int(clip_duration_sec * 1000)
        NUM_CLIPS = 3
        starts = [max(0, int(total_ms * i / NUM_CLIPS)) for i in range(NUM_CLIPS)]
    except Exception as e:
        _log(f"⚠️  語言偵測前置處理失敗: {e}")
        return None

    votes = []
    tmp_paths = []

    try:
        for i, start_ms in enumerate(starts):
            end_ms = min(start_ms + clip_ms, total_ms)
            clip = audio[start_ms:end_ms].set_channels(1).set_frame_rate(16000)

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                tmp_path = f.name
            tmp_paths.append(tmp_path)
            clip.export(tmp_path, format="wav")

            try:
                lang = None
                if engine == "mlx-whisper":
                    import mlx_whisper

                    # 壓制子進程 stdout + stderr（mlx_whisper tqdm / macOS 雜訊）
                    with open(os.devnull, "w") as _dn:
                        _old_err = os.dup(2)
                        _old_out = os.dup(1)
                        os.dup2(_dn.fileno(), 2)
                        os.dup2(_dn.fileno(), 1)
                        try:
                            det = mlx_whisper.transcribe(
                                tmp_path,
                                path_or_hf_repo=model_name,
                                condition_on_previous_text=False,
                                verbose=False,
                            )
                        finally:
                            os.dup2(_old_err, 2)
                            os.dup2(_old_out, 1)
                            os.close(_old_err)
                            os.close(_old_out)
                    lang = det.get("language")
                elif engine == "faster-whisper" and model is not None:
                    lang_probs = model.detect_language(tmp_path)
                    lang = lang_probs[0][0] if lang_probs else None

                if lang:
                    votes.append(lang)
                    _log(f"   片段 {i + 1}/{NUM_CLIPS} ({start_ms // 1000}s): [{lang}]")
            except Exception as e:
                _log(f"   片段 {i + 1} 偵測失敗: {e}")

        if not votes:
            _log("⚠️  語言偵測無法取得任何結果，將使用 Whisper 自動判斷。")
            return None

        winner, count = Counter(votes).most_common(1)[0]
        _log(
            f"🌐 語言偵測結果：[{winner}]（{count}/{len(votes)} 片段同意）— 將鎖定此語言進行轉錄。"
        )
        return winner

    finally:
        for p in tmp_paths:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass


class Phase1Transcribe(PipelineBase):
    def __init__(self):
        super().__init__(phase_key="p1", phase_name="語音轉錄", logger=None)
        # Audio Chunk Fallback config (#7)
        fb_cfg = self.config_manager.get_section("phase1_chunk_fallback") or {}
        self.chunk_fallback_enabled = bool(fb_cfg.get("enabled", True))
        self.max_chunk_duration_sec = float(fb_cfg.get("max_chunk_duration_sec", 30.0))

    def run(self, force=False, subject=None, file_filter=None, single_mode=False, resume_from=None):
        self.log("🚀 啟動 Phase 1：語音轉錄 (V8.1 抗幻覺版)")

        # Sandbox HuggingFace to strictly inside the project
        openclaw_root = os.path.abspath(os.path.join(self.base_dir, "..", ".."))
        model_dir = os.path.join(openclaw_root, "models")
        os.makedirs(model_dir, exist_ok=True)
        os.environ["HF_HOME"] = model_dir
        os.environ["HF_HUB_CACHE"] = model_dir

        model = None
        current_model_name = None

        tasks = self.get_tasks(
            force=force,
            subject_filter=subject,
            file_filter=file_filter,
            single_mode=single_mode,
            resume_from=resume_from,
        )

        if not tasks:
            self.log("📋 Phase 1 沒有待轉錄的音檔。")
            return

        self.log(f"📋 Phase 1 共有 {len(tasks)} 個音檔待轉錄。")

        for idx, task in enumerate(tasks, 1):
            if self.check_system_health():
                break

            subj, fname = task["subject"], task["filename"]

            # ── 讀取設定 ────────────────────────────────────────────────
            config = self.get_config("phase1", subject_name=subj)
            engine = config.get("engine", "faster-whisper").lower()
            model_name = config.get("model", "medium")
            device = config.get("device", "cpu")
            compute_type = config.get("compute_type", "int8")
            beam_size = int(config.get("beam_size", 5))

            # 讀取抗幻覺設定（所有值均有合理預設值）
            ah = config.get("anti_hallucination", {})
            # Layer 0
            condition_on_prev_text = bool(ah.get("condition_on_previous_text", False))
            compression_ratio_thresh = float(ah.get("compression_ratio_threshold", 2.4))
            no_speech_thresh = float(ah.get("no_speech_threshold", 0.6))
            hallucination_silence_sec = float(ah.get("hallucination_silence_threshold", 2.0))
            # Layer 1
            vad_enabled = bool(ah.get("vad_enabled", True))
            vad_min_silence_ms = int(ah.get("vad_min_silence_len_ms", 1500))
            vad_silence_dbfs = int(ah.get("vad_silence_thresh_dbfs", -35))
            vad_padding_ms = int(ah.get("vad_padding_ms", 300))
            vad_max_removal_ratio = float(ah.get("vad_max_removal_ratio", 0.90))
            # Language detection
            lang_detect_enabled = bool(ah.get("language_detection_enabled", True))
            lang_detect_clip_sec = float(ah.get("language_detection_clip_sec", 30.0))
            force_language = ah.get("force_language", None) or None  # e.g. 'zh', None = auto
            # Layer 2
            rep_enabled = bool(ah.get("repetition_detection_enabled", True))
            rep_ngram = int(ah.get("repetition_ngram_size", 4))
            rep_threshold = float(ah.get("repetition_threshold", 0.45))
            rep_compress_ratio = float(ah.get("repetition_compress_ratio", 0.3))
            retry_temperature = float(ah.get("retry_temperature", 0.2))

            # Re-load model if profile changes between subjects
            if model is not None and current_model_name != model_name:
                model = None
            current_model_name = model_name

            base_name = fname.replace(".m4a", "")
            audio_path = os.path.join(self.dirs["p0"], subj, fname)
            pure_out_path = os.path.join(self.dirs["p1"], subj, f"{base_name}.md")
            ts_out_path = os.path.join(self.dirs["p1"], subj, f"{base_name}_timestamped.md")
            tmp_dir = os.path.join(self.dirs["p1"], subj, "tmp")

            os.makedirs(os.path.dirname(pure_out_path), exist_ok=True)

            self.log(f"🎙️ [{idx}/{len(tasks)}] 正在處理：[{subj}] {fname}")

            # ── 載入模型 ────────────────────────────────────────────────
            if model is None:
                if engine == "faster-whisper":
                    try:
                        from faster_whisper import WhisperModel
                    except ImportError:
                        self.log(
                            "❌ 找不到 faster_whisper。請安裝: pip3 install faster-whisper", "error"
                        )
                        return
                    self.log(f"🧠 載入 Whisper ({engine}) {model_name}...")
                    model = WhisperModel(
                        model_name,
                        device=device,
                        compute_type=compute_type,
                        download_root=model_dir,
                    )
                elif engine == "mlx-whisper":
                    try:
                        import mlx_whisper
                    except ImportError:
                        self.log("❌ 找不到 mlx_whisper。請安裝: pip3 install mlx-whisper", "error")
                        return
                    self.log(f"🧠 備妥 Whisper ({engine}) {model_name}...")

            try:
                # ── 語言偵測（在 VAD 前對原始音檔執行） ────────────────────
                detected_lang = force_language
                if not detected_lang and lang_detect_enabled:
                    self.log(f"🌐 語言偵測中（前 {lang_detect_clip_sec:.0f}s）...")
                    detected_lang = detect_audio_language(
                        audio_path=audio_path,
                        engine=engine,
                        model=model,
                        model_name=model_name,
                        clip_duration_sec=lang_detect_clip_sec,
                        log_fn=self.log,
                    )

                # ── Layer 1: VAD 前處理 ──────────────────────────────────
                cleaned_path = audio_path
                if vad_enabled:
                    self.log(
                        f"🔇 Layer 1: VAD 前處理中（閾值 {vad_silence_dbfs} dBFS，上限移除率 {vad_max_removal_ratio:.0%}）..."
                    )
                    cleaned_path = vad_preprocess(
                        audio_path=audio_path,
                        tmp_dir=tmp_dir,
                        min_silence_len_ms=vad_min_silence_ms,
                        silence_thresh_dbfs=vad_silence_dbfs,
                        padding_ms=vad_padding_ms,
                        max_removal_ratio=vad_max_removal_ratio,
                        log_fn=self.log,
                    )

                # #7 ── Time-based Chunk Fallback ──────────────────────────
                # Handles continuous speech where VAD finds insufficient silence.
                # Splits audio into deterministic fixed-length chunks so Whisper
                # never receives audio longer than max_chunk_duration_sec.
                self._time_chunks: list = []
                if self.chunk_fallback_enabled:
                    try:
                        from pydub import AudioSegment

                        _audio_seg = AudioSegment.from_file(cleaned_path)
                        duration_sec = len(_audio_seg) / 1000.0
                        max_ms = int(self.max_chunk_duration_sec * 1000)
                        if duration_sec > self.max_chunk_duration_sec * 1.2:
                            self.log(
                                f"⚠️ [Chunk Fallback] 音檔長度 {duration_sec:.1f}s > "
                                f"{self.max_chunk_duration_sec:.0f}s，啟動時間切片保護模式"
                            )
                            os.makedirs(tmp_dir, exist_ok=True)
                            chunk_paths = []
                            for start_ms in range(0, len(_audio_seg), max_ms):
                                seg = _audio_seg[start_ms : start_ms + max_ms]
                                seg_path = os.path.join(
                                    tmp_dir,
                                    f"{base_name}_chunk{start_ms // max_ms:04d}.wav",
                                )
                                seg.export(seg_path, format="wav")
                                chunk_paths.append(seg_path)
                            self._time_chunks = chunk_paths
                            self.log(
                                f"✅ [Chunk Fallback] 切分為 {len(chunk_paths)} 個 "
                                f"{self.max_chunk_duration_sec:.0f}s 時間區塊"
                            )
                    except ImportError:
                        self.log("⚠️ [Chunk Fallback] pydub 未安裝，跳過時間切片", "warn")
                    except Exception as _ce:
                        self.log(f"⚠️ [Chunk Fallback] 切片失敗: {_ce}，繼續使用原始音檔", "warn")

                pure_text = ""
                ts_text = ""
                segments = []

                # 將偵測到的語言碼準備為 VAR_KEYWORD（直接展開傳入）
                lang_kwargs = {"language": detected_lang} if detected_lang else {}

                # F2: Use time-based chunks if Chunk Fallback produced them; otherwise use full file
                _audio_paths_to_transcribe = (
                    self._time_chunks if self._time_chunks else [cleaned_path]
                )

                if engine == "mlx-whisper":
                    import warnings

                    import mlx_whisper

                    _n_chunks = len(_audio_paths_to_transcribe)
                    chunk_iter = _audio_paths_to_transcribe

                    if _n_chunks > 1:
                        from tqdm import tqdm

                        self.log(f"   📦 共 {_n_chunks} 個區塊，啟動批次轉錄...")
                        chunk_iter = tqdm(
                            _audio_paths_to_transcribe,
                            desc="   轉錄進度",
                            unit="區塊",
                            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
                        )

                    for _chunk_path in chunk_iter:
                        # 同時壓制 stdout(fd 1) 與 stderr(fd 2)，
                        # 避免 mlx_whisper 內部 tqdm 進度條輸出至終端
                        with open(os.devnull, "w") as _devnull, warnings.catch_warnings():
                            warnings.simplefilter("ignore")
                            _old_err = os.dup(2)
                            _old_out = os.dup(1)
                            os.dup2(_devnull.fileno(), 2)
                            os.dup2(_devnull.fileno(), 1)
                            try:
                                result = mlx_whisper.transcribe(
                                    _chunk_path,
                                    path_or_hf_repo=model_name,
                                    condition_on_previous_text=condition_on_prev_text,
                                    compression_ratio_threshold=compression_ratio_thresh,
                                    no_speech_threshold=no_speech_thresh,
                                    hallucination_silence_threshold=hallucination_silence_sec,
                                    word_timestamps=True,
                                    **lang_kwargs,
                                    verbose=False,
                                )
                            finally:
                                os.dup2(_old_err, 2)
                                os.dup2(_old_out, 1)
                                os.close(_old_err)
                                os.close(_old_out)
                        segments.extend(result.get("segments", []))

                else:  # faster-whisper
                    from tqdm import tqdm

                    for _chunk_path in _audio_paths_to_transcribe:
                        segments_gen, info = model.transcribe(
                            _chunk_path,
                            beam_size=beam_size,
                            vad_filter=True,
                            condition_on_previous_text=condition_on_prev_text,
                            word_timestamps=True,
                        )
                        duration = int(info.duration)
                        last_end = 0
                        with tqdm(
                            total=duration,
                            desc=f"\u8f49\u9304\u9032\u5ea6 ({os.path.basename(_chunk_path)})",
                            unit="\u79d2",
                            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
                        ) as pbar:
                            for s in segments_gen:
                                inc = int(s.end) - last_end
                                if inc > 0:
                                    pbar.update(inc)
                                    last_end = int(s.end)
                                segments.append(s)
                            if last_end < duration:
                                pbar.update(duration - last_end)

                # ── Layer 2: Segment 掃描 + 局部重試 ────────────────────
                hallucination_count = 0
                last_segment_end = None

                for s in segments:
                    is_dict = isinstance(s, dict)
                    text_val = s["text"] if is_dict else s.text
                    start_val = s["start"] if is_dict else s.start
                    end_val = s["end"] if is_dict else s.end
                    words = s.get("words", []) if is_dict else getattr(s, "words", [])

                    start_m, start_s = int(start_val // 60), int(start_val % 60)
                    end_m, end_s = int(end_val // 60), int(end_val % 60)

                    # ── Light Diarization (Speaker Separation on Pauses) ──
                    if last_segment_end is not None and (start_val - last_segment_end > 1.5):
                        pure_text += "\n\n"
                        ts_text += "\n"
                    last_segment_end = end_val

                    # 偵測到幻覺 → 嘗試局部重試
                    if rep_enabled and detect_repetition(
                        text_val, rep_ngram, rep_threshold, rep_compress_ratio
                    ):
                        hallucination_count += 1
                        self.log(
                            f"🔁 Layer 2: 幻覺 [{start_m:02d}:{start_s:02d}-{end_m:02d}:{end_s:02d}]"
                            f" 啟動局部重試..."
                        )
                        repaired = retry_segment(
                            audio_path=cleaned_path,
                            start_sec=start_val,
                            end_sec=end_val,
                            tmp_dir=tmp_dir,
                            engine=engine,
                            model=model,
                            model_name=model_name,
                            retry_temperature=retry_temperature,
                            ngram_size=rep_ngram,
                            repetition_threshold=rep_threshold,
                            compress_ratio_threshold=rep_compress_ratio,
                            log_fn=self.log,
                        )
                        text_val = repaired  # None = 重試仍失敗
                        words = []  # Clear words if we retry, since retry doesn't guarantee word timestamps

                    # ── Low-Confidence Flagging (<60%) ──
                    formatted_text = ""
                    if text_val is not None:
                        if words:
                            for w in words:
                                w_text = w["word"] if isinstance(w, dict) else w.word
                                w_prob = w["probability"] if isinstance(w, dict) else w.probability
                                w_start = w["start"] if isinstance(w, dict) else w.start

                                if w_prob < 0.60:
                                    formatted_text += f"[? {w_text.strip()} | {w_start:.1f} ?] "
                                else:
                                    formatted_text += w_text
                        else:
                            formatted_text = text_val

                        formatted_text = formatted_text.strip()

                    # ── 分層輸出策略 ─────────────────────────────────────
                    if text_val is None:
                        # pure_text：靜默跳過（讓 Phase 2 AI 自然補缺）
                        # ts_text：保留時間戳標記供 debug 審查
                        ts_text += (
                            f"[HALLUCINATION_DETECTED "
                            f"{start_m:02d}:{start_s:02d}-{end_m:02d}:{end_s:02d}]\n"
                        )
                    else:
                        pure_text += formatted_text + " "
                        ts_text += (
                            f"[{start_m:02d}:{start_s:02d}] - [{end_m:02d}:{end_s:02d}]"
                            f" {formatted_text}\n"
                        )

                if hallucination_count > 0:
                    self.log(f"🛡️  Layer 2 修補完成：共處理 {hallucination_count} 個幻覺 Segment。")

                # ── 寫入輸出 ─────────────────────────────────────────────
                AtomicWriter.write_text(pure_out_path, pure_text)
                AtomicWriter.write_text(ts_out_path, ts_text)

                # DAG 追蹤
                out_hash = self.state_manager.get_file_hash(pure_out_path)
                self.state_manager.update_task(subj, fname, "p1", status="✅", output_hash=out_hash)

                self.log(f"✅ [{idx}/{len(tasks)}] 轉錄完成：{fname}")

                # ── 清理 VAD 暫存 ────────────────────────────────────────
                if cleaned_path != audio_path and os.path.exists(cleaned_path):
                    try:
                        os.remove(cleaned_path)
                    except OSError:
                        pass

                # 暫停機制：每個任務完成後檢查是否要 checkpoint
                if self.stop_requested:
                    if self.pause_requested and idx < len(tasks):
                        next_task = tasks[idx]  # idx 已是 1-based，下一個剛好
                        self.save_checkpoint(next_task["subject"], next_task["filename"])
                    break

            except Exception as e:
                self.log(f"❌ 轉錄失敗 {fname}: {e}", "error")
                # 清理 VAD 暫存（即使失敗也要清）
                if "cleaned_path" in locals() and cleaned_path != audio_path:
                    if os.path.exists(cleaned_path):
                        try:
                            os.remove(cleaned_path)
                        except OSError:
                            pass

        # ── 釋放模型與記憶體 ──────────────────────────────────────────
        self.log("🧹 [Phase 1] 正在卸載轉錄模型並釋放記憶體...")
        if model is not None:
            del model

        import gc

        gc.collect()

        # 清理 MLX / PyTorch 快取
        if engine == "mlx-whisper":
            try:
                import mlx.core as mx

                mx.clear_cache()
            except Exception:
                pass
        elif engine == "faster-whisper":
            try:
                import torch

                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception:
                pass

        self.log("✅ [Phase 1] 記憶體釋放完成。")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--force", "-f", action="store_true")
    parser.add_argument("--subject", "-s", type=str)
    args = parser.parse_args()
    Phase1Transcribe().run(force=args.force, subject=args.subject)
