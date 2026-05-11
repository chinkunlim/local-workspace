"""
core/utils/playwright_utils.py — Playwright Persistent Context Manager
=======================================================================
Shared utilities for all skills that drive web browsers via Playwright.

Uses Google Chrome with a single persistent user-data directory to
preserve login sessions (Google Gemini, NDHU OpenAthens, Elsevier).

Token optimization: get_clean_text_snapshot() strips DOM noise before
handing text to the LLM, minimizing token consumption.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import os

from playwright.async_api import BrowserContext, Page, async_playwright

# ---------------------------------------------------------------------------
# Profile directory — lives inside openclaw-sandbox/data/playwright_profile/
# ---------------------------------------------------------------------------

_WORKSPACE_DIR = os.environ.get(
    "WORKSPACE_DIR",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
)
PLAYWRIGHT_PROFILE_DIR = os.path.join(_WORKSPACE_DIR, "data", "playwright_profile")


# ---------------------------------------------------------------------------
# Persistent Context
# ---------------------------------------------------------------------------


@asynccontextmanager
async def get_persistent_context(
    headless: bool = True,
) -> AsyncIterator[BrowserContext]:
    """Yield a Playwright BrowserContext backed by Google Chrome.

    The persistent user-data directory preserves all login sessions
    (Google Gemini, NDHU OpenAthens, Elsevier) across runs. The caller
    is responsible for keeping ``PLAYWRIGHT_PROFILE_DIR`` seeded via
    ``ops/setup_playwright_auth.sh``.

    Args:
        headless: Run Chrome without a visible window. Set to False to
                  inspect or debug browser behaviour.

    Yields:
        BrowserContext — caller should open pages on this context.
    """
    os.makedirs(PLAYWRIGHT_PROFILE_DIR, exist_ok=True)

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=PLAYWRIGHT_PROFILE_DIR,
            channel="chrome",
            headless=headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )

        # Mask navigator.webdriver to reduce bot-detection fingerprinting.
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        try:
            yield context
        finally:
            await context.close()


# ---------------------------------------------------------------------------
# Token-efficient snapshot extraction
# ---------------------------------------------------------------------------


async def get_clean_text_snapshot(page: Page) -> str:
    """Return clean body text from a Playwright page, stripping DOM noise.

    Removes navbars, footers, ads, and scripts before extracting text.
    This typically reduces token consumption by ≥50% vs raw HTML.

    Args:
        page: An active Playwright Page object.

    Returns:
        Newline-joined plain text, whitespace-collapsed.
    """
    await page.evaluate(
        """() => {
            const sel = 'nav,footer,header,aside,.sidebar,.ad,.advertisement,'
                      + 'script,style,noscript,iframe,svg';
            document.querySelectorAll(sel).forEach(el => el.remove());
        }"""
    )
    text: str = await page.evaluate("document.body.innerText")
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return "\n".join(lines)
