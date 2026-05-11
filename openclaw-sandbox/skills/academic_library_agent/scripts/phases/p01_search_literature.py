"""
Phase 1: Institutional Literature Search + ArXiv Fallback
==========================================================
Search strategy (priority order):

  1. ScienceDirect via Playwright + NDHU OpenAthens session
     → Accesses full-text of paywalled Elsevier journals.
     → Requires populated playwright_profile (setup_playwright_auth.sh).

  2. ArXiv public API (automatic fallback)
     → Free, no authentication, covers most STEM preprints.
     → Returns abstract + PDF URL for evidence file.

Token optimization:
  - ScienceDirect: DOM-stripped clean-text snapshot (≥50% token reduction).
  - ArXiv: abstract only (≤500 tokens per paper). Full PDF fetched only on demand.

Evidence files:
  All snapshots/abstracts are written to data/academic_library_agent/evidence/
  with deterministic filenames for 100% local traceability.
"""

from __future__ import annotations

import asyncio
import json
import os
import re

from core.orchestration.pipeline_base import PipelineBase as PhaseBase
from core.utils.atomic_writer import AtomicWriter
from core.utils.playwright_utils import get_clean_text_snapshot, get_persistent_context

_EVIDENCE_SUBDIR = "evidence"


def _safe_slug(text: str, max_len: int = 40) -> str:
    """Convert a query string to a filesystem-safe slug."""
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[\s_-]+", "_", slug).strip("_")
    return slug[:max_len]


class Phase1SearchLiterature(PhaseBase):
    def __init__(self) -> None:
        super().__init__(
            phase_key="p01_search_literature",
            phase_name="Institutional Literature Search + ArXiv Fallback",
            skill_name="academic_library_agent",
        )

    # ------------------------------------------------------------------ #
    #  Strategy 1: ScienceDirect via Playwright                           #
    # ------------------------------------------------------------------ #

    async def _search_sciencedirect(self, query: str) -> str | None:
        """Return cleaned article text from ScienceDirect, or None on failure."""
        search_url = f"https://www.sciencedirect.com/search?qs={query.replace(' ', '%20')}"
        try:
            async with get_persistent_context(headless=True) as context:
                page = await context.new_page()
                self.info(f"  🔍 ScienceDirect: '{query}'")
                await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_selector(".result-item-content", timeout=15000)

                first = await page.query_selector(".result-item-content h2 a")
                if not first:
                    return None

                await first.click()
                await page.wait_for_load_state("domcontentloaded", timeout=60000)
                await page.wait_for_selector("#body", timeout=15000)
                snapshot = await get_clean_text_snapshot(page)
                self.info("  ✅ ScienceDirect: 成功擷取全文快照")
                return snapshot

        except Exception as exc:
            self.warning(f"  ⚠️  ScienceDirect 失敗 ({exc.__class__.__name__}): {exc}")
            return None

    # ------------------------------------------------------------------ #
    #  Strategy 2: ArXiv public API fallback                              #
    # ------------------------------------------------------------------ #

    def _search_arxiv(self, query: str, max_results: int = 3) -> str | None:
        """Return a formatted multi-abstract snippet from ArXiv."""
        try:
            import arxiv  # noqa: PLC0415 — optional dependency, lazy import

            client = arxiv.Client()
            search = arxiv.Search(query=query, max_results=max_results)
            results = list(client.results(search))

            if not results:
                return None

            parts: list[str] = []
            for paper in results:
                entry = (
                    f"**Title**: {paper.title}\n"
                    f"**Authors**: {', '.join(str(a) for a in paper.authors[:3])}"
                    f"{'et al.' if len(paper.authors) > 3 else ''}\n"
                    f"**Published**: {paper.published.strftime('%Y-%m-%d') if paper.published else 'N/A'}\n"
                    f"**ArXiv ID**: {paper.entry_id}\n"
                    f"**Abstract**: {paper.summary[:800]}...\n"
                )
                parts.append(entry)

            self.info(f"  ✅ ArXiv: 找到 {len(results)} 篇相關論文")
            return "\n\n---\n\n".join(parts)

        except ImportError:
            self.warning("  ⚠️  arxiv 套件未安裝 (pip install arxiv)")
            return None
        except Exception as exc:
            self.warning(f"  ⚠️  ArXiv 搜尋失敗: {exc}")
            return None

    # ------------------------------------------------------------------ #
    #  Evidence File Persistence                                           #
    # ------------------------------------------------------------------ #

    def _save_evidence(self, query: str, snapshot: str, source: str) -> str:
        """Write snapshot to a deterministic local evidence file."""
        evidence_dir = os.path.join(self.base_dir, _EVIDENCE_SUBDIR)
        os.makedirs(evidence_dir, exist_ok=True)
        slug = _safe_slug(query)
        filename = f"evidence_{slug}__{source}.txt"
        path = os.path.join(evidence_dir, filename)
        AtomicWriter.write_text(path, snapshot)
        self.info(f"  💾 Evidence saved: {path}")
        return path

    def run(self, force: bool = False, subject: str | None = None, **kwargs: object) -> None:
        """Search literature for each task and persist evidence."""
        tasks = self.get_tasks(force=force, subject_filter=subject)
        if not tasks:
            self.log("📋 No pending literature search tasks.")
            return
        for task in tasks:
            query = task.get("filename", "")
            self.log(f"🔍 Searching: {query}")
            snapshot = asyncio.run(self._search_sciencedirect(query))
            source = "sciencedirect"
            if not snapshot:
                snapshot = self._search_arxiv(query)
                source = "arxiv"
            if snapshot:
                out_path = self._save_evidence(query, snapshot, source)
                self.info(f"  💾 文獻搜尋完成，輸出至: {out_path}")
            else:
                self.warning(f"  ⚠️  No results found for: {query}")
        self.state_manager.sync_physical_files()
