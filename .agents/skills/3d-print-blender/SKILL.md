---
name: 3d-print-blender
description: >-
  Guide for designing, validating, and exporting 3D printable models in Blender. Use whenever designing, creating, modifying, or checking a model for 3D printing.
---

# Blender 3D Printing Workflow

## 1. Scene & Setup
- **Units:** Metric, millimeters, 0.001 scale. Do not alter unit or grid settings.
- **Scene:** Inspect the current scene before acting. A new scene may be blank; when modifying an existing project, preserve and inspect its objects unless the user requested replacement.
- **Units:** Confirm the scene unit settings and object scale before modeling. Use millimeter design dimensions; do not silently rescale an existing project or change its unit/grid settings when that could change interpretation.
- **Verification:** Never spawn Camera or Light objects. If a Blender viewport inspection tool is available, use it to inspect the model from multiple angles; in Antigravity with the Blender MCP server, use `look` with `{"mode": "angles", "target": "<object_name>"}`.

### Tool Availability
- Use the persistent Blender MCP session when it is available (for example, Antigravity's `execute_blender_code`). Do not assume that a particular MCP server or tool is installed in every agent environment.
- If Blender MCP is unavailable, use another Blender access method only when the environment provides one. Otherwise, explain that modeling actions are blocked by the missing connection and provide the next setup step; do not claim to have edited or inspected a model.
- Apply the same rule to viewport inspection, mesh validation, and 3MF export: use the available tools and report which checks or outputs could not be performed.

### Canonical Scene Hierarchy & Origins
Organize every project into three top-level collections so the Outliner stays clean and modifiers remain easy to edit:
- **`1_Printable_Parts`** (visible): Only final printable objects (e.g., `positive_object`, `WedgePlug`).
- **`2_Boolean_Cutters`** (hidden via `hide_set(True)`): All boolean difference/union helper meshes.
- **`3_References`** (visible or toggleable): Consolidated multi-material reference models (`MiniPod_MK1_Reference`) and 3D scans (`mesh`).
- **Orphan Cleanup:** Delete superseded cutter objects (`negative_plane_*`, internal construction helpers) and run `bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)` when consolidating.
- **Depsgraph Visibility Rule (`hide_set` vs `hide_viewport`):** Always hide cutters or temporarily hidden references using `obj.hide_set(True)` while keeping `obj.hide_viewport = False`. Setting `hide_viewport = True` disables the object in Blender's evaluated dependency graph, which causes `evaluated_depsgraph_get()` to return unscaled coordinates and silently skips boolean modifiers referencing that object.
- **Coordinate Origin Invariant (No Double Offsets):** Never mix object-level `obj.location` offsets with baked world-space vertex offsets. Build every cutter and sub-part with its local mesh centered at `(0, 0, 0)` on its functional axis and position it using `obj.location` and `obj.rotation_euler`. Coaxial mating features (e.g., reference model, screw counterbore, locating pins) must share the exact same `obj.location` origin.

## 2. Project Organization & Versioning
- **Location:** All files must reside in `/home/john/Documents/Blender files/<Project Name>/`.
  Auto-create if missing (`os.makedirs(project_dir, exist_ok=True)`).
- **Working File (Root):** Always maintain a single active working file at root: `<Project_Name>.blend`. The user opens this file to see real-time edits in Blender via MCP without having to switch files or guess which version is newest.
- **History Archive (`history/`):** All earlier iterations and milestone backups reside in a `history/` subdirectory:
  `/home/john/Documents/Blender files/<Project Name>/history/<Project_Name>_v<N>[_<short_description>].blend`.
- **Version numbering:** Before saving, inspect existing history filenames and use the next unused positive integer. Never overwrite a snapshot. Use the same version number for a corresponding `.blend` and `.3mf`; keep the root working file and export as the current version without a suffix.
- **Snapshot Workflow:** Before starting a new iteration, making destructive changes, or reaching a milestone:
  1. Save a background copy to `history/` using `copy=True` (so the active session remains undisturbed):
     ```python
     import bpy, os
     project_dir = "/home/john/Documents/Blender files/<Project_Name>"
     history_dir = os.path.join(project_dir, "history")
     os.makedirs(history_dir, exist_ok=True)

     # Snapshot to history (does NOT change the active file path in Blender):
     bpy.ops.wm.save_as_mainfile(filepath=os.path.join(history_dir, "<Project_Name>_v<N>.blend"), copy=True)

     # Save current live working file at root:
     bpy.ops.wm.save_mainfile()
     ```
  2. The user's open Blender session continues working in `<Project_Name>.blend` in real time.

## 3. Project Documentation (`PROJECT.md`)
- **Requirement:** Every project directory must contain a living `PROJECT.md` file at `/home/john/Documents/Blender files/<Project Name>/PROJECT.md`.
- **Purpose:** Acts as the persistent source of truth across sessions, subagent lookups, and context compactions. Never rely purely on conversational memory for dimensions, clearances, or past design choices.
- **Template:** The canonical starter template is maintained in [`resources/PROJECT_TEMPLATE.md`](resources/PROJECT_TEMPLATE.md).
- **Workflow:**
  1. **Initialize:** When starting a new project (or opening an existing project lacking documentation), copy `resources/PROJECT_TEMPLATE.md` to `/home/john/Documents/Blender files/<Project Name>/PROJECT.md` and fill in initial goals.
  2. **Continuously Update:**
     - Record measurement sources and hardware references as soon as researched.
     - Document key design decisions and why rejected alternatives were abandoned.
     - Append each new milestone or iteration snapshot to the iteration log.

## 4. Modeling & Slicing Guidelines
- **Joining:** Prefer `bpy.ops.object.join()` over complex boolean modifiers. When booleans are required, use `solver='MANIFOLD'`.
- **Orientation:** Design in printable orientation to minimize overhangs (use 45° chamfers/gussets).
- **Validation:** Check mesh integrity using the 3D-Print Toolbox extension (`bl_ext.blender_org.print3d_toolbox`):
  ```python
  with bpy.context.temp_override(active_object=obj, selected_objects=[obj]):
      bpy.ops.mesh.print3d_check_all()
      for item in bpy.context.scene.print3d_toolbox.get_report():
          print(f"{item.name}: {item.value}")
  ```
- If the extension or expected API is unavailable, report that and perform available checks (dimensions, transforms, normals, connected components, and boundary/non-manifold edges). A successful toolbox run alone does not prove a part is printable. Report the checks actually completed; do not claim validation that was not performed.
- **Scope:** Slicing is handled by the user; focus on 3D modeling, tolerances, printable geometries, and clean mesh exports.

### Boolean Architecture, Mating Contours & Kinematics
- **Single-Shell Analytical Cutters:** Do not stack multiple overlapping boolean objects for a single compound feature (e.g., separate cylinder bore + box channel + dovetail slot). Instead, construct a single closed 2D keyhole/T-slot profile in `bmesh` and extrude it as one watertight cutter (`Cutter_<Feature>`). This prevents coplanar boolean slivers and allows adjusting the entire feature by moving one object.
- **Mirror Symmetric Cutters:** Always use a `Mirror` modifier (`mirror_object=<Main_Part>`) on symmetric left/right features (`Cutter_<Feature>_Side`) rather than maintaining separate `_left` and `_right` meshes.
- **Mating Footprint Inset (Preventing Protruding Lips):** When designing a flat mounting deck under a curved or spherical product, do not size the deck to the product's outer silhouette. Wrap the contour tightly around the actual fastener/locating-pin envelope and inset the perimeter $3\text{–}8\text{ mm}$ inside the product's flat bottom contact ring so no lip protrudes beneath the curved body.
- **Variable Thickness Optimization:** Match wall/slab thickness to the local bending moment: keep lightly loaded perimeters slim and ramp thickness upward (where clearance permits) across high-stress cantilever necks and clamping blocks.
- **3D Scan Alignment & Insertion Kinematics:**
  - When aligning to a 3D scan, fit analytical geometry (e.g., least-squares 3D centerlines across scanned rod/surface vertices at the mating plane) to extract true symmetric spans and compound 3D slopes (`dX/dZ`, `dY/dZ`).
  - Verify physical insertion kinematics: ensure hooked entry channels can clear fixed multi-rod/multi-pin spans without undercut lockout, ensure through-slots extend completely past top/bottom surfaces (never leave a trapped blind skin), and verify self-locking wedge angles ($\theta < \arctan(\mu)$, typically $5^\circ\text{–}8^\circ$ with $0.15\text{–}0.25\text{ mm}$ per-side clearance).
- **Support-Free Overhang & Build-Plate Bevel Audit:**
  - Avoid $45^\circ$ bottom chamfers starting directly at the build plate ($Z = Z_{\min}$), which are prone to upward perimeter curling on the first 10–15 layers; use steeper **$\le 30^\circ\text{–}35^\circ$ from vertical** ($55^\circ\text{–}60^\circ$ from horizontal) bottom bevels computed along the continuous 2D perimeter normal.
  - On secondary parts (such as locking wedges or clips with grip tabs), chamfer overhanging flanges at $\le 35^\circ$ from vertical so they print support-free.
  - Alongside `print3d_check_all()`, run an evaluated BMesh audit on every printable part to confirm **0 non-manifold edges, 0 zero-area sliver faces, and $0.0\text{ mm}^2$ of unintentional overhangs $> 45^\circ$ from vertical**:
    ```python
    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_obj = obj.evaluated_get(depsgraph)
    bm = bmesh.new()
    bm.from_mesh(eval_obj.to_mesh())
    bm.transform(obj.matrix_world)
    z_min = min(v.co.z for v in bm.verts)
    non_manifold = [e for e in bm.edges if not e.is_manifold]
    zero_faces = [f for f in bm.faces if f.calc_area() < 1e-6]
    steep_overhangs = [
        f for f in bm.faces
        if f.calc_area() >= 1e-4
        and not (abs(f.calc_center_median().z - z_min) < 0.05 and f.normal.z < -0.99)
        and f.normal.z < -0.7071  # > 45 deg from vertical
    ]
    ```

### Incremental Viewport Staging & Self-Evaluation Gates
- When developing new shapes, major redesigns, or complex profiles, **never execute everything in a single monolithic script** (derivation + extrusion + booleans + bevels + materials).
- Break work into distinct, visible stages committed to Blender, with an **explicit evaluation gate** at each step:
  1. **Stage 1: Skeleton & Guide Constraints:** Add reference wireframes, guide curves, or bounding boxes (e.g. `Guide_SpineCurve`, contact planes).
     - *Agent Self-Evaluation:* Verify bounding dimensions, clearances, tangency, and alignment against `PROJECT.md` specs *before* generating surfaces. If alignment is off, adjust the curve immediately.
     - *User Checkpoint:* User can visually confirm the profile/tilt in the Blender viewport in seconds and course-correct early before destructive modeling begins.
  2. **Stage 2: Primary Solid Body:** Loft, sweep, or extrude the un-cut base volume.
     - *Agent Self-Evaluation:* Confirm volume continuity, overall envelope, and base stability.
  3. **Stage 3: Features & Boolean Cuts:** Apply shelf pockets, cable cutouts, and collar clearances. Keep cutter objects in a `_cutters` collection for inspection before final boolean execution.
     - *Agent Self-Evaluation:* Verify clearance gaps (e.g. collar slip fit, cable pass-through) and verify no unintended non-manifold geometry or inverted normals resulted from booleans.
  4. **Stage 4: Refinement, Detailing & Export:** Apply edge bevels/fillets, materials, and 3MF export.
     - *Agent Self-Evaluation:* Run 3D-Print Toolbox (`print3d_check_all()`) to guarantee 0 non-manifold edges and single-shell manifold status.
- **Autonomous Progression Rule:** Commit each stage to the Blender viewport so the user has full live visibility. Do not wait for approval at every stage unless the user requested checkpoints; pause if a self-evaluation gate fails or a material design choice is ambiguous. The user can intervene at any time.
- **Fail Fast / Course-Correction Rule:** Never build Stage N+1 on an unverified Stage N. If intermediate checks fail or the user flags a concern, reconsider and refine the current stage immediately.
- **Direct MCP Execution:** When the persistent Blender MCP server is available, execute operations directly in the active session and avoid spawning redundant headless `blender -b` background processes (which repeatedly register and unregister addons).

## 5. Exporting (3MF)
- **Format:** Export as **3MF** into the project directory (do not export STL).
- **Primary Export:** Export the latest model to the root folder as `<Project_Name>.3mf` for immediate slicing.
- **Versioned Backup:** Also export a snapshot copy to `history/<Project_Name>_v<N>[_<Part_Name>].3mf`.
- **Export Command:** Use `bpy.context.temp_override`; confirm the operator exists in the installed Blender version and verify that the resulting file exists and is non-empty:
  ```python
  with bpy.context.temp_override(active_object=obj, selected_objects=[obj]):
      bpy.ops.export_mesh.threemf(filepath=os.path.join(project_dir, "<Project_Name>.3mf"), use_selection=True)
  ```

## 6. Hardware Profile: Prusa Core One (0.4mm Nozzle / PLA)
- **Nozzle:** 0.4mm. Walls must be multiples of 0.4mm (minimum 1.2mm / 3 perimeters). Avoid features < 0.4mm in X/Y.
- **Material (PLA):** Rigid but brittle. Thicken load-bearing features. Orient parts so layer lines run perpendicular to expected stress.
- **Tolerances:** Do not apply a universal fit tolerance. State whether clearance is per side/radial or total. For a round fit, radial clearance `c` adds `2c` to the hole diameter. Use the spec-extractor values only as starting estimates and prefer a printer/material-specific test coupon for critical fits.
- **Overhangs & Supports:** 45° overhangs print cleanly without support. When supports are required, PrusaSlicer organic supports will be used.

## 7. External Hardware Research & Dimensions (Subagent Delegation)
- When external hardware (e.g., phones, chargers, plugs, cables) needs to be modeled from URLs, photos, or spec sheets:
- Delegate this research to a `research` subagent using the `3d-print-spec-extractor` skill when one is available; otherwise research directly using that skill.
- The researcher handles source review, image measurements, and datasheet cross-checking.
- The subagent must return only a concise **Mechanical Spec Sheet** (nominal mm dimensions + recommended clearances).
- Treat image-derived numbers as estimates, not verified values; log sources, evidence type, uncertainty, and numbers into `PROJECT.md`.

### Subagent Delegation Boundaries (Context Hygiene)
- **Delegate to Subagent:**
  - Image analysis, pixel-to-mm scaling, and photogrammetry contour extraction when a suitable subagent is available; otherwise handle directly.
  - Exploratory math, spline fitting, and trial-and-error Python scripts tested in headless Blender (`blender -b`).
  - Scraped teardowns, spec sheets, and datasheet cross-referencing.
- **Main Agent Focus:**
  - Receives clean, finalized parameters or validated Blender Python snippets.
  - Executes live updates in the active Blender session via MCP.
  - Maintains user communication and updates `PROJECT.md`.
