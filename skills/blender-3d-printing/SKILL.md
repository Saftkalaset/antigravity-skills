---
name: blender-3d-printing
description: >-
  Guide for designing 3D printable models in Blender via the MCP server. Use whenever designing, creating, or modifying models for 3D printing.
---

# Blender 3D Printing Workflow

## 1. Scene & Setup
- **Units:** Metric, millimeters, 0.001 scale. Do not alter unit or grid settings.
- **Scene:** Starts blank. Do not assume any objects exist.
- **Verification:** Never spawn Camera or Light objects. Visually inspect using the `look` tool with `{"mode": "angles", "target": "<object_name>"}`.

## 2. Project Organization & Versioning
- **Location:** All files must reside in `/home/john/Documents/Blender files/<Project Name>/`.
  Auto-create if missing (`os.makedirs(project_dir, exist_ok=True)`).
- **Naming (`.blend`):** `<Project_Name>_v<N>[_<short_description>].blend` (e.g., `Desk_Mount_v1.blend`, `Desk_Mount_v2_wider_slot.blend`).
- **History:** Always increment to `v<N+1>` for new iterations or before destructive edits. Never overwrite earlier versions.
- **Save Command:**
  ```python
  import bpy, os
  project_dir = "/home/john/Documents/Blender files/<Project_Name>"
  os.makedirs(project_dir, exist_ok=True)
  bpy.ops.wm.save_as_mainfile(filepath=os.path.join(project_dir, "<Project_Name>_v1.blend"))
  ```

## 3. Modeling & Slicing Guidelines
- **Joining:** Prefer `bpy.ops.object.join()` over complex boolean modifiers.
- **Orientation:** Design in printable orientation to minimize overhangs (use 45° chamfers/gussets).
- **Validation:** Check mesh integrity using `bpy.ops.mesh.print3d_check_all` (`print3d_toolbox` extension).

## 4. Exporting (3MF)
- **Format:** Export as **3MF** into the project directory (do not export STL).
- **Naming (`.3mf`):** `<Project_Name>_v<N>[_<Part_Name>].3mf` (matches the source `.blend` version).
- **Export Command:**
  ```python
  bpy.ops.export_mesh.threemf(filepath=os.path.join(project_dir, "<Project_Name>_v1_Mount.3mf"), use_selection=True)
  ```

## 5. Hardware Profile: Prusa Core One (0.4mm Nozzle / PLA)
- **Nozzle:** 0.4mm. Walls must be multiples of 0.4mm (minimum 1.2mm / 3 perimeters). Avoid features < 0.4mm in X/Y.
- **Material (PLA):** Rigid but brittle. Thicken load-bearing features. Orient parts so layer lines run perpendicular to expected stress.
- **Tolerances:** 0.15mm – 0.2mm clearance for joints and interlocking fits.
- **Overhangs & Supports:** 45° overhangs print cleanly without support. When supports are required, PrusaSlicer organic supports will be used.
