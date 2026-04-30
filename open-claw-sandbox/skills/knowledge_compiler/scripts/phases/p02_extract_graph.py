"""
skills/knowledge_compiler/scripts/phases/p02_extract_graph.py  (P3-2)
======================================================================
Phase 2: Wikilink → Entity-Relation Graph Extraction.

Parses compiled wiki/*.md files from p01_compile, extracts:
  - Entities from [[wikilink]] syntax
  - Relations from the "## 延伸連結" section
  - Tags from #Hashtag entries

Then upserts everything into the configured GraphStore backend
(NetworkX local or Neo4j prod).

CLI:
    python p02_extract_graph.py [--subject SUBJECT] [--force]

After this phase runs, core.hybrid_retriever can augment vector queries
with 1-hop graph neighbours (P3-3).
"""

from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))
from core.utils.bootstrap import ensure_core_path as _bootstrap

_bootstrap(__file__)

from core import PipelineBase
from core.ai.graph_store import get_graph_store

# Regex patterns
_WIKILINK_RE = re.compile(r"\[\[([^\[\]|#]+?)(?:\|[^\]]+?)?\]\]")
_HASHTAG_RE = re.compile(r"(?<!\w)#([A-Za-z\u4e00-\u9fff][A-Za-z0-9\u4e00-\u9fff_-]*)")
_RELATION_SECTION_RE = re.compile(r"##\s*延伸連結(.*?)(?=\n##|\Z)", re.DOTALL)
_RELATION_LINE_RE = re.compile(
    r"([\u4e00-\u9fff A-Za-z0-9_-]+?)\s+((?:RELATED_TO|IS_A|PART_OF|DEPENDS_ON|ENABLES|CITES|延伸|關聯|屬於|包含|依賴))\s+([\u4e00-\u9fff A-Za-z0-9_-]+)",
    re.IGNORECASE,
)

# Default relation when only a wikilink is found with no explicit relation
DEFAULT_RELATION = "RELATED_TO"


class Phase2ExtractGraph(PipelineBase):
    """Phase 2: Entity-Relation extraction from compiled wiki notes."""

    def __init__(self):
        super().__init__(
            phase_key="p2",
            phase_name="知識圖譜抽取",
            skill_name="knowledge_compiler",
        )
        # wiki_dir from p01 config
        output_cfg = self.config_manager.get_section("output") or {}
        default_wiki = os.path.abspath(os.path.join(self.base_dir, "..", "wiki"))
        self.wiki_dir = os.path.realpath(output_cfg.get("wiki_dir", default_wiki))
        self.graph = get_graph_store(self.workspace_root, skill_name="knowledge_compiler")

    # ── Parsing ───────────────────────────────────────────────────────────

    @staticmethod
    def _extract_wikilinks(text: str) -> list[str]:
        return _WIKILINK_RE.findall(text)

    @staticmethod
    def _extract_hashtags(text: str) -> list[str]:
        return _HASHTAG_RE.findall(text)

    @staticmethod
    def _extract_explicit_relations(text: str) -> list[tuple[str, str, str]]:
        """Return (src, relation, dst) triples from '## 延伸連結' section."""
        relations: list[tuple[str, str, str]] = []
        m = _RELATION_SECTION_RE.search(text)
        if not m:
            return relations
        section = m.group(1)
        for match in _RELATION_LINE_RE.finditer(section):
            relations.append(
                (match.group(1).strip(), match.group(2).strip(), match.group(3).strip())
            )
        return relations

    # ── Processing ────────────────────────────────────────────────────────

    def _process_file(self, filepath: str) -> None:
        filename = os.path.basename(filepath)
        try:
            with open(filepath, encoding="utf-8") as f:
                text = f.read()
        except Exception as exc:
            self.warning(f"⚠️ 無法讀取 {filename}: {exc}")
            return

        # Extract title (first H1)
        title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        doc_title = title_match.group(1).strip() if title_match else os.path.splitext(filename)[0]

        # Upsert document entity
        self.graph.upsert_entity(doc_title, labels=["Document", "Note"], props={"file": filename})

        # Wikilinks → RELATED_TO edges
        links = self._extract_wikilinks(text)
        for link in links:
            link = link.strip()
            if link and link != doc_title:
                self.graph.upsert_entity(link, labels=["Concept"])
                self.graph.upsert_relation(doc_title, DEFAULT_RELATION, link)

        # Hashtags → IS_A Domain edges
        for tag in self._extract_hashtags(text):
            self.graph.upsert_entity(tag, labels=["Domain", "Tag"])
            self.graph.upsert_relation(doc_title, "IS_A", tag)

        # Explicit relations from 延伸連結 section
        for src, rel, dst in self._extract_explicit_relations(text):
            self.graph.upsert_entity(src, labels=["Concept"])
            self.graph.upsert_entity(dst, labels=["Concept"])
            self.graph.upsert_relation(src, rel.upper(), dst)

        self.info(f"  ✅ {doc_title}: {len(links)} 連結, {len(self._extract_hashtags(text))} 標籤")

    def run(self, force: bool = False, subject: str | None = None, **_kwargs) -> None:
        self.info("🕸️ 啟動 Phase 2：知識圖譜抽取")
        if not os.path.isdir(self.wiki_dir):
            self.error(f"❌ wiki_dir 不存在: {self.wiki_dir}  請先執行 Phase 1 (p01_compile)")
            return

        files = [
            os.path.join(self.wiki_dir, f)
            for f in os.listdir(self.wiki_dir)
            if f.endswith(".md") and f != "INDEX.md"
        ]

        if not files:
            self.warning("⚠️ wiki/ 目錄為空，無可處理的檔案。")
            return

        self.info(f"📄 共找到 {len(files)} 個 wiki 筆記，開始抽取實體與關係...")
        for filepath in sorted(files):
            self._process_file(filepath)

        # Persist graph state
        self.graph.close()

        if hasattr(self.graph, "node_count"):
            self.info(
                f"\n✨ 圖譜抽取完成！節點: {self.graph.node_count}, 邊: {self.graph.edge_count}"
            )
        else:
            self.info("\n✨ 圖譜抽取完成！")

        # Publish event for downstream consumers (P1-1 EventBus)
        try:
            from core.orchestration.event_bus import DomainEvent, EventBus

            EventBus.publish(
                DomainEvent(
                    name="KnowledgeCompiled",
                    source_skill="knowledge_compiler",
                    payload={"wiki_dir": self.wiki_dir, "file_count": len(files)},
                )
            )
        except Exception:
            pass  # EventBus is optional — never block the pipeline


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Knowledge Compiler — Phase 2: Graph Extraction")
    parser.add_argument("--subject", help="Filter by subject")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    Phase2ExtractGraph().run(force=args.force, subject=args.subject)
