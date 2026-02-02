import math
import numpy as np
import fbx
from collections import defaultdict


def add_skinning(scene, fbx_mesh, skinned_mesh, bone_nodes, ):
    skin = fbx.FbxSkin.Create(scene, "Skin")

    geom = skinned_mesh.geometry
    # TODO Skin index needs to be hooked to the geo attributes

    skin_indices = geom.attributes["skin_index"]
    skin_weights = geom.attributes["skin_weight"]

    for bone_idx, bone in enumerate(skinned_mesh.skeleton.bones):
        print(bone.matrix.elements)
        cluster = fbx.FbxCluster.Create(scene, bone.name)
        cluster.SetLink(bone_nodes[bone])
        cluster.SetLinkMode(fbx.FbxCluster.ELinkMode.eNormalize)

        for v in range(len(skin_indices)):
            for i in range(4):
                idx = int(skin_indices[v, i])
                w = float(skin_weights[v, i])

                if idx == bone_idx and w > 0.0:
                    cluster.AddControlPointIndex(v, w)

        # Bind matrices
        mesh_matrix = fbx.FbxAMatrix()
        bone_matrix = fbx.FbxAMatrix()

        mesh_matrix.SetIdentity()
        bone_matrix.SetIdentity()

        cluster.SetTransformMatrix(mesh_matrix)
        cluster.SetTransformLinkMatrix(bone_matrix)

        skin.AddCluster(cluster)

    fbx_mesh.AddDeformer(skin)


def build_fbx_skeleton(scene, skeleton):
    bone_nodes = {}

    for bone in skeleton.bones:
        fbx_skel = fbx.FbxSkeleton.Create(scene, bone.name)
        fbx_skel.SetSkeletonType(fbx.FbxSkeleton.EType.eLimbNode)

        node = fbx.FbxNode.Create(scene, bone.name)
        node.SetNodeAttribute(fbx_skel)

        # Local translation from your Bone.position
        node.LclTranslation.Set(
            fbx.FbxDouble3(
                bone.position.x,
                bone.position.y,
                bone.position.z
            )
        )

        bone_nodes[bone] = node

    # Build hierarchy
    for bone in skeleton.bones:
        if bone.parent and bone.parent in bone_nodes:
            bone_nodes[bone.parent].AddChild(bone_nodes[bone])

    return bone_nodes


def flatten_mesh(glmesh):
    new_vertices = []
    new_uvs = []
    new_colors = []
    new_faces = []

    vert_map = {}  # (v_idx, uv_idx) -> new index

    for face in glmesh.faces:
        new_face = []
        for v_idx, uv_idx in face:
            key = (v_idx, uv_idx)

            if key not in vert_map:
                vert_map[key] = len(new_vertices)
                new_vertices.append(glmesh.vertices[v_idx])

                if glmesh.uvs is not None:
                    new_uvs.append(glmesh.uvs[uv_idx])

                if glmesh.colors is not None:
                    new_colors.append(glmesh.colors[v_idx])

            new_face.append(vert_map[key])

        new_faces.append(new_face)

    return (
        new_vertices,
        new_uvs if glmesh.uvs is not None else None,
        new_colors if glmesh.colors is not None else None,
        new_faces,
    )


def export_fbx_scene(path, meshes):
    manager = fbx.FbxManager.Create()
    ios = fbx.FbxIOSettings.Create(manager, fbx.IOSROOT)
    manager.SetIOSettings(ios)

    scene = fbx.FbxScene.Create(manager, "Scene")
    root = scene.GetRootNode()

    # -------------------------------
    # Group meshes by material
    # -------------------------------
    meshes_by_material = defaultdict(list)
    for gl_mesh in meshes:
        meshes_by_material[gl_mesh.material_id].append(gl_mesh)

    # -------------------------------
    # Material cache to reuse
    # -------------------------------
    material_cache = {}

    # -------------------------------
    # Process each material group
    # -------------------------------
    parent = fbx.FbxNode.Create(scene, path.split('/')[-1].split('.')[0])

    for material_id, mesh_list in meshes_by_material.items():

        combined_vertices = []
        combined_uvs = []
        combined_colors = []
        combined_faces = []

        vert_map = {}  # maps (vertex_tuple, uv_tuple, color_tuple) -> new index

        # Merge all meshes in this group
        for gl_mesh in mesh_list:
            vertices, uvs, colors, faces = flatten_mesh(gl_mesh)

            for i, v in enumerate(vertices):
                key = [tuple(v)]
                if uvs is not None:
                    key.append(tuple(uvs[i]))
                if colors is not None:
                    key.append(tuple(colors[i]))
                key = tuple(key)

                if key not in vert_map:
                    vert_map[key] = len(combined_vertices)
                    combined_vertices.append(v)
                    if uvs is not None:
                        combined_uvs.append(uvs[i])
                    if colors is not None:
                        combined_colors.append(colors[i])

            # Remap faces
            for face in faces:
                new_face = []
                for idx in face:
                    key = [tuple(vertices[idx])]
                    if uvs is not None:
                        key.append(tuple(uvs[idx]))
                    if colors is not None:
                        key.append(tuple(colors[idx]))
                    key = tuple(key)
                    new_face.append(vert_map[key])
                combined_faces.append(new_face)

        # -------------------------------
        # Create FBX mesh
        # -------------------------------

        fbx_mesh = fbx.FbxMesh.Create(scene, f"Mesh_{path.split('/')[-1].split('.')[0]}")
        fbx_mesh.CreateLayer()
        layer = fbx_mesh.GetLayer(0)

        # Control points
        fbx_mesh.InitControlPoints(len(combined_vertices))
        for i, v in enumerate(combined_vertices):
            fbx_mesh.SetControlPointAt(
                fbx.FbxVector4(float(v[0]), float(v[1]), float(v[2])), i
            )

        # Polygons
        for face in combined_faces:
            fbx_mesh.BeginPolygon()
            for idx in face:
                fbx_mesh.AddPolygon(idx)
            fbx_mesh.EndPolygon()

        # UVs
        if combined_uvs:
            uv_layer = fbx.FbxLayerElementUV.Create(fbx_mesh, "UVs")
            uv_layer.SetMappingMode(fbx.FbxLayerElement.EMappingMode.eByPolygonVertex)
            uv_layer.SetReferenceMode(fbx.FbxLayerElement.EReferenceMode.eIndexToDirect)
            for uv in combined_uvs:
                uv_layer.GetDirectArray().Add(fbx.FbxVector2(float(uv[0]), float(uv[1])))
            for face in combined_faces:
                for idx in face:
                    uv_layer.GetIndexArray().Add(idx)
            layer.SetUVs(uv_layer)

        # Vertex colors
        if combined_colors:
            col_layer = fbx.FbxLayerElementVertexColor.Create(fbx_mesh, "Colors")
            col_layer.SetMappingMode(fbx.FbxLayerElement.EMappingMode.eByControlPoint)
            col_layer.SetReferenceMode(fbx.FbxLayerElement.EReferenceMode.eDirect)
            for c in combined_colors:
                col_layer.GetDirectArray().Add(
                    fbx.FbxColor(
                        float(c[0]),
                        float(c[1]),
                        float(c[2]),
                        float(c[3]) if len(c) > 3 else 1.0
                    )
                )
            layer.SetVertexColors(col_layer)
        if gl_mesh.skinned_mesh:  # SOMTHING BROKE THE MESH ... CHECK THIS FUNCTION
            bone_nodes = build_fbx_skeleton(scene, gl_mesh.skinned_mesh.skeleton)
            add_skinning(scene, fbx_mesh, gl_mesh.skinned_mesh, bone_nodes)
        # Normals
        fbx_mesh.GenerateNormals(True)

        # -------------------------------
        # Create node
        # -------------------------------
        node = fbx.FbxNode.Create(scene, "{}".format(material_id))
        node.SetNodeAttribute(fbx_mesh)
        node.LclScaling.Set(fbx.FbxDouble3(100, 100, 100))
        node.LclRotation.Set(fbx.FbxDouble3(0, 0, 0))

        # -------------------------------
        # Material
        # -------------------------------
        if material_id not in material_cache:
            material = fbx.FbxSurfacePhong.Create(scene, "MI_{}".format(material_id))
            material.Diffuse.Set(fbx.FbxDouble3(1, 1, 1))

            if material_id:
                diffuse_tex = fbx.FbxFileTexture.Create(scene, material_id)
                diffuse_tex.SetFileName("../textures/{}".format(material_id))
                diffuse_tex.SetTextureUse(fbx.FbxTexture.ETextureUse.eStandard)
                diffuse_tex.SetMappingType(fbx.FbxTexture.EMappingType.eUV)
                diffuse_tex.SetMaterialUse(fbx.FbxFileTexture.EMaterialUse.eModelMaterial)
                diffuse_tex.SetSwapUV(False)
                diffuse_tex.SetTranslation(0.0, 0.0)
                diffuse_tex.SetScale(1.0, 1.0)
                diffuse_tex.SetRotation(0.0, 0.0)
                material.Diffuse.ConnectSrcObject(diffuse_tex)

            material_cache[material_id] = material
        else:
            material = material_cache[material_id]

        node.AddMaterial(material)
        parent.AddChild(node)

    root.AddChild(parent)
    # -------------------------------
    # Export FBX
    # -------------------------------
    exporter = fbx.FbxExporter.Create(manager, "")
    exporter.Initialize(path, -1, manager.GetIOSettings())
    exporter.Export(scene)
    exporter.Destroy()
    manager.Destroy()

    print('File Exported')


def write_bvh_joint(f, bone_id, indent, bones, children, offsets, is_root):
    tab = "  " * indent
    name = bones[bone_id].name

    if is_root:
        f.write(f"{tab}ROOT {name}\n")
    else:
        f.write(f"{tab}JOINT {name}\n")

    f.write(f"{tab}{{\n")

    ox, oy, oz = offsets[bone_id]
    f.write(f"{tab}  OFFSET {ox:.6f} {oy:.6f} {oz:.6f}\n")

    if is_root:
        f.write(f"{tab}  CHANNELS 6 Xposition Yposition Zposition Zrotation Yrotation Xrotation\n")
    else:
        f.write(f"{tab}  CHANNELS 3 Zrotation Yrotation Xrotation\n")

    for child in children[bone_id]:
        write_bvh_joint(f, child, indent + 1, bones, children, offsets, False)

    if not children[bone_id]:
        f.write(f"{tab}  End Site\n")
        f.write(f"{tab}  {{\n")
        f.write(f"{tab}    OFFSET 0 0 0\n")
        f.write(f"{tab}  }}\n")

    f.write(f"{tab}}}\n")


def get_rotation_at_time(tracks, bone_id, t):
    for tr in tracks:
        if tr["bone"] == bone_id and tr["type"] == "rotation":
            times = tr["times"]
            values = tr["values"]

            for i in range(len(times)):
                if t <= times[i]:
                    return values[i]
            return values[-1]

    return (0, 0, 0, 1)


def sample_rotation(track, time):
    times = track['times']
    values = track['values']

    if time <= times[0]:
        return np.array(values[0], dtype=np.float32)

    if time >= times[-1]:
        return np.array(values[-1], dtype=np.float32)

    for i in range(len(times) - 1):
        t0, t1 = times[i], times[i + 1]
        if t0 <= time <= t1:
            alpha = (time - t0) / (t1 - t0)
            q0 = np.array(values[i], dtype=np.float32)
            q1 = np.array(values[i + 1], dtype=np.float32)
            return quat_slerp(q0, q1, alpha)


def apply_animation(tracks, time, bones):
    for track in tracks:
        bone = bones[track['bone']]
        q = sample_rotation(track, time)

        # Option A
        # bone.quaternion.set(*q)

        # Option B
        bone.rotation.x, bone.rotation.y, bone.rotation.z = quat_to_euler_zyx(q)


def quat_slerp(q1, q2, t):
    dot = np.dot(q1, q2)

    if dot < 0.0:
        q2 = -q2
        dot = -dot

    if dot > 0.9995:
        return q1 + t * (q2 - q1)

    theta_0 = np.arccos(dot)
    theta = theta_0 * t

    q3 = q2 - q1 * dot
    q3 /= np.linalg.norm(q3)

    return q1 * np.cos(theta) + q3 * np.sin(theta)


def make_transform(pos, rot):
    m = quat_to_mat4(rot)
    m[0:3, 3] = pos
    return m


def quat_to_mat4(q):
    x, y, z, w = q
    xx, yy, zz = x * x, y * y, z * z
    xy, xz, yz = x * y, x * z, y * z
    wx, wy, wz = w * x, w * y, w * z

    return np.array([
        [1 - 2 * (yy + zz), 2 * (xy - wz), 2 * (xz + wy), 0],
        [2 * (xy + wz), 1 - 2 * (xx + zz), 2 * (yz - wx), 0],
        [2 * (xz - wy), 2 * (yz + wx), 1 - 2 * (xx + yy), 0],
        [0, 0, 0, 1],
    ], dtype=np.float32)


def quat_to_euler_zyx(q):
    x, y, z, w = q

    # ZYX order
    t0 = +2.0 * (w * z + x * y)
    t1 = +1.0 - 2.0 * (y * y + z * z)
    rz = math.atan2(t0, t1)

    t2 = +2.0 * (w * y - z * x)
    t2 = max(-1.0, min(1.0, t2))
    ry = math.asin(t2)

    t3 = +2.0 * (w * x + y * z)
    t4 = +1.0 - 2.0 * (x * x + y * y)
    rx = math.atan2(t3, t4)

    return (
        math.degrees(rz),
        math.degrees(ry),
        math.degrees(rx),
    )


def export_bvh(animation, filename, skeleton, fps=30):
    frame_time = 1.0 / fps
    num_frames = animation.length

    with open(filename, "w") as f:
        # --- HIERARCHY ---
        f.write("HIERARCHY\n")

        root = 0
        write_bvh_joint(
            f,
            root,
            0,
            skeleton.bones,
            [[skeleton.bones.index(y) for y in x.children] for x in skeleton.bones],
            [a.position.get() for a in skeleton.bones],
            True,
        )

        # --- MOTION ---
        f.write("MOTION\n")
        f.write(f"Frames: {num_frames}\n")
        f.write(f"Frame Time: {frame_time:.6f}\n")

        for frame in range(num_frames):
            t = frame * frame_time
            values = []

            for bone_id in range(len(skeleton.bones)):
                q = get_rotation_at_time(animation.tracks, bone_id, t)
                rz, ry, rx = quat_to_euler_zyx(q)

                if bone_id == 0:
                    values.extend([0.0, 0.0, 0.0])  # root position

                values.extend([rz, ry, rx])

            f.write(" ".join(f"{v:.6f}" for v in values) + "\n")
