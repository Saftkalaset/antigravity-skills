# Boolean Architecture, Mating Contours & Kinematics

## 1. Single-Shell Analytical Cutters & Live Booleans
- **Single-Shell Cutters:** Never stack multiple overlapping boolean objects for a single compound feature (e.g., separate cylinder bore + box channel + dovetail slot). Construct one closed 2D keyhole/T-slot profile in `bmesh` and extrude it as a single watertight cutter (`Cutter_<Feature>`) via `make_extruded_cutter()` or `make_cylinder_cutter()` in [`scripts/lib.py`](../scripts/lib.py).
- **Live Boolean Modifiers:** Keep cutters as live `BOOLEAN` (`solver='MANIFOLD'`) modifiers on the main printable part (`add_live_boolean(target, cutter)`) rather than baking booleans destructively during iteration.
  - Resizing or moving a cutter in `2_Boolean_Cutters` immediately updates the evaluated mesh.
  - `snapshot_and_export()` automatically bakes a temporary copy for `.3mf` export while leaving modifiers live in the `.blend` file.
  - **Never call `bpy.ops.object.modifier_apply`:** It fails when `ViewLayer` selection context is missing. Always use `apply_modifiers(obj)` from `lib.py` (which bakes via `evaluated_depsgraph_get()`).
  - **`MANIFOLD` Solver Watertight Precondition:** Blender's `MANIFOLD` boolean solver silently acts as a no-op (returning the uncut mesh with no exception) if either the target mesh or the cutter has `nonmanifold > 0`. Always run `audit(base_obj)` to verify `nonmanifold == 0` on the uncut base mesh before attaching live booleans.
  - **Splitting N-gon Caps Before Partial BMesh Edits:** When replacing a regional section of a mesh in BMesh, never delete vertices that share a large planar n-gon cap without first splitting the cap across the boundary (`bmesh.ops.connect_vert_pair` or `bmesh.ops.bisect_plane`); otherwise the entire cap face is destroyed and makes the mesh non-manifold.
- **Mirror Symmetric Cutters:** Always use a `Mirror` modifier (`mirror_object=<Main_Part>`) on symmetric left/right features (`Cutter_<Feature>_Side`) rather than maintaining separate `_left` and `_right` meshes.

## 2. Mating Footprint & Structural Contours
- **Mating Footprint Inset (Preventing Protruding Lips):** When designing a flat mounting deck under a curved or spherical product, do not size the deck to the product's outer silhouette. Wrap the contour tightly around the actual fastener/locating-pin envelope and inset the perimeter $3\text{–}8\text{ mm}$ inside the product's flat bottom contact ring so no lip protrudes beneath the curved body.
- **Variable Thickness Optimization:** Match wall/slab thickness to the local bending moment: keep lightly loaded perimeters slim and ramp thickness upward (where clearance permits) across high-stress cantilever necks and clamping blocks. Use a wide lower root bridge where cantilever moment peaks and flare outward at $\le 43^\circ$ from vertical only at concentrated load points (e.g., J-hook crowns/jaws) rather than uniformly thickening the entire spine.

## 3. 3D Scan Alignment & Insertion Kinematics
- **Analytical Fit to Scans:** When aligning to a 3D scan, fit analytical geometry (e.g., least-squares 3D centerlines across scanned rod/surface vertices at the mating plane) to extract true symmetric spans and compound 3D slopes (`dX/dZ`, `dY/dZ`).
- **Insertion Kinematics:**
  - Ensure hooked entry channels can clear fixed multi-rod/multi-pin spans without undercut lockout.
  - Ensure through-slots extend completely past top/bottom surfaces (never leave a trapped blind skin).
  - Verify self-locking wedge angles ($\theta < \arctan(\mu)$, typically $5^\circ\text{–}8^\circ$ with $0.15\text{–}0.25\text{ mm}$ per-side clearance).
