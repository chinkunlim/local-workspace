# MODEL_SELECTION.md — Open Claw Skill Model Registry

> **Strategy**: Quality-First (2026-05-04)
> **Hardware**: Apple Silicon, 16GB Unified RAM
> **Last Updated**: 2026-05-04

All model choices are driven by **output quality** as the primary criterion.
Resource constraints are secondary — all models listed below are confirmed
runnable on the target hardware (RUNS GREAT / RUNS WELL / DECENT tiers from
[canIrunAI.com](https://www.canrunaI.com) with Apple Silicon 16GB).

---

## Installed Model Reference

| Model | Size | Perf. Tier | Best For |
|:---|:---|:---:|:---|
| `phi4-mini-reasoning` | 3.2GB | RUNS WELL | Reasoning with 128K context |
| `qwen3:8b` | 5.2GB | DECENT | General routing, fast fallback |
| `deepseek-r1:8b` | 5.2GB | RUNS WELL | Chain-of-Thought analytical reasoning |
| `gemma4:e2b` | 7.2GB | RUNS WELL | Fast instruction following |
| `llama3.2-vision` | 7.8GB | RUNS WELL | Multimodal vision tasks |
| `gemma4:e4b` | 9.6GB | DECENT | High-quality instruction following |
| `qwen3:14b` | 9.3GB | DECENT | Strongest general reasoning, Chinese academic |

---

## Per-Skill Model Assignment

### `note_generator`
| Role | Model | Rationale |
|:---|:---|:---|
| **Primary** | `qwen3:14b` (profile: `qwen3_reasoning`) | Largest model for best synthesis quality; generates more nuanced Cornell notes and Mermaid diagrams |
| **Fallback** | `phi4-mini-reasoning` (profile: `phi4_reasoning`) | 128K context allows fewer Map-Reduce splits; fast for large files |
| **Inactive** | `gemma4:e4b` (profile: `default`) | Original default, good instruction following |

```yaml
# To switch to fallback:
# synthesize.active_profile: phi4_reasoning
```

---

### `feynman_simulator` (Student Agent)
| Role | Model | Rationale |
|:---|:---|:---|
| **Primary** | `deepseek-r1:8b` | Native Chain-of-Thought; `<think>` tokens enable genuine Socratic argument construction |
| **Fallback** | `qwen3:8b` (hardcoded in scripts) | Fast general fallback |

```yaml
# config.yaml: models.default.name: "deepseek-r1:8b"
```

---

### `student_researcher`
| Role | Model | Rationale |
|:---|:---|:---|
| **Primary** | `deepseek-r1:8b` | CoT reasoning identifies *which* claims need academic verification; superior to general models for analytical tasks |
| **Fallback** | `qwen3:8b` (config) | Reliable general fallback |

```yaml
# config.yaml: models.default.name: "deepseek-r1:8b"
```

---

### `knowledge_compiler`
| Role | Model | Rationale |
|:---|:---|:---|
| **Primary** | `qwen3:14b` | Largest model for most accurate entity/relation extraction and WikiLink generation |
| **Fallback** | `qwen3:8b` (config fallback key) | Circuit-breaker fallback |

```yaml
# config.yaml: models.default: "qwen3:14b" / fallback: "qwen3:8b"
```

---

### `gemini_verifier_agent`
| Role | Model | Rationale |
|:---|:---|:---|
| **Primary** | `qwen3:14b` | Strongest argumentation capacity needed for AI-to-AI debate with Gemini |
| **Fallback** | `qwen3:8b` (config) | Sufficient for simpler verification tasks |

---

### `academic_edu_assistant`
| Role | Model | Rationale |
|:---|:---|:---|
| **Primary** | `qwen3:14b` | Deep academic concept comparison and high-quality Anki card generation |
| **Fallback** | `qwen3:8b` (config) | |

---

### `academic_library_agent`
| Role | Model | Rationale |
|:---|:---|:---|
| **Primary** | `qwen3:14b` | Best comprehension of academic paper abstracts and structured data extraction |
| **Fallback** | `qwen3:8b` (config) | |

---

### `interactive_reader`
| Role | Model | Rationale |
|:---|:---|:---|
| **Primary** | `qwen3:14b` | Superior Q&A quality for document-grounded conversation |
| **Fallback** | `qwen3:8b` (commented in config) | |

---

### `video_ingester`
| Role | Model | Rationale |
|:---|:---|:---|
| **Primary** | `qwen3:14b` | Best quality keyframe description and text-video integration |
| **Fallback** | `qwen3:8b` (config) | |
| **ASR** | `mlx-community/whisper-large-v3-turbo` | Fixed — MLX Whisper, not Ollama |

---

### `audio_transcriber`
| Role | Model | Rationale |
|:---|:---|:---|
| **Phase 2 (cleanup)** | `gemma4:e4b` | Google Gemma4 excels at instruction-following for disfluency removal |
| **Phase 3 (highlights)** | `gemma4:e4b` | Consistent structured output for highlight extraction |
| **Fallback** | `gemma4:e2b` (configurable) | Faster, lower VRAM |
| **ASR** | `mlx-community/whisper-large-v3-turbo` | Fixed — MLX Whisper |

---

### `smart_highlighter`
| Role | Model | Rationale |
|:---|:---|:---|
| **Quality profiles** | `gemma4:e4b` | Best precision for academic term identification |
| **Fast profile** | `gemma4:e2b` | Lower VRAM for rapid highlighting passes |

---

### `telegram_kb_agent`
| Role | Model | Rationale |
|:---|:---|:---|
| **Primary** | `gemma4:e4b` | Best Q&A quality for RAG-based knowledge retrieval |
| **Fallback** | `gemma4:e2b` (commented in config) | Faster for high-volume queries |

```yaml
# To switch to fallback:
# rag.generate_model: "gemma4:e2b"
```

---

### `doc_parser`
| Role | Model | Rationale |
|:---|:---|:---|
| **Vision** | `llama3.2-vision` | Only multimodal vision model installed; handles PDF image OCR |
| **Text analysis** | `qwen3:8b` (fallback) | General text processing |

---

### `RouterAgent` (intent decomposition)
| Role | Model | Rationale |
|:---|:---|:---|
| **Low complexity** | `qwen3:8b` | Routing decisions don't need the biggest model; fast response |
| **High complexity** | `qwen3:14b` | Complex intent decomposition (debate/research/feynman keywords) |

---

## How to Switch to Fallback

Each skill's `config.yaml` has commented fallback options. To use a fallback:

1. **Profile-based** (note_generator): change `synthesize.active_profile`
2. **Direct model key** (knowledge_compiler, video_ingester): edit `models.default`
3. **Named profile** (feynman_simulator, student_researcher): edit `models.default.name`

---

## Update History

| Date | Change |
|:---|:---|
| 2026-05-04 | Initial quality-first model assignment (Phase A V9.1) |
| 2026-05-04 | note_generator: phi4-mini → qwen3:14b (primary) |
| 2026-05-04 | student_researcher: qwen3:8b → deepseek-r1:8b |
| 2026-05-04 | knowledge_compiler, gemini_verifier, edu_assistant, library_agent, interactive_reader, video_ingester: qwen3:8b → qwen3:14b |
| 2026-05-04 | telegram_kb_agent: gemma4:e2b → gemma4:e4b |
| 2026-05-04 | RouterAgent high-complexity: deepseek-r1:14b → qwen3:14b |
