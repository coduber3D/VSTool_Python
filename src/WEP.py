# from three import (
#     BufferGeometry,
#     Skeleton,
#     Float32BufferAttribute,
#     SkinnedMesh,
#     Bone,
#     VertexColors,
#     MeshNormalMaterial,
# )
from src.V3DClasses import Geometry, SkinnedMesh, Material, Bone, Skeleton
from src.VSTOOLS import float32_buffer_attribute, compute_vertex_normals
from src.WEP_classes import *




class WEP:
    def __init__(self, reader):
        self.mesh = None
        self.geometry = None
        self.material = None
        self.uv = None
        self.reader = reader
        self.version = 1

    def read(self):
        self.header()
        self.data()

    # ───────────────────────── headers ─────────────────────────

    def header(self):
        r = self.reader

        self.header1()

        self.texture_ptr1 = r.u32() + 0x10
        r.padding(0x30)
        self.texture_ptr = r.u32() + 0x10
        self.group_ptr = r.u32() + 0x10
        self.vertex_ptr = r.u32() + 0x10
        self.face_ptr = r.u32() + 0x10

    def header1(self):
        r = self.reader

        # magic 'H01\0'
        r.constant([0x48, 0x30, 0x31, 0x00])

        self.num_bones = r.u8()
        self.num_groups = r.u8()
        self.num_triangles = r.u16()
        self.num_quads = r.u16()
        self.num_polygons = r.u16()
        self.num_all_polygons = (
            self.num_triangles + self.num_quads + self.num_polygons
        )

    # ───────────────────────── data sections ─────────────────────────

    def data(self):
        self.bone_section()
        self.group_section()
        self.vertex_section()
        self.face_section()
        self.texture_section(7, True)

    def bone_section(self):
        self.bones = []

        for i in range(self.num_bones):
            bone = WEPBone(self.reader, i)
            bone.read()
            self.bones.append(bone)

    def group_section(self):
        self.groups = []

        for i in range(self.num_groups):
            group = WEPGroup(self.reader, i)
            group.read()

            bone = self.bones[group.bone_id]
            if group.id != bone.group_id:
                raise RuntimeError("Unexpected group/bone reference")

            self.groups.append(group)

    def vertex_section(self):
        self.vertices = []
        self.num_vertices = self.groups[self.num_groups - 1].last_vertex

        g = 0
        for i in range(self.num_vertices):
            if i >= self.groups[g].last_vertex:
                g += 1

            vertex = WEPVertex(self.reader)
            vertex.read()
            vertex.group_id = g
            self.vertices.append(vertex)

    def face_section(self):
        r = self.reader
        pos = r.pos

        try:
            self.faces = []
            for _ in range(self.num_all_polygons):
                face = WEPFace(r)
                face.read()
                self.faces.append(face)
        except Exception as err:
            if "Unknown face type" not in str(err):
                raise

            r.seek(pos)
            self.faces = []
            self.version = 2

            for _ in range(self.num_all_polygons):
                face = WEPFace(r)
                face.read_colored()
                self.faces.append(face)

    def texture_section(self, num_palettes, wep):
        self.texture_map = WEPTextureMap(self.reader)
        self.texture_map.read(num_palettes, wep)

    # ───────────────────────── build pipeline ─────────────────────────

    def build(self):
        self.build_geometry()
        self.build_material()
        self.build_skeleton()
        self.build_mesh()

    def build_geometry(self):
        tw = self.texture_map.get_width()
        th = self.texture_map.height

        iv = 0
        index = []
        position = []
        uv = []
        skin_weight = []
        skin_index = []
        color = []
        face_sizes = []

        def get_offset(vertex):
            offset = 0
            bone = self.get_parent_bone(self.groups[vertex.group_id].bone_id)

            while bone:
                offset += -bone.length
                bone = self.get_parent_bone(bone.id)

            return offset

        def get_bone_id(vertex):
            return self.groups[vertex.group_id].bone_id

        for f in self.faces:
            if f.quad():
                vs = [self.vertices[i] for i in (f.vertex1, f.vertex2, f.vertex3, f.vertex4)]
                for v in vs:
                    position.extend((v.x + get_offset(v), v.y, v.z))
                    skin_weight.extend((1, 0, 0, 0))
                    skin_index.extend((get_bone_id(v), 0, 0, 0))

                uv.extend((
                    f.u1 / tw, f.v1 / th,
                    f.u2 / tw, f.v2 / th,
                    f.u3 / tw, f.v3 / th,
                    f.u4 / tw, f.v4 / th,
                ))

                color.extend((
                    f.r1 / 255, f.g1 / 255, f.b1 / 255,
                    f.r2 / 255, f.g2 / 255, f.b2 / 255,
                    f.r3 / 255, f.g3 / 255, f.b3 / 255,
                    f.r4 / 255, f.g4 / 255, f.b4 / 255,
                ))

                index.extend((iv + 2, iv + 1, iv + 0, iv + 1, iv + 2, iv + 3))
                face_sizes.append(4)
                if f.double():
                    index.extend((iv + 0, iv + 1, iv + 2, iv + 3, iv + 2, iv + 1))

                iv += 4
            else:
                vs = [self.vertices[i] for i in (f.vertex1, f.vertex2, f.vertex3)]
                for v in vs:
                    position.extend((v.x + get_offset(v), v.y, v.z))
                    skin_weight.extend((1, 0, 0, 0))
                    skin_index.extend((get_bone_id(v), 0, 0, 0))

                uv.extend((
                    f.u2 / tw, f.v2 / th,
                    f.u3 / tw, f.v3 / th,
                    f.u1 / tw, f.v1 / th,
                ))

                color.extend((
                    f.r1 / 255, f.g1 / 255, f.b1 / 255,
                    f.r2 / 255, f.g2 / 255, f.b2 / 255,
                    f.r3 / 255, f.g3 / 255, f.b3 / 255,
                ))

                index.extend((iv + 2, iv + 1, iv + 0))
                face_sizes.append(3)
                if f.double():
                    index.extend((iv + 0, iv + 1, iv + 2))

                iv += 3



        self.geometry = Geometry()
        self.geometry.attributes["positions"] = position
        self.geometry.attributes["normals"] = compute_vertex_normals(position, index, face_sizes)
        self.geometry.attributes["face_sizes"] = face_sizes
        self.geometry.attributes["indices"] = index
        self.geometry.attributes["colors"] = color
        self.geometry.attributes["uvs"] = uv
        self.geometry.attributes["skin_weight"] = float32_buffer_attribute(skin_weight, 4)
        self.geometry.attributes["skin_index"] = float32_buffer_attribute(skin_index, 4)


        self.uv =float32_buffer_attribute(uv, 2)
        #geometry.computeBoundingSphere()
        #geometry.computeVertexNormals()

    def build_material(self):
        self.texture_map.build()

        if not self.texture_map.textures[0]:
            #self.material = MeshNormalMaterial(skinning=True)
            return

        self.material = Material(
            texture=self.texture_map.textures[0],
            vertex_color= "#fff"
        )

    def build_skeleton(self):
        skeleton_bones = []

        for i in range(self.num_bones):
            bone = Bone()
            bone.name = f"bone{i}"
            skeleton_bones.append(bone)

        for i in range(self.num_bones):
            parent = self.get_parent_bone(i)
            if parent:
                skeleton_bones[parent.id].add(skeleton_bones[i])
                skeleton_bones[i].position.x = -parent.length

        # IMPORTANT: update world matrices before creating skeleton
        for b in skeleton_bones:
            if b.parent is None:
                b.updateMatrixWorld(True)

        self.skeleton = Skeleton(skeleton_bones)

    def build_mesh(self):
        self.mesh = SkinnedMesh(self.geometry, self.material)
        self.mesh.add(self.skeleton.bones[0])
        self.mesh.bind(self.skeleton)
        self.mesh.rotation.x = 3.141592653589793

    # ───────────────────────── utils ─────────────────────────

    def get_parent_bone(self, bone_id):
        bone = self.bones[bone_id]
        return self.bones[bone.parent_id] if bone.parent_id < self.num_bones else None
