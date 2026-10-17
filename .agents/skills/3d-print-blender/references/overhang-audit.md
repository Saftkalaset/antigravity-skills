# Overhangs, Build-Plate Bevels & Mesh Validation

## 1. Support-Free Overhangs & Build-Plate Bevels
- **Build-Plate Bevel Rule ($\le 30^\circ\text{–}35^\circ$ from vertical):** Avoid $45^\circ$ bottom chamfers starting directly at the build plate ($Z = Z_{\min}$), which are prone to upward perimeter curling on the first 10–15 layers. Use either a vertical landing band at $Z = 0$ or steeper **$\le 30^\circ\text{–}35^\circ$ from vertical** ($55^\circ\text{–}60^\circ$ from horizontal) bottom bevels computed along the continuous 2D perimeter normal.
- **Secondary Parts & Tabs:** On secondary parts (such as locking wedges or clips with grip tabs), chamfer overhanging flanges at $\le 35^\circ$ from vertical so they print support-free.
- **Horizontal Tunnels & Bridges:** For horizontal pass-through tunnels, either use a $45^\circ$ self-supporting peaked/teardrop roof for support-free printing, or use a rounded arch and explicitly document required slicer supports in `PROJECT.md`.

## 2. Evaluated Mesh Audit (`lib.audit`)
- Always validate the **evaluated** mesh (modifiers included) using `audit(obj)` from [`scripts/lib.py`](../scripts/lib.py):
  ```python
  exec(open('/home/john/.gemini/config/skills/3d-print-blender/scripts/lib.py').read())
  cleanup_mesh(obj)
  audit(obj, overhang_deg=45.0)
  ```
- **Pass Criteria:**
  - `shells == 1` (single connected manifold shell per printable part)
  - `nonmanifold == 0` (zero open boundary or non-manifold edges)
  - `zero_area == 0` (zero degenerate sliver faces $< 10^{-6}\text{ mm}^2$)
  - `overhang_mm2 == 0.0` (or matches only intentional supported regions listed in `PROJECT.md`)
- **3D-Print Toolbox (`bl_ext.blender_org.print3d_toolbox`):**
  ```python
  with bpy.context.temp_override(active_object=obj, selected_objects=[obj]):
      bpy.ops.mesh.print3d_check_all()
      for item in bpy.context.scene.print3d_toolbox.get_report():
          print(f"{item.name}: {item.value}")
  ```
  If the extension is unavailable, rely on `audit(obj)` and report the checks performed.
