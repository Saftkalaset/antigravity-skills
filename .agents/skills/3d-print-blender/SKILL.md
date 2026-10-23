---
name: 3d-print-blender
description: >-
  Guide for designing, validating, and exporting 3D printable models in Blender. Use whenever designing, creating, modifying, or checking a model for 3D printing.
---

# Blender 3D Printing Workflow

## 1. Session Bootstrap & Helper Library (`scripts/lib.py`)
At the start of a Blender MCP session, load [`scripts/lib.py`](scripts/lib.py) once and call `open_project(project_dir)` to open `<Project_Name>.blend` (if not already open), verify environment settings, and print cached specs and scene objects in a single round-trip:
```python
exec(open('<skill-directory>/scripts/lib.py').read(), globals())
open_project('/home/john/Documents/Blender files/<Project Name>')
```
- **Quiet Output & Diagnostic Discipline:** Never print per-vertex, per-face, or raw coordinate loops in MCP calls. Printing raw coordinate arrays floods context, burns tokens, and degrades attention. Use `quiet_summary(coords, label=...)` or `quiet_inspect(obj, z_range=..., min_area=...)` to print a single 1-line statistical digest (`count`, `X/Y/Z` spans, `centroid`). All `lib.py` functions return a dictionary and automatically register themselves (plus `bmesh`, `json`, `math`, `os`, `re`) in Python `builtins` so they stay in scope across all subsequent `execute_blender_code` calls in the session without re-loading `lib.py`.
  - **Execution Scope Invariant:** Python `builtins` persist across MCP calls, but local script variables (e.g. `pos = ...`) do NOT. Always re-acquire objects via `bpy.data.objects["..."]` or store session references on `builtins` / `scene` to avoid `NameError` roundtrips.
- **Core Helpers Available After Bootstrap:**
  - `open_project(project_dir)` / `check_env()` — opens the root `.blend` if needed, verifies metric mm (`0.001` scale), `.3mf` exporter, 3D-Print Toolbox, auto-loads `parametric_recipe.py` functions into `builtins`, and prints cached `scene["cad_specs"]` plus collection bounding boxes (`world_bbox(obj)`), modifiers, and `cutter_def` spans.
  - `quiet_summary(coords, label="POINTS")` & `quiet_inspect(obj, z_range=None, min_area=None)` — 1-line statistical digest (`n`, `X/Y/Z` min/max, `centroid`) for point/vertex/face groups; replaces verbose print loops in exploratory scripts.
  - `save_specs(target=None, **specs)` / `get_specs(target=None)` — persists and retrieves extracted reference coordinates, port/vent bounds, and design parameters in `scene["cad_specs"]` so follow-up sessions never re-raycast heavy reference meshes.
  - `save_recipe(code_str)` / `get_recipe()` — stores and retrieves the parametric generator script inside `bpy.data.texts["parametric_recipe.py"]` in the `.blend` file (and registers its functions in `builtins`) so future sessions can tweak parameters without reverse-engineering BMesh vertices.
  - `make_keepout_box(...)` / `make_keepout_cylinder(...)` — creates lightweight `KeepOut_*` wireframe volumes in `3_References` for ports, fans, cables, and airflow windows.
  - `ensure_collections()` / `hide_cutters()` — maintains the 3 canonical collections and enforces the depsgraph visibility rule.
  - `inspect_ref(obj)` — world-space bounds, shell count, and dominant horizontal contact planes for reference meshes in one call (includes `bm.normal_update()`).
  - `cleanup_mesh(obj, dist=0.01)` — merges doubles, dissolves degenerate zero-area faces/edges, removes loose geometry, and recalculates normals.
  - `audit(obj, overhang_deg=45.0)` & `toolbox_check(obj)` — evaluates the modifier-applied mesh in world space to report `size`, `volume_cm3`, `shells`, `non_manifold`, `zero_area`, `overhang_mm2`, `min_wall_mm` + `min_wall_at` (opposing-normal raycast wall thickness check excluding 1-ring bevel neighbors), `keepout_hits` (automated BVH collision check against all `KeepOut_*` objects), and 3D-Print Toolbox checks.
  - `audit_cantilever(obj, axis='X', ...)` & `check_insertion(part, moving_obj, path_vec)` — **opt-in** local solvers for load-bearing brackets (exact 3D cross-sectional $I(s)$, $Z_s(s)$, peak stress, and Euler-Bernoulli tip sag) and tight enclosures (swept-path BVH collision check); see [`references/booleans.md`](references/booleans.md).
  - `make_extruded_cutter(...)`, `set_extruded_profile(...)`, `rect_2d(...)`, `rounded_poly_2d(...)`, `make_cylinder_cutter(...)`, `make_slotted_cylinder_cutter(...)`, `add_live_boolean(target, cutter)` — builds or updates watertight single-shell cutters (`'X'`, `'Y'`, or `'Z'` extrusion, with auto-cached `obj["cutter_def"]` and uniform or per-corner fillet radii) in `2_Boolean_Cutters` and attaches live `BOOLEAN` (`solver='MANIFOLD'`) modifiers.
  - `apply_modifiers(obj)` — context-independent depsgraph bake (use only when freezing topology before final mesh-level bevels).
  - `snapshot_and_export(project_dir, obj, project_name=None, suffix="", log_msg=None)` — audits `obj` (blocking export if `non_manifold > 0` or `shells != 1`), saves `history/<name>_v<N>.blend`, saves root `<Project_Name>.blend`, exports a temporary baked copy to both root `<Project_Name>.3mf` and `history/<name>_v<N>.3mf`, and optionally appends `log_msg` to `LOG.md`.
  - `log(project_dir, text)` — appends one dated line to `LOG.md`.

## 2. Scene Hierarchy & Invariants
- **Units:** Metric, millimeters (`scale_length = 0.001`). Never silently rescale an existing project.
- **Viewport Verification:** Never spawn Camera or Light objects. Use `look` (`{"mode": "angles", "target": ["<object_name>"]}`) when inspecting visual geometry. Note that `look` frames `target` but draws all visible scene objects; when inspecting internal features occluded by an opaque reference mesh, pass `shading="xray"` to `look` or toggle `ref.hide_set(True)` inside the preceding `execute_blender_code` call.
- **Canonical Collections:**
  - `1_Printable_Parts` (visible): Final printable objects only.
  - `2_Boolean_Cutters` (`hide_set(True)`, `hide_viewport = False`): Live boolean cutter meshes. **Never set `hide_viewport = True`** on cutters, as that disables them in Blender's evaluated dependency graph and causes boolean modifiers to silently skip.
  - `3_References` (visible/toggleable): Non-printable hardware mocks, 3D scans, and `KeepOut_*` wireframe clearance volumes (`display_type = 'WIRE'`, `hide_render = True`).
- **In-File Spec & Recipe Persistence:** Whenever reference dimensions, port/vent envelopes, or overhang steps are extracted from a reference mesh, save them immediately via `save_specs()` and `KeepOut_*` primitives, and store parametric profile scripts via `save_recipe()`, so future sessions read `open_project()` / `get_recipe()` in one call instead of running exploratory raycast scripts.
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
