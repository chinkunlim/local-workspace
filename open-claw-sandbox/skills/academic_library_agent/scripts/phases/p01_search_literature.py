import asyncio
import json
import os

from core import PhaseBase, SessionState
from core.utils.playwright_utils import get_clean_text_snapshot, get_persistent_context


class Phase1SearchLiterature(PhaseBase):
    def __init__(self) -> None:
        super().__init__(
            phase_key="p01_search_literature",
            phase_name="Institutional Literature Search",
            skill_name="academic_library_agent",
        )

    async def _search_sciencedirect(self, query: str) -> str:
        async with get_persistent_context(headless=True) as context:
            page = await context.new_page()

            # Navigate to ScienceDirect Search
            print(f"🔍 正在搜尋 ScienceDirect: '{query}'")
            try:
                # Using ScienceDirect advanced search URL pattern
                search_url = f"https://www.sciencedirect.com/search?qs={query.replace(' ', '%20')}"
                await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)

                # Wait for search results
                await page.wait_for_selector(".result-item-content", timeout=15000)

                # Click the first result
                first_result = await page.query_selector(".result-item-content h2 a")
                if first_result:
                    print("✅ 找到相關文獻，正在提取內容快照...")
                    await first_result.click()
                    await page.wait_for_load_state("domcontentloaded", timeout=60000)

                    # Ensure article body is loaded
                    await page.wait_for_selector("#body", timeout=15000)

                    # Extract clean text snapshot
                    snapshot = await get_clean_text_snapshot(page)
                    return snapshot
                else:
                    return "沒有找到相關文獻。"
            except Exception as e:
                print(f"⚠️ Playwright 搜尋失敗或超時: {e}")
                return f"搜尋失敗: {e}"

    def run(self, force: bool = False, **kwargs) -> None:
        input_dir = self.phase_dirs["input"]
        evidence_dir = os.path.join(self.base_dir, "data", "academic_library_agent", "evidence")
        os.makedirs(evidence_dir, exist_ok=True)

        # We expect a claims.json file from student_researcher P01
        for root, _, files in os.walk(input_dir):
            for file in files:
                if not file.endswith(".json"):
                    continue

                filepath = os.path.join(root, file)
                print(f"\n📂 處理斷言檔案: {file}")

                with open(filepath, encoding="utf-8") as f:
                    try:
                        claims = json.load(f)
                    except json.JSONDecodeError:
                        print("❌ 無法解析 JSON")
                        continue

                results = []
                for claim in claims.get("claims", []):
                    query = claim.get("search_query", "")
                    if not query:
                        continue

                    # Run Playwright search synchronously via asyncio.run
                    snapshot = asyncio.run(self._search_sciencedirect(query))

                    # Save local evidence
                    evidence_filename = f"evidence_{query.replace(' ', '_')[:30]}.txt"
                    evidence_path = os.path.join(evidence_dir, evidence_filename)
                    with open(evidence_path, "w", encoding="utf-8") as ef:
                        ef.write(snapshot)

                    results.append(
                        {
                            "claim_id": claim.get("id"),
                            "query": query,
                            "evidence_file": evidence_path,
                            "snapshot": snapshot[
                                :2000
                            ],  # Pass truncated snapshot to next phase to save tokens
                        }
                    )

                # Write results to output directory to be picked up by gemini_verifier_agent
                out_path = self._get_output_path(filepath, ext=".json")
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump({"verified_claims": results}, f, ensure_ascii=False, indent=2)

                print(f"✅ 文獻搜尋完成，輸出至: {out_path}")

        # Register the physical files for state manager
        self.state_manager.sync_physical_files()
