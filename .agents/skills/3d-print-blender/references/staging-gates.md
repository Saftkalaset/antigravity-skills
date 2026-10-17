# Incremental Viewport Staging & Self-Evaluation Gates

When developing new shapes, major redesigns, or complex profiles, **never execute everything in a single monolithic script** (derivation + extrusion + booleans + bevels + materials). Break work into distinct, visible stages committed to the live Blender session, with an explicit self-evaluation gate at each step:

1. **Stage 1 — Skeleton & Guide Constraints:** Add reference wireframes, guide curves, or bounding boxes (e.g., `Guide_SpineCurve`, contact planes).
   - *Self-Evaluation Gate:* Verify bounding dimensions, clearances, tangency, and alignment against `PROJECT.md` specs *before* generating surfaces.
2. **Stage 2 — Primary Solid Body:** Loft, sweep, or extrude the un-cut base volume in `1_Printable_Parts`.
   - *Self-Evaluation Gate:* Confirm volume continuity, overall envelope, base stability (`Z_min = 0`), and `audit(obj)` (`shells=1, nonmanifold=0`).
3. **Stage 3 — Features & Live Boolean Cuts:** Create single-shell cutters in `2_Boolean_Cutters` (`hide_cutters()`) and attach them via `add_live_boolean(obj, cutter)`.
   - *Self-Evaluation Gate:* Verify clearance gaps (e.g., collar slip fit, cable pass-through) and run `audit(obj)` on the evaluated mesh to confirm `nonmanifold=0` and `zero_area=0`.
4. **Stage 4 — Refinement, Detailing & Export:** Apply edge bevels/fillets, materials, and run `snapshot_and_export(project_dir, obj)`.
   - *Self-Evaluation Gate:* Confirm final `audit(obj)` passes and `.3mf` files are non-empty.

## Execution Rules
- **Autonomous Progression:** Commit each stage to the live Blender viewport so the user has real-time visibility. Do not pause for approval at every stage unless requested; pause only when a gate fails or a design choice is ambiguous.
- **Fail Fast:** Never build Stage $N+1$ on an unverified Stage $N$.
- **Direct MCP Execution:** Always use the persistent Blender MCP session (`execute_blender_code`) and avoid spawning redundant headless `blender -b` processes.
