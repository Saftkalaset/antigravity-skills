"""3d-print-blender helper library (run inside the live Blender session).

Load once per session (via execute_blender_code):
    exec(open('<skill-directory>/scripts/lib.py').read(), globals())

Design rules:
  * Every function prints ONE compact summary and returns a dict. Never prints per-face lists.
  * Cutters are kept as live Boolean modifier targets; apply only on milestone/export.
  * Cutters are hidden with hide_set(True) and hide_viewport stays False (depsgraph rule).
  * Persist extracted reference measurements in `scene["cad_specs"]` (`save_specs`/`get_specs`)
    and keep-out zones as `KeepOut_*` wireframes in `3_References` to avoid repeat raycasting.
"""
import bpy, bmesh, json, math, os, re
from mathutils import Vector
from mathutils.bvhtree import BVHTree

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
    has_specs = "cad_specs" in bpy.context.scene
    has_recipe = "parametric_recipe.py" in bpy.data.texts
    print(f"ENV {r['blender']} | file={r['filepath']} | specs_cached={has_specs} | recipe={has_recipe} | problems={bad or 'none'}")
    return r


def world_bbox(obj):
    """World-space bounding box (xmin, xmax, ymin, ymax, zmin, zmax) rounded to 2 decimals."""
    if obj.type != 'MESH' or not obj.data.vertices:
        return None
    pts = [obj.matrix_world @ v.co for v in obj.data.vertices]
    return (round(min(p.x for p in pts), 2), round(max(p.x for p in pts), 2),
            round(min(p.y for p in pts), 2), round(max(p.y for p in pts), 2),
            round(min(p.z for p in pts), 2), round(max(p.z for p in pts), 2))

_world_bbox = world_bbox


def _load_recipe_into_builtins(name="parametric_recipe.py"):
    import builtins as _b, inspect as _ins
    txt = bpy.data.texts.get(name)
    if not txt:
        return []
    ns = {}
    exec(txt.as_string(), globals(), ns)
    sigs = []
    for k, v in ns.items():
        if not k.startswith("_") and callable(v):
            setattr(_b, k, v)
            globals()[k] = v
            try:
                sigs.append(f"{k}{_ins.signature(v)}")
            except Exception:
                sigs.append(f"{k}()")
    return sigs


def open_project(project_dir):
    """Single-call session bootstrap: open <Project>.blend if needed, load recipe into builtins, and print scene/spec/bbox digest."""
    project_dir = os.path.abspath(project_dir)
    cur_path = os.path.abspath(bpy.data.filepath) if bpy.data.filepath else ""
    if os.path.dirname(cur_path) != project_dir:
        blends = [f for f in os.listdir(project_dir) if f.endswith(".blend")] if os.path.isdir(project_dir) else []
        if blends:
            bpy.ops.wm.open_mainfile(filepath=os.path.join(project_dir, sorted(blends)[0]))
    env = check_env()
    specs = get_specs() if "cad_specs" in bpy.context.scene else {}
    recipe_fns = _load_recipe_into_builtins()
    if recipe_fns:
        print(f"RECIPE loaded into builtins: {', '.join(recipe_fns)}")
    parts, cutters, refs = [], [], []
    for o in (bpy.data.collections.get("1_Printable_Parts").objects if bpy.data.collections.get("1_Printable_Parts") else []):
        mods = [f"{m.name}({getattr(m, 'solver', m.type)})" for m in o.modifiers]
        parts.append(f"{o.name} bbox={_world_bbox(o)} mods={mods}")
    for o in (bpy.data.collections.get("2_Boolean_Cutters").objects if bpy.data.collections.get("2_Boolean_Cutters") else []):
        cdef = json.loads(o["cutter_def"]) if "cutter_def" in o else {}
        cd_str = f" axis={cdef.get('axis')} {cdef.get('start')}..{round(cdef.get('start',0)+cdef.get('length',0),2)}" if cdef else ""
        cutters.append(f"{o.name} bbox={_world_bbox(o)}{cd_str}")
    for o in (bpy.data.collections.get("3_References").objects if bpy.data.collections.get("3_References") else []):
        refs.append(f"{o.name} bbox={_world_bbox(o)}")
    print(f"PROJECT parts={parts} | cutters={cutters} | refs={refs}")
    return {"env": env, "specs": specs, "recipe_fns": recipe_fns, "parts": parts, "cutters": cutters, "refs": refs}


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


# ---------------------------------------------------- persistent in-file specs
def save_specs(target=None, **specs):
    """Merge and persist JSON-serializable CAD measurements into target['cad_specs'] (default: scene)."""
    tgt = target if target is not None else bpy.context.scene
    cur = json.loads(tgt["cad_specs"]) if "cad_specs" in tgt else {}
    cur.update(specs)
    tgt["cad_specs"] = json.dumps(cur, sort_keys=True)
    print(f"SPECS saved on {getattr(tgt, 'name', 'scene')}: keys={list(cur.keys())}")
    return cur


def get_specs(target=None):
    """Read persisted CAD measurements from target['cad_specs'] (default: scene) in one call."""
    tgt = target if target is not None else bpy.context.scene
    cur = json.loads(tgt["cad_specs"]) if "cad_specs" in tgt else {}
    print(f"SPECS ({getattr(tgt, 'name', 'scene')}): {json.dumps(cur)}")
    return cur


def save_recipe(code_str, name="parametric_recipe.py"):
    """Save a reusable parametric rebuild script inside bpy.data.texts[name] and load its functions into builtins."""
    txt = bpy.data.texts.get(name) or bpy.data.texts.new(name)
    txt.clear()
    txt.write(code_str)
    fns = _load_recipe_into_builtins(name)
    print(f"RECIPE saved in bpy.data.texts['{name}'] ({len(code_str.splitlines())} lines) | loaded: {', '.join(fns) or 'none'}")
    return txt


def get_recipe(name="parametric_recipe.py"):
    """Return and print the parametric rebuild script from bpy.data.texts[name] if present."""
    txt = bpy.data.texts.get(name)
    s = txt.as_string() if txt else ""
    print(f"RECIPE '{name}': {len(s.splitlines())} lines" if txt else f"RECIPE '{name}': (not found)")
    return s


def make_keepout_box(name, x_range, y_range, z_range, collection="3_References"):
    """Create or update a wireframe keep-out box (`KeepOut_<Name>`) in 3_References."""
    full_name = name if name.startswith("KeepOut_") else f"KeepOut_{name}"
    pts = [
        (x_range[0], y_range[0]), (x_range[1], y_range[0]),
        (x_range[1], y_range[1]), (x_range[0], y_range[1]),
    ]
    ob = bpy.data.objects.get(full_name)
    if ob is not None:
        bpy.data.objects.remove(ob, do_unlink=True)
    ob = make_extruded_cutter(full_name, pts, z_range[1] - z_range[0], axis='Z',
                              start=z_range[0], collection=collection, hide=False)
    ob.display_type = 'WIRE'
    ob.hide_render = True
    return ob


def make_keepout_cylinder(name, center_xyz, radius, length, axis='Y', segments=64, collection="3_References"):
    """Create or update a wireframe keep-out cylinder (`KeepOut_<Name>`) in 3_References."""
    full_name = name if name.startswith("KeepOut_") else f"KeepOut_{name}"
    cx, cy, cz = center_xyz
    pts = [( (cx if axis != 'X' else cy) + radius * math.cos(2 * math.pi * i / segments),
             (cz if axis == 'Y' else cy) + radius * math.sin(2 * math.pi * i / segments) )
           for i in range(segments)]
    ob = bpy.data.objects.get(full_name)
    if ob is not None:
        bpy.data.objects.remove(ob, do_unlink=True)
    start = (cy if axis == 'Y' else (cx if axis == 'X' else cz)) - 0.5 * length
    ob = make_extruded_cutter(full_name, pts, length, axis=axis,
                              start=start, collection=collection, hide=False)
    ob.display_type = 'WIRE'
    ob.hide_render = True
    return ob


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

    Reports: bbox, volume, shells, non-manifold edges, zero-area faces, overhang area
    steeper than `overhang_deg` from vertical (bed-contact faces excluded), and any
    collisions with `KeepOut_*` meshes in `3_References`.
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

    # Check BVHTree overlap against any KeepOut_* objects and compute min_wall thickness
    bvh_part = BVHTree.FromBMesh(bm, epsilon=0.0)
    ko_hits = []
    ko_objs = [o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith("KeepOut_")]
    for ko in ko_objs:
        bm_k = bmesh.new()
        bm_k.from_mesh(ko.data)
        bm_k.transform(ko.matrix_world)
        bvh_k = BVHTree.FromBMesh(bm_k, epsilon=0.0)
        if bvh_part.overlap(bvh_k):
            ko_hits.append(ko.name)
        bm_k.free()

    bm.faces.ensure_lookup_table()
    min_wall, min_wall_at = float("inf"), None
    for f in bm.faces:
        if f.calc_area() < 2.0:
            continue
        c = f.calc_center_median()
        hit, hit_no, idx, dist = bvh_part.ray_cast(c - f.normal * 0.02, -f.normal)
        if hit is not None and dist > 0.1 and hit_no.dot(f.normal) < -0.90:
            ring_verts = set(v.index for v in f.verts for e in v.link_edges for v in e.verts)
            if not (ring_verts & set(v.index for v in bm.faces[idx].verts)):
                if dist + 0.02 < min_wall:
                    min_wall = dist + 0.02
                    min_wall_at = tuple(round(x, 1) for x in c)
    min_wall_mm = round(min_wall, 2) if min_wall < float("inf") else None

    r = {
        "name": obj.name,
        "size": (round(max(xs) - min(xs), 2), round(max(ys) - min(ys), 2), round(max(zs) - zmin, 2)),
        "volume_cm3": round(bm.calc_volume() / 1000.0, 2),
        "shells": _components(bm),
        "non_manifold": nm,
        "zero_area": zero,
        "overhang_mm2": round(steep, 2),
        "min_wall_mm": min_wall_mm,
        "min_wall_at": min_wall_at,
        "keepout_hits": ko_hits,
        "faces": len(bm.faces),
    }
    ok = nm == 0 and zero == 0 and r["shells"] == 1 and len(ko_hits) == 0
    ko_str = f" keepout_hits={ko_hits or 0}" if ko_objs else ""
    mw_str = f" min_wall={min_wall_mm}mm@{min_wall_at}" if min_wall_mm is not None else ""
    print(f"AUDIT {obj.name}: size={r['size']} vol={r['volume_cm3']}cm3 shells={r['shells']} "
          f"nonmanifold={nm} zero_area={zero} overhang>{overhang_deg:.0f}deg={r['overhang_mm2']}mm2"
          f"{mw_str}{ko_str} faces={r['faces']} -> {'PASS' if ok else 'CHECK'}")
    if bands:
        top = sorted(bands.items(), key=lambda kv: -kv[1])[:5]
        print("  overhang Z-bands (z_mm: area_mm2): " + ", ".join(f"{z}: {a:.1f}" for z, a in top))
    r["pass"] = ok
    bm.free()
    return r


def audit_cantilever(obj, axis='X', root_pos=None, tip_pos=None, load_n=25.0, e_mpa=900.0, slices=40):
    """Exact cross-sectional beam solver (Green's theorem on 3D mesh slices) for cantilever brackets.

    Slices the evaluated mesh along `axis` ('X' or 'Y') from `root_pos` to `tip_pos`,
    computing exact cross-sectional area A(s), neutral axis zc(s), second moment I(s),
    section modulus Zs(s), peak bending stress (MPa), and Euler-Bernoulli tip sag (mm).
    Prints ONE summary line.
    """
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(obj.evaluated_get(dg), depsgraph=dg)
    bm = bmesh.new()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)
    bm.transform(obj.matrix_world)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.normal_update()

    ax = 0 if axis.upper() == 'X' else 1
    ay = 1 if ax == 0 else 0
    coords = [v.co[ax] for v in bm.verts]
    s0 = root_pos if root_pos is not None else min(coords) + 1.0
    s1 = tip_pos if tip_pos is not None else max(coords) - 1.0
    span = abs(s1 - s0)
    sign_dir = 1.0 if s1 >= s0 else -1.0
    ds = span / slices

    weak_s, min_zs, min_i, max_stress = s0, float("inf"), float("inf"), 0.0
    tip_sag = 0.0
    for k in range(slices):
        s = s0 + sign_dir * (k + 0.5) * ds
        area, qz, iz0 = 0.0, 0.0, 0.0
        zs_slice = []
        for f in bm.faces:
            vs = f.verts
            d = [v.co[ax] - s for v in vs]
            pts = []
            for i in range(3):
                j = (i + 1) % 3
                if (d[i] < 0.0 and d[j] >= 0.0) or (d[i] >= 0.0 and d[j] < 0.0):
                    t = d[i] / (d[i] - d[j])
                    pts.append((vs[i].co[ay] + t * (vs[j].co[ay] - vs[i].co[ay]),
                                vs[i].co.z + t * (vs[j].co.z - vs[i].co.z)))
            if len(pts) == 2:
                (y0, z0), (y1, z1) = pts[0], pts[1]
                ny, nz = f.normal[ay], f.normal.z
                if (z1 - z0) * ny - (y1 - y0) * nz < 0.0:
                    y0, z0, y1, z1 = y1, z1, y0, z0
                dz = z1 - z0
                area += 0.5 * (y0 + y1) * dz
                qz += (0.25 * (y0 + y1) * (z0 + z1) + (y1 - y0) * dz / 12.0) * dz
                iz0 += dz * (y0 * (z0 * z0 / 4.0 + z0 * z1 / 6.0 + z1 * z1 / 12.0)
                             + y1 * (z0 * z0 / 12.0 + z0 * z1 / 6.0 + z1 * z1 / 4.0))
                zs_slice.extend((z0, z1))
        if area > 1.0 and zs_slice:
            zc = qz / area
            iyy = max(1.0, iz0 - area * zc * zc)
            c_max = max(abs(max(zs_slice) - zc), abs(min(zs_slice) - zc), 0.5)
            zs_mod = iyy / c_max
            arm = abs(s1 - s)
            moment = load_n * (arm ** 2) / (2.0 * max(span, 1.0))  # distributed load M(s)
            stress = moment / zs_mod
            tip_sag += (moment / (e_mpa * iyy)) * arm * ds
            if zs_mod < min_zs:
                min_zs, min_i, weak_s = zs_mod, iyy, s
            if stress > max_stress:
                max_stress = stress
    bm.free()
    r = {
        "axis": axis.upper(), "span_mm": round(span, 1), "weak_pos_mm": round(weak_s, 1),
        "min_I_mm4": round(min_i, 1), "min_Zs_mm3": round(min_zs, 1),
        "max_stress_mpa": round(max_stress, 2), "est_tip_sag_mm": round(tip_sag, 2),
    }
    print(f"CANTILEVER {obj.name} ({r['axis']}={s0:.1f}..{s1:.1f}mm, F={load_n}N, E={e_mpa}MPa): "
          f"weak_{r['axis']}={r['weak_pos_mm']}mm I={r['min_I_mm4']}mm4 Zs={r['min_Zs_mm3']}mm3 "
          f"stress={r['max_stress_mpa']}MPa tip_sag={r['est_tip_sag_mm']}mm")
    return r


def check_insertion(part, moving_obj, path_vec, steps=20):
    """Sweep `moving_obj` along `offset = path_vec * frac` (frac=1.0 -> 1/steps) and check BVH overlap with `part`.

    Builds the static BVH in C via `BVHTree.FromObject` on whichever mesh has more faces
    (e.g. an 88k-face reference scan) and translates the lighter mesh in local space (<180 ms total).
    Excludes frac=0.0 so seated resting contact does not false-trigger a collision.
    """
    dg = bpy.context.evaluated_depsgraph_get()
    ev_p, ev_m = part.evaluated_get(dg), moving_obj.evaluated_get(dg)
    if len(ev_m.data.polygons) > len(ev_p.data.polygons):
        static_ob, moving_ob, sign = moving_obj, part, -1.0
    else:
        static_ob, moving_ob, sign = part, moving_obj, 1.0

    bvh_static = BVHTree.FromObject(static_ob, dg, epsilon=0.0)
    inv_static = static_ob.matrix_world.inverted()

    me_mv = bpy.data.meshes.new_from_object(moving_ob.evaluated_get(dg), depsgraph=dg)
    bm_mv = bmesh.new(); bm_mv.from_mesh(me_mv); bpy.data.meshes.remove(me_mv)
    bm_mv.transform(inv_static @ moving_ob.matrix_world)

    vec_local = inv_static.to_3x3() @ (Vector(path_vec) * sign)
    hits_at = []
    for k in range(steps):
        frac = 1.0 - (k / steps)
        bm_step = bm_mv.copy()
        bmesh.ops.translate(bm_step, verts=bm_step.verts, vec=vec_local * frac)
        bvh_step = BVHTree.FromBMesh(bm_step, epsilon=0.0)
        if bvh_static.overlap(bvh_step):
            hits_at.append(round(frac, 2))
        bm_step.free()
    bm_mv.free()
    ok = len(hits_at) == 0
    print(f"INSERTION {moving_obj.name} -> {part.name} along {tuple(round(x,1) for x in path_vec)}: "
          f"steps={steps} hit_fracs={hits_at or 'none'} -> {'PASS' if ok else 'BLOCKED'}")
    return {"pass": ok, "hit_fracs": hits_at}


def toolbox_check(obj):
    """Run 3D-Print Toolbox on the EVALUATED mesh via view_layer.objects.active."""
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(obj.evaluated_get(dg), depsgraph=dg)
    tmp = bpy.data.objects.new(obj.name + "_chk", me)
    bpy.context.scene.collection.objects.link(tmp)
    prev = bpy.context.view_layer.objects.active
    try:
        for o in bpy.context.view_layer.objects:
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


def quiet_summary(coords, label="POINTS"):
    """Compact 1-line statistical digest (count, X/Y/Z spans, centroid) of vectors/tuples/vertices.

    Use whenever querying vertex or face clusters to prevent flooding LLM context with raw arrays.
    """
    pts = []
    for c in coords:
        if hasattr(c, "co"):
            pts.append(c.co)
        elif hasattr(c, "x") and hasattr(c, "y"):
            pts.append(c)
        elif isinstance(c, (tuple, list)) and len(c) >= 2:
            pts.append(Vector((c[0], c[1], c[2] if len(c) > 2 else 0.0)))
    if not pts:
        print(f"{label}: n=0 (empty)")
        return {"n": 0}
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    zs = [p[2] if len(p) > 2 else 0.0 for p in pts]
    r = {
        "n": len(pts),
        "x": (round(min(xs), 2), round(max(xs), 2)),
        "y": (round(min(ys), 2), round(max(ys), 2)),
        "z": (round(min(zs), 2), round(max(zs), 2)),
        "centroid": (round(sum(xs) / len(xs), 2), round(sum(ys) / len(ys), 2), round(sum(zs) / len(zs), 2))
    }
    print(f"{label}: n={r['n']} X={r['x']} Y={r['y']} Z={r['z']} centroid={r['centroid']}")
    return r


def quiet_inspect(obj, z_range=None, min_area=None):
    """World-space filtered digest of vertices/faces on obj matching z_range=(z0, z1) or min_area.

    Prints one summary line instead of raw coordinate loops.
    """
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.transform(obj.matrix_world)
    verts = bm.verts
    if z_range is not None:
        verts = [v for v in verts if z_range[0] <= v.co.z <= z_range[1]]
    faces = bm.faces
    if z_range is not None:
        faces = [f for f in faces if z_range[0] <= f.calc_center_median().z <= z_range[1]]
    if min_area is not None:
        faces = [f for f in faces if f.calc_area() >= min_area]
    label = f"INSPECT {obj.name}" + (f" Z={z_range}" if z_range else "") + (f" area>={min_area}" if min_area else "")
    res = quiet_summary([v.co for v in verts], label=label)
    res["faces_matching"] = len(faces)
    bm.free()
    return res


# --------------------------------------------------------------------- cutters
def rounded_poly_2d(pts2d, r=3.0, arc_steps=6):
    """Round corners of a 2D polygon `pts2d` with uniform radius `r` or per-vertex radii list/tuple (`r_i <= 0` keeps sharp)."""
    pts = [Vector((p[0], p[1])) for p in pts2d]
    m = len(pts)
    radii = [r] * m if isinstance(r, (int, float)) else list(r)
    area2 = sum(pts[i].x * pts[(i + 1) % m].y - pts[(i + 1) % m].x * pts[i].y for i in range(m))
    if area2 < 0:
        pts.reverse()
        radii.reverse()
    out = []
    for i in range(m):
        ri = radii[i]
        v1 = (pts[(i - 1) % m] - pts[i]).normalized()
        v2 = (pts[(i + 1) % m] - pts[i]).normalized()
        ha = 0.5 * math.acos(max(-1.0, min(1.0, v1.dot(v2))))
        if ri <= 1e-4 or ha < 1e-3 or abs(ha - 0.5 * math.pi) < 1e-3:
            out.append((round(pts[i].x, 3), round(pts[i].y, 3)))
            continue
        dc, dt = ri / math.sin(ha), ri / math.tan(ha)
        c = pts[i] + (v1 + v2).normalized() * dc
        t1, t2 = pts[i] + v1 * dt, pts[i] + v2 * dt
        a1, a2 = math.atan2(t1.y - c.y, t1.x - c.x), math.atan2(t2.y - c.y, t2.x - c.x)
        da = (a2 - a1) % (2.0 * math.pi)
        if da > math.pi:
            da -= 2.0 * math.pi
        for s in range(arc_steps + 1):
            ang = a1 + da * (s / arc_steps)
            out.append((round(c.x + ri * math.cos(ang), 3), round(c.y + ri * math.sin(ang), 3)))
    return out


def rect_2d(w, h, cx=0.0, cy=0.0, r=0.0, arc_steps=6):
    """2D rectangle of `(w, h)` centered at `(cx, cy)` with uniform radius `r` or 4-tuple `(r_bl, r_br, r_tr, r_tl)`."""
    hw, hh = 0.5 * w, 0.5 * h
    pts = [(cx - hw, cy - hh), (cx + hw, cy - hh), (cx + hw, cy + hh), (cx - hw, cy + hh)]
    return rounded_poly_2d(pts, r=r, arc_steps=arc_steps) if r else pts


def set_extruded_profile(obj, pts2d, length, axis='Z', start=0.0):
    """Update `obj.data` in-place from a 2D profile extruded along `axis` ('X', 'Y', or 'Z').

    axis='Z': pts2d are (x, y), extruded along +Z from `start` for `length`.
    axis='Y': pts2d are (x, z), extruded along +Y from `start` for `length`.
    axis='X': pts2d are (y, z), extruded along +X from `start` for `length`.
    Also caches the 2D profile metadata in `obj["cutter_def"]`.
    """
    bm = bmesh.new()
    def pt(p, t):
        if axis == 'Z':
            return (p[0], p[1], t)
        return (p[0], t, p[1]) if axis == 'Y' else (t, p[0], p[1])
    a = [bm.verts.new(pt(p, start)) for p in pts2d]
    b = [bm.verts.new(pt(p, start + length)) for p in pts2d]
    n = len(pts2d)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new([a[i], b[i], b[j], a[j]])
    bm.faces.new(a)
    bm.faces.new(list(reversed(b)))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    obj["cutter_def"] = json.dumps({
        "axis": axis, "start": round(start, 3), "length": round(length, 3),
        "pts2d": [[round(p[0], 3), round(p[1], 3)] for p in pts2d],
    })
    return obj


def make_extruded_cutter(name, pts2d, length, axis='Z', start=0.0, location=(0, 0, 0),
                         collection="2_Boolean_Cutters", hide=True):
    """One watertight single-shell cutter from a closed 2D profile ('X', 'Y', or 'Z')."""
    me = bpy.data.meshes.new(name + "_Mesh")
    ob = bpy.data.objects.new(name, me)
    ob.location = location
    set_extruded_profile(ob, pts2d, length, axis=axis, start=start)
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


def make_slotted_cylinder_cutter(name, bore_dia, channel_w, channel_len, z0, z1,
                                 angle_deg=0.0, flare_r=0.0, segments=64, location=(0, 0, 0), **kw):
    """Watertight single-shell cylinder cutter with an exit slot and optional entry mouth flares."""
    r_bore = bore_dia / 2.0
    hw = channel_w / 2.0
    rad = math.radians(angle_deg)
    ux, uy = math.sin(rad), math.cos(rad)
    nx, ny = uy, -ux
    pts = []
    start_a = math.atan2(-ny, -nx)
    for i in range(segments + 1):
        a = start_a + math.pi * (i / segments)
        pts.append((r_bore * math.cos(a), r_bore * math.sin(a)))
    if flare_r > 0.0:
        pts.append((nx * hw + ux * (channel_len - flare_r), ny * hw + uy * (channel_len - flare_r)))
        for s in range(1, 9):
            ta = math.pi - 0.5 * math.pi * (s / 8)
            pts.append((nx * (hw + flare_r * (1.0 + math.cos(ta))) + ux * (channel_len - flare_r + flare_r * math.sin(ta)),
                        ny * (hw + flare_r * (1.0 + math.cos(ta))) + uy * (channel_len - flare_r + flare_r * math.sin(ta))))
        pts.append((nx * (hw + flare_r) + ux * channel_len, ny * (hw + flare_r) + uy * channel_len))
        pts.append((-nx * (hw + flare_r) + ux * channel_len, -ny * (hw + flare_r) + uy * channel_len))
        for s in range(8, 0, -1):
            ta = 0.5 * math.pi * (s / 8)
            pts.append((-nx * (hw + flare_r * (1.0 - math.cos(ta))) + ux * (channel_len - flare_r + flare_r * math.sin(ta)),
                        -ny * (hw + flare_r * (1.0 - math.cos(ta))) + uy * (channel_len - flare_r + flare_r * math.sin(ta))))
        pts.append((-nx * hw + ux * (channel_len - flare_r), -ny * hw + uy * (channel_len - flare_r)))
    else:
        pts.append((nx * hw + ux * channel_len, ny * hw + uy * channel_len))
        pts.append((-nx * hw + ux * channel_len, -ny * hw + uy * channel_len))
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


def snapshot_and_export(project_dir, obj, project_name=None, suffix="", export=True, log_msg=None):
    """Milestone save: audits `obj`, saves history/<name>_v<N><suffix>.blend (+ .3mf), root <name>.3mf, and optional LOG.md entry.

    Exports a baked copy so live modifiers are always included. Refuses export if non-manifold or multi-shell.
    """
    aud = audit(obj)
    if export and (aud["non_manifold"] > 0 or aud["shells"] != 1):
        raise RuntimeError(f"Export blocked by audit failure on {obj.name}: shells={aud['shells']}, non_manifold={aud['non_manifold']}")
    os.makedirs(os.path.join(project_dir, "history"), exist_ok=True)
    root_name = (os.path.splitext(os.path.basename(bpy.data.filepath))[0]
                 if bpy.data.filepath else (project_name or os.path.basename(project_dir).replace(" ", "_")))
    hist_name = project_name or root_name
    v = next_version(project_dir)
    tag = f"{hist_name}_v{v}{suffix}"
    hist_blend = os.path.join(project_dir, "history", tag + ".blend")
    bpy.ops.wm.save_as_mainfile(filepath=hist_blend, copy=True)
    out = {"version": v, "blend": hist_blend, "audit": aud}
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
    if log_msg:
        log(project_dir, f"**v{v}** (`history/{tag}.blend` & `.3mf`): {log_msg}")
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


# Persist helpers and core modules in builtins so a single session bootstrap makes them available across all MCP calls
import builtins as _builtins
for _k, _v in list(globals().items()):
    if not _k.startswith("_") and (callable(_v) or _k in ("bmesh", "json", "math", "os", "re", "CANON")):
        setattr(_builtins, _k, _v)


