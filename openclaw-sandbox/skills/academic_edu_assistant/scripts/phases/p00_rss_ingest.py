"""
skills/academic_edu_assistant/scripts/phases/p00_rss_ingest.py  (P2-2)
=====================================================================
Proactive RSS/Atom feed ingestion for the academic_edu_assistant skill.

Fetches papers from configured feeds (arXiv, journal RSS, etc.), downloads
PDFs, and deposits them in data/raw/<subject>/ for inbox_daemon to route to
doc_parser automatically.

Config (academic_edu_assistant/config/config.yaml):
    rss:
      feeds:
        - name: "cs.AI"
          url: "https://arxiv.org/rss/cs.AI"
          subject: "ComputerScience"
          max_items: 5
        - name: "Nature ML"
          url: "https://www.nature.com/natmachintell.rss"
          subject: "NaturePapers"
          max_items: 3
      download_pdfs: true
      dedupe_file: "state/rss_seen.jsonl"

CLI:
    python p00_rss_ingest.py [--subject SUBJECT] [--dry-run]

Requirements:
    pip install feedparser requests
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time

# Core Bootstrap
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))
from core.utils.bootstrap import ensure_core_path as _bootstrap

_bootstrap(__file__)

from core import PipelineBase


class Phase0RSSIngest(PipelineBase):
    """Phase 0: Proactive RSS/Atom feed ingestion."""

    def __init__(self) -> None:
        super().__init__(
            phase_key="p0",
            phase_name="RSS 主動擷取",
            skill_name="academic_edu_assistant",
        )
        rss_cfg = self.config_manager.get_section("rss") or {}
        self.feeds: list = rss_cfg.get("feeds", [])
        self.download_pdfs: bool = rss_cfg.get("download_pdfs", True)
        self.max_items_default: int = rss_cfg.get("max_items_default", 5)
        self.dedupe_path: str = os.path.join(
            self.base_dir,
            rss_cfg.get("dedupe_file", "state/rss_seen.jsonl"),
        )
        os.makedirs(os.path.dirname(self.dedupe_path), exist_ok=True)
        self._seen_ids: set[str] = self._load_seen()

    # ── Deduplication ─────────────────────────────────────────────────────

    def _load_seen(self) -> set:
        seen: set[str] = set()
        if not os.path.exists(self.dedupe_path):
            return seen
        try:
            with open(self.dedupe_path, encoding="utf-8") as f:
                for line in f:
                    rec = json.loads(line.strip())
                    seen.add(rec.get("id", ""))
        except Exception:
            pass
        return seen

    def _mark_seen(self, entry_id: str, title: str) -> None:
        with open(self.dedupe_path, "a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "id": entry_id,
                        "title": title,
                        "seen_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
        self._seen_ids.add(entry_id)

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _entry_id(entry) -> str:
        """Stable ID: prefer entry.id, fall back to URL hash."""
        raw = getattr(entry, "id", None) or getattr(entry, "link", "") or ""
        return hashlib.sha256(raw.encode()).hexdigest()[:16] if raw else ""

    @staticmethod
    def _find_pdf_link(entry) -> str | None:
        """Try to locate a direct PDF link in entry.links."""
        for link in getattr(entry, "links", []):
            href = link.get("href", "")
            ltype = link.get("type", "")
            if "pdf" in ltype or href.endswith(".pdf") or "/pdf/" in href:
                return href
        # arXiv: convert abs URL to PDF URL
        link = getattr(entry, "link", "")
        if "arxiv.org/abs/" in link:
            return link.replace("/abs/", "/pdf/") + ".pdf"
        return None

    def _download_pdf(self, url: str, dest_dir: str, title: str, dry_run: bool) -> str | None:
        """Download a PDF to dest_dir; return local path or None on failure."""
        safe_name = "".join(c if c.isalnum() or c in "-_ " else "_" for c in title)[:80]
        filename = f"{safe_name}.pdf"
        dest_path = os.path.join(dest_dir, filename)

        if os.path.exists(dest_path):
            self.info(f"   \u23ed\ufe0f  \u5df2\u5b58\u5728\uff0c\u8df3\u904e: {filename}")
            return dest_path

        if dry_run:
            self.info(f"   [dry-run] \u5c07\u4e0b\u8f09: {url} \u2192 {dest_path}")
            return None

        try:
            import requests

            self.info(f"   \u2b07\ufe0f  \u4e0b\u8f09 PDF: {url}")
            resp = requests.get(url, timeout=60, headers={"User-Agent": "OpenClaw/1.0"})
            resp.raise_for_status()
            os.makedirs(dest_dir, exist_ok=True)
            with open(dest_path, "wb") as f:
                f.write(resp.content)
            self.info(f"   \u2705 \u5132\u5b58: {dest_path}")
            return dest_path
        except Exception as exc:
            self.warning(f"   \u26a0\ufe0f  PDF \u4e0b\u8f09\u5931\u6557 ({url}): {exc}")
            return None

    # ── Main ──────────────────────────────────────────────────────────────

    def run(
        self,
        force: bool = False,
        subject: str | None = None,
        dry_run: bool = False,
        **_kwargs,
    ) -> None:
        try:
            import feedparser  # type: ignore[import]
        except ImportError:
            self.error(
                "\u274c feedparser \u672a\u5b89\u88dd\u3002\u8acb\u57f7\u884c: pip install feedparser"
            )
            return

        if not self.feeds:
            self.warning(
                "\u26a0\ufe0f  config.yaml \u4e2d\u7684 rss.feeds \u70ba\u7a7a\uff0c\u7121\u4efb\u52d9\u53ef\u57f7\u884c\u3002"
            )
            return

        self.info(
            f"\U0001f4e1 \u555f\u52d5 Phase 0\uff1aRSS \u4e3b\u52d5\u64f7\u53d6 ({len(self.feeds)} \u500b Feed)"
        )
        total_new = 0

        for feed_cfg in self.feeds:
            feed_subject = feed_cfg.get("subject", "Default")
            if subject and feed_subject != subject:
                continue

            feed_url: str = feed_cfg.get("url", "")
            feed_name: str = feed_cfg.get("name", feed_url)
            max_items: int = feed_cfg.get("max_items", self.max_items_default)

            if not feed_url:
                self.warning(
                    f"\u26a0\ufe0f  Feed '{feed_name}' \u7f3a\u5c11 url\uff0c\u8df3\u904e\u3002"
                )
                continue

            self.info(f"\n\U0001f4f0 \u8655\u7406 Feed: [{feed_name}] {feed_url}")
            pbar, stop_tick, t = self.create_spinner(f"Fetch {feed_name}")
            try:
                parsed = feedparser.parse(feed_url)
            finally:
                self.finish_spinner(pbar, stop_tick, t)

            if parsed.bozo and not parsed.entries:
                self.warning(
                    f"\u26a0\ufe0f  Feed \u89e3\u6790\u5931\u6557: {parsed.bozo_exception}"
                )
                continue

            entries = parsed.entries[:max_items]
            self.info(f"   \U0001f4cb {len(entries)} \u7bc7\u6587\u7ae0 (max={max_items})")

            raw_inbox = os.path.join(
                os.environ.get(
                    "WORKSPACE_DIR", os.path.abspath(os.path.join(self.base_dir, "..", ".."))
                ),
                "data",
                "raw",
                feed_subject,
            )

            for entry in entries:
                entry_id = self._entry_id(entry)
                title = getattr(entry, "title", "untitled")

                if not force and entry_id in self._seen_ids:
                    self.info(
                        f"   \u23ed\ufe0f  \u8df3\u904e\uff08\u5df2\u63a1\u96c6\uff09: {title[:60]}"
                    )
                    continue

                self.info(f"   \U0001f4f0 \u65b0\u6587\u7ae0: {title[:70]}")

                if self.download_pdfs:
                    pdf_url = self._find_pdf_link(entry)
                    if pdf_url:
                        local = self._download_pdf(pdf_url, raw_inbox, title, dry_run)
                        if local:
                            total_new += 1
                    else:
                        self.info(
                            "   \u2139\ufe0f  \u7121 PDF \u9023\u7d50\uff0c\u8df3\u904e\u4e0b\u8f09\u3002"
                        )

                if not dry_run:
                    self._mark_seen(entry_id, title)

        self.info(
            f"\n\u2728 RSS \u64f7\u53d6\u5b8c\u6210\uff01\u65b0\u589e {total_new} \u4efd PDF \u81f3\u6536\u4ef6\u533a\u3002"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Open Claw RSS Ingest (Phase 0)")
    parser.add_argument("--subject", help="\u50c5\u8655\u7406\u6307\u5b9a\u79d1\u76ee")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="\u8a66\u884c\u6a21\u5f0f\uff0c\u4e0d\u5be6\u969b\u4e0b\u8f09",
    )
    parser.add_argument("--force", action="store_true", help="\u5ffd\u7565\u91cd\u8907\u6aa2\u6e2c")
    args = parser.parse_args()
    Phase0RSSIngest().run(subject=args.subject, dry_run=args.dry_run, force=args.force)


if __name__ == "__main__":
    main()
