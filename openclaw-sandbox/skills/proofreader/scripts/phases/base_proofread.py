import os
from typing import Tuple

from core import PipelineBase
from core.state.global_registry import GlobalRegistry


class BaseProofreadPhase(PipelineBase):
    """
    Shared base class for proofreader phases to eliminate boilerplate and unify reference data lookup.
    """

    def _unload_used_models(self) -> None:
        if hasattr(self, "_used_models"):
            for m in self._used_models:
                self.llm.unload_model(m, logger=self)

    def _get_reference_data(
        self,
        subject: str,
        prefix: str,
        transcript_text: str = None,
        use_semantic_fallback: bool = False,
    ) -> Tuple[str, str]:
        """Fetch doc_parser reference text and figure list for this prefix.

        Reads all paths registered under (subject, prefix, "doc_parser") in GlobalRegistry.
        Optionally uses Semantic Matcher to find related docs if no direct match is found.
        """
        registry = GlobalRegistry(self.workspace_root)
        paths = registry.get_asset_paths(subject, prefix, "doc_parser")

        # Fast Path Fallback: Semantic Matching
        if not paths and use_semantic_fallback and transcript_text:
            self.log(f"⚠️ 找不到前綴 {prefix} 的直接配對，啟動語意檢索 (Semantic Pairing)...")

            try:
                from core.ai.semantic_matcher import SemanticMatcher

                matcher = SemanticMatcher(self.llm)

                subject_assets = registry.get_subject_assets(subject)
                candidate_docs = {}
                for doc_prefix, skills_map in subject_assets.items():
                    raw_paths = skills_map.get("doc_parser")
                    if not raw_paths:
                        continue
                    path_list = raw_paths if isinstance(raw_paths, list) else [raw_paths]
                    first_path = path_list[0]
                    if os.path.exists(first_path):
                        try:
                            with open(first_path, encoding="utf-8") as f:
                                candidate_docs[doc_prefix] = f.read()[:1500]
                        except Exception:
                            pass

                if candidate_docs:
                    best_prefixes = matcher.find_best_matches(
                        transcript_text, candidate_docs, target_prefix=prefix, logger=self
                    )
                    for bp in best_prefixes:
                        paths.extend(registry.get_asset_paths(subject, bp, "doc_parser"))
                    if not best_prefixes:
                        self.log("⚠️ 語意檢索未能找到相關講義，放棄配對。")
                else:
                    self.log("⚠️ 該 subject 無任何 doc_parser 候選講義，放棄配對。")
            except ImportError:
                self.log("⚠️ 無法載入 SemanticMatcher", "warn")

        ref_parts: list[str] = []
        fig_parts: list[str] = []
        ref_files = []

        for p in paths:
            if not os.path.exists(p):
                continue

            ref_files.append(os.path.basename(p))

            try:
                with open(p, encoding="utf-8") as f:
                    ref_parts.append(f.read()[:6000])
            except Exception:
                pass

            fig_path = os.path.join(os.path.dirname(p), "figure_list.md")
            if os.path.exists(fig_path):
                try:
                    with open(fig_path, encoding="utf-8") as f:
                        fig_parts.append(f.read())
                except Exception:
                    pass

        self._current_ref_files = ref_files
        ref_text = ("\n\n---\n\n".join(ref_parts))[:20000]
        figure_list_text = "\n\n".join(fig_parts)
        return ref_text, figure_list_text
