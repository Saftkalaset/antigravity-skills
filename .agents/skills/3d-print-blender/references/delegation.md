# External Hardware Research & Subagent Delegation

## 1. Hardware Research Workflow
When external hardware (phones, chargers, plugs, cables, mounts) must be modeled from URLs, photos, or spec sheets:
- Delegate the lookup and extraction to a `research` subagent using the `3d-print-spec-extractor` skill when available; otherwise execute the skill directly.
- Require the subagent to return only a concise **Mechanical Spec Sheet** (nominal mm dimensions, recommended radial/per-side clearances, and confidence levels).
- Log sources, nominal values, clearances, and CAD targets into the `Dimensions & Clearances` table in `PROJECT.md`. Treat image-derived numbers as estimates and prefer a compact fit-test coupon (e.g., a $5\text{ mm}$ ring slice) for critical press/slip fits.

## 2. Subagent Delegation Boundaries (Context Hygiene)
- **Delegate to Subagent:**
  - Web scraping, teardown lookups, datasheet cross-referencing, and pixel-to-mm photogrammetry scaling.
  - Exploratory math or standalone curve-fitting calculations that do not require the active Blender viewport.
- **Main Agent Focus:**
  - Receives finalized parameters and updates `PROJECT.md` / `LOG.md`.
  - Executes live modeling, auditing, and exporting in the active Blender MCP session using [`scripts/lib.py`](../scripts/lib.py).
  - Never run competing headless `blender -b` processes against the same `.blend` file that is open in the live MCP session.
