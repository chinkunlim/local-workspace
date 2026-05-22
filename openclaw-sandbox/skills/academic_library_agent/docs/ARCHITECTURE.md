# ARCHITECTURE.md — academic_library_agent Skill

> **Version**: V1.0 | **Last Updated**: 2026-05-23

## 1. Role

`academic_library_agent` is a **Playwright-powered browser automation skill** that retrieves academic paper content from paywalled databases on behalf of `student_researcher`. It is a **sub-skill** — it is never invoked directly by `RouterAgent` or `inbox_daemon`. Only `student_researcher` calls it.

---

## 2. Pipeline Position

```
student_researcher P01 (claim list)
        │
        ▼
academic_library_agent
        │
        ├──▶ Query: Google Scholar, Elsevier, Wiley, ScienceDirect
        │
        ├──▶ For each result: Playwright persistent context (bypass login walls)
        │         └──▶ Extract: abstract + full text (if accessible) + PDF snapshot
        │
        └──▶ Output: data/student_researcher/evidence/<Subject>/
                     ├── <paper_id>.pdf
                     ├── <paper_id>_abstract.txt
                     └── <paper_id>_fulltext.md (if extracted)
```

---

## 3. Retrieval Strategy

| Priority | Strategy | Notes |
|:---|:---|:---|
| 1 | Open-access PDF (arXiv, PubMed Central, institutional OA) | Direct download, no auth required |
| 2 | Playwright authenticated session (university library proxy) | Requires `LIBRARY_PROXY_URL` env var |
| 3 | Abstract only | When full text inaccessible — downstream `gemini_verifier_agent` uses abstract |
| 4 | DOI metadata only | Minimum useful output — records existence but not content |

---

## 4. Security Constraints

- **No credential storage in code**: Library proxy credentials live in `.env` only (`LIBRARY_PROXY_URL`, `LIBRARY_PROXY_USER`, `LIBRARY_PROXY_PASS`).
- **Playwright persistent context**: Session cookies stored in `data/academic_library_agent/browser_context/`. Never commit this directory.
- **Rate limiting**: 3-second minimum delay between requests per domain. Configurable in `config.yaml` (`scraping.request_delay_seconds`).
- **robots.txt compliance**: Skip URLs where robots.txt disallows scraping.

---

## 5. Core Framework Dependencies

| Module | Usage |
|:---|:---|
| `core.orchestration.pipeline_base.PipelineBase` | Phase class inheritance |
| `core.utils.atomic_writer.AtomicWriter` | Crash-safe PDF/text writes |
| `playwright.async_api` | Browser automation (persistent context) |

---

## 6. Key Invariants

1. **Sub-skill only**: Never add `academic_library_agent` to `RouterAgent._DEFAULT_CHAINS` or `inbox_config.json` routing rules.
2. **Evidence is immutable**: Once a paper snapshot is written to `evidence/`, it is never overwritten. Re-runs skip existing evidence files.
3. **Rate limiting is non-negotiable**: Never remove the inter-request delay — academic databases actively block scrapers.
4. **Structured logging only**: Use `self.info()`, `self.error()`, `self.warning()` — no bare `print()`.
