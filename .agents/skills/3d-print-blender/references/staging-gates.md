# Incremental Viewport Staging vs. Batched Iterative Edits

Choose the execution cadence that matches whether you are building a **new part from scratch (Greenfield)** or **modifying an existing parametric/boolean model (Iterative Edit)**:

## 1. Greenfield Builds (New Part from Scratch — 4 Stages)
When developing a brand-new part or complex profile for the first time, break work into 4 distinct stages committed to the live Blender session so base topology is verified before booleans are attached:

1. **Stage 1 — Skeleton, Spec Extraction & Keep-Out Zones:** Extract reference bounds/features once, persist them in the `.blend` file via `save_specs()`, and create `KeepOut_*` wireframe volumes (`make_keepout_box`, `make_keepout_cylinder`) in `3_References`.
   - *Self-Evaluation Gate:* Verify bounding dimensions, clearances, print orientation, and nominal root Z-layer peel stress ($\sigma_z = M / Z_s \le 3.0\text{ MPa}$) before generating surfaces.
2. **Stage 2 — Primary Solid Body:** Loft, sweep, or extrude the uncut base volume in `1_Printable_Parts`.
   - *Self-Evaluation Gate:* Confirm volume continuity, overall envelope, flat build-plate landing, and `audit(obj)` (`shells=1, nonmanifold=0`).
3. **Stage 3 — Features & Live Boolean Cuts:** Create single-shell cutters in `2_Boolean_Cutters` (`hide_cutters()`) and attach them via `add_live_boolean(obj, cutter)`.
   - *Self-Evaluation Gate:* Run `audit(obj)` on the evaluated mesh to confirm `nonmanifold=0`, `zero_area=0`, and `keepout_hits=0`.
4. **Stage 4 — Refinement, Detailing & Export:** Apply edge bevels/fillets, run `look` to verify visually, and run `snapshot_and_export(project_dir, obj)`.

## 2. Iterative Edits (Modifying an Existing Model — Batched Execution)
When resuming a project or modifying an existing boolean/parametric model where the topology architecture is already established, **do not split edits into 4–5 micro-steps**:
1. **Single-Call Bootstrap & Spec Read:** Call `check_env()` and `get_specs()` in one script. If `scene["cad_specs"]` is already populated, **never re-run exploratory raycast/slice scripts** on heavy reference meshes.
2. **Batched Geometry Update + Audit:** Update the base profile and live boolean cutters, call `hide_cutters()`, and run `audit(obj)` + `toolbox_check(obj)` **in a single atomic `execute_blender_code` call**.
3. **Visual Check & Export:** Call `look` (`mode="angles"`) to verify the updated geometry, then run `snapshot_and_export()`.

## Execution Rules
- **Fail Fast:** If `audit(obj)` reports `nonmanifold > 0` or `keepout_hits` after a batched edit, disable boolean modifiers to isolate whether the base mesh or a specific cutter caused the issue.
- **Direct MCP Execution:** Always use the persistent Blender MCP session (`execute_blender_code`) and avoid spawning redundant headless `blender -b` processes.
