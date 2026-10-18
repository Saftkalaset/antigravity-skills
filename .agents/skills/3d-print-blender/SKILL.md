---
name: 3d-print-blender
description: >-
  Guide for designing, validating, and exporting 3D printable models in Blender. Use whenever designing, creating, modifying, or checking a model for 3D printing.
---

# Blender 3D Printing Workflow

## 1. Session Bootstrap & Helper Library (`scripts/lib.py`)
At the start of a Blender MCP session, load [`scripts/lib.py`](scripts/lib.py) once into the live global namespace:
```python
exec(open('<skill-directory>/scripts/lib.py').read(), globals())
check_env()
```
- **Quiet Output Rule:** Never print per-vertex or per-face debug lists in MCP calls. All `lib.py` functions print a single compact summary line and return a dictionary.
- **Core Helpers Available After Bootstrap:**
  - `check_env()` — verifies metric mm (`0.001` scale), `.3mf` exporter, and 3D-Print Toolbox.
  - `ensure_collections()` / `hide_cutters()` — maintains the 3 canonical collections and enforces the depsgraph visibility rule.
  - `inspect_ref(obj)` — world-space bounds, shell count, and dominant horizontal contact planes for reference meshes in one call (includes `bm.normal_update()`).
  - `cleanup_mesh(obj, dist=0.01)` — merges doubles, dissolves degenerate zero-area faces/edges, removes loose geometry, and recalculates normals.
  - `audit(obj, overhang_deg=45.0)` & `toolbox_check(obj)` — evaluates the modifier-applied mesh in world space to report `size`, `volume_cm3`, `shells`, `non_manifold`, `zero_area`, `overhang_mm2`, and 3D-Print Toolbox checks.
  - `make_extruded_cutter(...)`, `make_cylinder_cutter(...)`, `add_live_boolean(target, cutter)` — builds watertight single-shell cutters in `2_Boolean_Cutters` and attaches live `BOOLEAN` (`solver='MANIFOLD'`) modifiers.
  - `apply_modifiers(obj)` — context-independent depsgraph bake (use only when freezing topology before final mesh-level bevels).
  - `snapshot_and_export(project_dir, obj, project_name=None, suffix="")` — saves `history/<name>_v<N>.blend`, saves root `<Project_Name>.blend`, and exports a temporary baked copy to both root `<Project_Name>.3mf` and `history/<name>_v<N>.3mf`.
  - `log(project_dir, text)` — appends one dated line to `LOG.md`.

## 2. Scene Hierarchy & Invariants
- **Units:** Metric, millimeters (`scale_length = 0.001`). Never silently rescale an existing project.
- **Viewport Verification:** Never spawn Camera or Light objects. Use `look` (`{"mode": "angles", "target": "<object_name>"}`) when inspecting visual geometry.
- **Canonical Collections:**
  - `1_Printable_Parts` (visible): Final printable objects only.
  - `2_Boolean_Cutters` (`hide_set(True)`, `hide_viewport = False`): Live boolean cutter meshes. **Never set `hide_viewport = True`** on cutters, as that disables them in Blender's evaluated dependency graph and causes boolean modifiers to silently skip.
  - `3_References` (visible/toggleable): Non-printable hardware mocks and 3D scans.
- **Coordinate Origin Invariant:** Keep every object's local mesh centered at `(0, 0, 0)` on its functional axis and position it via `obj.location` / `obj.rotation_euler` (no mixed baked + object offsets).
- **Orphan Cleanup:** Purge unused meshes/data-blocks with `bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)`.

## 3. Project Organization, Versioning & Blender 5.3 Compatibility
- **Project Root (`/home/john/Documents/Blender files/<Project Name>/`):**
  - `<Project_Name>.blend`: Single active working file at root so live MCP edits appear immediately in the user's open session.
  - `<Project_Name>.3mf`: Latest ready-to-slice export at root (always verify non-empty).
  - `PROJECT.md`: Concise (~45-line) current-state spec sheet initialized from [`resources/PROJECT_TEMPLATE.md`](resources/PROJECT_TEMPLATE.md). Do not rewrite `PROJECT.md` for historical logs.
  - `LOG.md`: Append-only chronological iteration and decision log (`log(project_dir, "vN: ...")`).
  - `history/<name>_v<N>.blend` & `.3mf`: Immutable milestone snapshots created via `snapshot_and_export()`.
- **Blender 5.3+ Projects Compatibility:**
  - Keep `<Project_Name>.blend` at the project root so Blender 5.3's `.blender_project/` directory sits alongside it and upward path-walking from `history/` resolves to the same project root.
  - Always use Blender project-relative paths (`//`) for any linked assets or textures.
  - `next_version()` matches `r"_v(\d+)\.(?:blend|3mf)$"` strictly so native `.blend1`/`.blend2` backups are never mistaken for version numbers.

## 4. Hardware Baseline: Prusa Core One (0.4mm Nozzle / PLA)
- **Walls & Minimum Features:** Multiples of `0.4 mm` (`>= 1.2 mm` / 3 perimeters minimum; `1.6 mm` / 4 perimeters for structural collars).
- **Clearances:** State clearances as **per-side (radial)** and **total (diametral)** (`ID = OD + 2c`). On the Prusa Core One in PLA, circular bores shrink by $\sim 0.15\text{–}0.20\text{ mm}$; use $+0.20\text{ mm}$ radial ($+0.40\text{ mm}$ diametral) for a snug locating slip fit, and print a quick ring coupon when nominal hardware dimensions have $> \pm 0.2\text{ mm}$ uncertainty.

## 5. On-Demand Reference Guides
Read these focused guides only when the task involves their topic:
- **Boolean Architecture, Mating Contours & 3D Scan Kinematics:** [`references/booleans.md`](references/booleans.md)
- **Overhang Rules, Build-Plate Bevels & Mesh Auditing:** [`references/overhang-audit.md`](references/overhang-audit.md)
- **4-Stage Incremental Viewport Staging & Gates:** [`references/staging-gates.md`](references/staging-gates.md)
- **External Hardware Research & Subagent Delegation:** [`references/delegation.md`](references/delegation.md)
