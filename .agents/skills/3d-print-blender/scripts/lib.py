"""3d-print-blender helper library (run inside the live Blender session).

Load once per session (via execute_blender_code):
    exec(open('/home/john/.gemini/config/skills/3d-print-blender/scripts/lib.py').read())

Design rules:
  * Every function prints ONE compact summary and returns a dict. Never prints per-face lists.
  * Cutters are kept as live Boolean modifier targets; apply only on milestone/export.
  * Cutters are hidden with hide_set(True) and hide_viewport stays False (depsgraph rule).
"""
import bpy, bmesh, math, os, re
from mathutils import Vector

CANON = ("1_Printable_Parts", "2_Boolean_Cutters", "3_References")


# ----------------------------------------------------------------- environment
def check_env():
    """Verify units, exporter and 3D-Print Toolbox. Prints one line per problem."""
    u = bpy.context.scene.unit_settings
    r = {
        "blender": bpy.app.version_string,
        "units_ok": (u.system == 'METRIC' and abs(u.scale_length - 0.001) < 1e-6
                     and u.length_unit == 'MILLIMETERS'),
        "threemf_export": hasattr(bpy.ops.export_mesh, "threemf"),
        "print3d_toolbox": hasattr(bpy.ops.mesh, "print3d_check_all"),
        "filepath": bpy.data.filepath or "(unsaved)",
    }
    bad = [k for k in ("units_ok", "threemf_export", "print3d_toolbox") if not r[k]]
    print(f"ENV {r['blender']} | file={r['filepath']} | problems={bad or 'none'}")
    return r


def ensure_collections():
    """Create the three canonical top-level collections if missing."""
    root = bpy.context.scene.collection
    out = {}
    for n in CANON:
        c = bpy.data.collections.get(n) or bpy.data.collections.new(n)
        if c.name not in root.children:
            root.children.link(c)
        out[n] = c
    return out


def hide_cutters():
    """hide_set(True) on every object in 2_Boolean_Cutters; hide_viewport stays False."""
    c = bpy.data.collections.get("2_Boolean_Cutters")
    for o in (c.objects if c else []):
        o.hide_viewport = False
        o.hide_set(True)


# ------------------------------------------------------------------- mesh care
def cleanup_mesh(obj, dist=0.01):
    """Merge doubles, dissolve degenerate geometry, drop loose edges/verts, fix normals."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    before = (len(bm.verts), len(bm.faces))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=dist)
    bmesh.ops.dissolve_degenerate(bm, dist=dist, edges=bm.edges)
    loose_e = [e for e in bm.edges if not e.link_faces]
    if loose_e:
        bmesh.ops.delete(bm, geom=loose_e, context='EDGES')
    loose_v = [v for v in bm.verts if not v.link_edges]
    if loose_v:
        bmesh.ops.delete(bm, geom=loose_v, context='VERTS')
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    after = (len(bm.verts), len(bm.faces))
    bm.to_mesh(obj.data)
    bm.free()
    r = {"verts": (before[0], after[0]), "faces": (before[1], after[1])}
    print(f"CLEANUP {obj.name}: verts {before[0]}->{after[0]}, faces {before[1]}->{after[1]}")
    return r


def _components(bm):
    seen, n = set(), 0
    for v in bm.verts:
        if v.index in seen:
            continue
        n += 1
        seen.add(v.index)
        stack = [v]
        while stack:
            cur = stack.pop()
            for e in cur.link_edges:
                o = e.other_vert(cur)
                if o.index not in seen:
                    seen.add(o.index)
                    stack.append(o)
    return n


def audit(obj, overhang_deg=45.0, verbose=False):
    """Audit the EVALUATED mesh (modifiers included) in world space.

    Reports: bbox, volume, shells, non-manifold edges, zero-area faces, and overhang area
    steeper than `overhang_deg` from vertical (bed-contact faces excluded).
    Output is one summary line (+ at most 5 worst Z-bands when overhangs exist).
    """
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev, depsgraph=dg)
    bm = bmesh.new()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)
    bm.transform(obj.matrix_world)
    bm.verts.index_update()
    xs = [v.co.x for v in bm.verts]; ys = [v.co.y for v in bm.verts]; zs = [v.co.z for v in bm.verts]
    zmin = min(zs)
    nz_limit = -math.cos(math.radians(90.0 - overhang_deg))  # 45deg -> -0.7071
    nm = sum(1 for e in bm.edges if not e.is_manifold)
    zero = sum(1 for f in bm.faces if f.calc_area() < 1e-6)
    steep, bands = 0.0, {}
    for f in bm.faces:
        a = f.calc_area()
        if a < 1e-4 or f.normal.z >= nz_limit:
            continue
        if abs(f.calc_center_median().z - zmin) < 0.05 and f.normal.z < -0.99:
            continue  # bed contact
        steep += a
        k = round(f.calc_center_median().z)
        bands[k] = bands.get(k, 0.0) + a
    r = {
        "name": obj.name,
        "size": (round(max(xs) - min(xs), 2), round(max(ys) - min(ys), 2), round(max(zs) - zmin, 2)),
        "volume_cm3": round(bm.calc_volume() / 1000.0, 2),
        "shells": _components(bm),
        "non_manifold": nm,
        "zero_area": zero,
        "overhang_mm2": round(steep, 2),
        "faces": len(bm.faces),
    }
    ok = nm == 0 and zero == 0 and r["shells"] == 1
    print(f"AUDIT {obj.name}: size={r['size']} vol={r['volume_cm3']}cm3 shells={r['shells']} "
          f"nonmanifold={nm} zero_area={zero} overhang>{overhang_deg:.0f}deg={r['overhang_mm2']}mm2 "
          f"faces={r['faces']} -> {'PASS' if ok else 'CHECK'}")
    if bands:
        top = sorted(bands.items(), key=lambda kv: -kv[1])[:5]
        print("  overhang Z-bands (z_mm: area_mm2): " + ", ".join(f"{z}: {a:.1f}" for z, a in top))
    r["pass"] = ok
    bm.free()
    return r


def toolbox_check(obj):
    """Run 3D-Print Toolbox on the EVALUATED mesh via view_layer.objects.active."""
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(obj.evaluated_get(dg), depsgraph=dg)
    tmp = bpy.data.objects.new(obj.name + "_chk", me)
    bpy.context.scene.collection.objects.link(tmp)
    prev = bpy.context.view_layer.objects.active
    try:
        for o in bpy.context.selected_objects:
            o.select_set(False)
        tmp.select_set(True)
        bpy.context.view_layer.objects.active = tmp
        bpy.ops.mesh.print3d_check_all()
        rep = {item.name: item.value for item in bpy.context.scene.print3d_toolbox.get_report()}
        print(f"TOOLBOX {obj.name}: " + ", ".join(f"{k}={v}" for k, v in rep.items()))
        return rep
    finally:
        bpy.context.view_layer.objects.active = prev
        bpy.data.objects.remove(tmp, do_unlink=True)
        bpy.data.meshes.remove(me)


def inspect_ref(obj, top_n=8):
    """Compact world-space summary of a reference mesh (bounds, shells, dominant Z planes)."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.transform(obj.matrix_world)
    bm.normal_update()
    xs = [v.co.x for v in bm.verts]; ys = [v.co.y for v in bm.verts]; zs = [v.co.z for v in bm.verts]
    z_planes = {}
    for f in bm.faces:
        if abs(f.normal.z) > 0.95 and f.calc_area() > 10.0:
            z = round(f.calc_center_median().z, 2)
            z_planes[z] = round(z_planes.get(z, 0.0) + f.calc_area(), 1)
    top_z = sorted(z_planes.items(), key=lambda kv: -kv[1])[:top_n]
    r = {
        "x": (round(min(xs), 2), round(max(xs), 2)),
        "y": (round(min(ys), 2), round(max(ys), 2)),
        "z": (round(min(zs), 2), round(max(zs), 2)),
        "shells": _components(bm),
        "top_z_planes": top_z,
    }
    bm.free()
    print(f"REF {obj.name}: X={r['x']} Y={r['y']} Z={r['z']} shells={r['shells']} z_planes={top_z}")
    return r


# --------------------------------------------------------------------- cutters
def make_extruded_cutter(name, pts2d, length, axis='Z', start=0.0, location=(0, 0, 0),
                         collection="2_Boolean_Cutters", hide=True):
    """One watertight single-shell cutter from a closed 2D profile.

    axis='Z': pts2d are (x, y), extruded along +Z from `start` for `length`.
    axis='Y': pts2d are (x, z), extruded along +Y from `start` for `length`.
    Local mesh stays near the object origin; position with `location`.
    """
    me = bpy.data.meshes.new(name + "_Mesh")
    bm = bmesh.new()
    def pt(p, t):
        return (p[0], p[1], t) if axis == 'Z' else (p[0], t, p[1])
    a = [bm.verts.new(pt(p, start)) for p in pts2d]
    b = [bm.verts.new(pt(p, start + length)) for p in pts2d]
    n = len(pts2d)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new([a[i], b[i], b[j], a[j]])
    bm.faces.new(a)
    bm.faces.new(list(reversed(b)))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    ob.location = location
    ensure_collections()[collection].objects.link(ob)
    ob.hide_viewport = False
    if hide:
        ob.hide_set(True)
    return ob


def make_cylinder_cutter(name, diameter, z0, z1, segments=96, location=(0, 0, 0), **kw):
    """Vertical cylinder cutter. `diameter` is the CAD diameter (not the as-printed one)."""
    r = diameter / 2.0
    pts = [(r * math.cos(2 * math.pi * i / segments), r * math.sin(2 * math.pi * i / segments))
           for i in range(segments)]
    return make_extruded_cutter(name, pts, z1 - z0, 'Z', z0, location, **kw)


def add_live_boolean(target, cutter, name=None, operation='DIFFERENCE', solver='MANIFOLD'):
    """Attach `cutter` to `target` as a live Boolean modifier (reusable, editable)."""
    m = target.modifiers.new(name or f"B_{cutter.name}", 'BOOLEAN')
    m.object = cutter
    m.operation = operation
    m.solver = solver
    return m


def apply_modifiers(obj):
    """Bake all modifiers into the mesh (milestone/export only). Context independent (no bpy.ops)."""
    if not obj.modifiers:
        return
    dg = bpy.context.evaluated_depsgraph_get()
    new = bpy.data.meshes.new_from_object(obj.evaluated_get(dg), depsgraph=dg)
    old = obj.data
    new.name = old.name
    obj.modifiers.clear()
    obj.data = new
    if old.users == 0:
        bpy.data.meshes.remove(old)


# ------------------------------------------------------------ versioning/export
def next_version(project_dir):
    """Next unused positive integer across history/*_v<N>.blend|.3mf (ignores .blend1 backups)."""
    hist = os.path.join(project_dir, "history")
    nums = [0]
    if os.path.isdir(hist):
        for f in os.listdir(hist):
            m = re.search(r"_v(\d+)\.(?:blend|3mf)$", f, re.I)
            if m:
                nums.append(int(m.group(1)))
    return max(nums) + 1


def _bake_copy(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(obj.evaluated_get(dg), depsgraph=dg)
    tmp = bpy.data.objects.new(obj.name + "_export", me)
    tmp.matrix_world = obj.matrix_world
    bpy.context.scene.collection.objects.link(tmp)
    return tmp


def snapshot_and_export(project_dir, obj, project_name=None, suffix="", export=True):
    """Milestone save: history/<name>_v<N><suffix>.blend (+ .3mf) and root <name>.3mf.

    Exports a baked copy so live modifiers are always included. Never overwrites a snapshot.
    Saves the root working file only if it lives inside project_dir.
    """
    os.makedirs(os.path.join(project_dir, "history"), exist_ok=True)
    root_name = (os.path.splitext(os.path.basename(bpy.data.filepath))[0]
                 if bpy.data.filepath else (project_name or os.path.basename(project_dir).replace(" ", "_")))
    hist_name = project_name or root_name
    v = next_version(project_dir)
    tag = f"{hist_name}_v{v}{suffix}"
    hist_blend = os.path.join(project_dir, "history", tag + ".blend")
    bpy.ops.wm.save_as_mainfile(filepath=hist_blend, copy=True)
    out = {"version": v, "blend": hist_blend}
    if bpy.data.filepath and os.path.dirname(os.path.abspath(bpy.data.filepath)) == os.path.abspath(project_dir):
        bpy.ops.wm.save_mainfile()
    if export:
        tmp = _bake_copy(obj)
        try:
            for path in (os.path.join(project_dir, root_name + ".3mf"),
                         os.path.join(project_dir, "history", tag + ".3mf")):
                with bpy.context.temp_override(active_object=tmp, selected_objects=[tmp]):
                    bpy.ops.export_mesh.threemf(filepath=path, use_selection=True)
                if not (os.path.exists(path) and os.path.getsize(path) > 0):
                    raise RuntimeError(f"3MF export failed/empty: {path}")
            out["3mf"] = path
        finally:
            me = tmp.data
            bpy.data.objects.remove(tmp, do_unlink=True)
            bpy.data.meshes.remove(me)
    print(f"SNAPSHOT v{v}: {tag} (.blend{' + .3mf' if export else ''}); root export updated={export}")
    return out


def log(project_dir, text):
    """Append one line to the append-only LOG.md (never rewrite PROJECT.md for history)."""
    import datetime
    p = os.path.join(project_dir, "LOG.md")
    new = not os.path.exists(p)
    with open(p, "a") as f:
        if new:
            f.write("# Project Log (append-only)\n\n")
        f.write(f"- {datetime.date.today().isoformat()} - {text}\n")
    print(f"LOG +1 line -> {p}")
