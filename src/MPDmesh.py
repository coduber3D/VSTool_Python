from src.V3DClasses import *
from src.VSTOOLS import bit_merge
import math



class MPDMesh:
    def __init__(self, reader, group, texture_id, clut_id):
        self.reader = reader
        self.group = group
        self.texture_id = texture_id
        self.clut_id = clut_id
        self.faces = []

        self.positions = []
        self.colors = []
        self.uvs = []
        self.normals = []
        self.indices = []

    def add(self, face):
        self.faces.append(face)

    def build(self):
        tw = 256
        th = 256

        self.positions = []
        self.normals = []
        self.colors = []
        self.uvs = []
        self.indices = []

        iv = 0

        for f in self.faces:
            f.build()

            if f.quad:
                verts = [f.p1, f.p2, f.p3, f.p4]
                cols = [
                    (f.r1, f.g1, f.b1),
                    (f.r2, f.g2, f.b2),
                    (f.r3, f.g3, f.b3),
                    (f.r4, f.g4, f.b4),
                ]
                uvs = [
                    (f.u2, f.v2),
                    (f.u3, f.v3),
                    (f.u1, f.v1),
                    (f.u4, f.v4),
                ]

                # same winding as JS
                self.indices += [
                    iv + 2, iv + 1, iv + 0,
                    iv + 1, iv + 2, iv + 3
                ]
                iv += 4

            else:
                verts = [f.p1, f.p2, f.p3]
                cols = [
                    (f.r1, f.g1, f.b1),
                    (f.r2, f.g2, f.b2),
                    (f.r3, f.g3, f.b3),
                ]
                uvs = [
                    (f.u2, f.v2),
                    (f.u3, f.v3),
                    (f.u1, f.v1),
                ]

                self.indices += [iv + 2, iv + 1, iv + 0]
                iv += 3

            # positions + normals
            for v in verts:
                self.positions += [v.x, v.y, v.z]
                self.normals += [f.n.x, f.n.y, f.n.z]

            # colors
            for r, g, b in cols:
                self.colors += [r / 255.0, g / 255.0, b / 255.0]

            # UVs
            for u, v in uvs:
                self.uvs += [u / tw, v / th]

        # ---- Geometry (BufferGeometry equivalent) ----
        self.geometry = Geometry()
        self.geometry.attributes["positions"] = self.positions
        self.geometry.attributes["normals"] = self.normals
        self.geometry.attributes["indices"] = self.indices
        self.geometry.attributes["colors"] = self.colors
        self.geometry.attributes["uvs"] = self.uvs



        # ---- Material resolution (ZND) ----
        if self.group and self.group.mpd and self.group.mpd.znd:
            self.material = self.group.mpd.znd.get_materials(
                self.texture_id,
                self.clut_id
            )
            self.material_id = f"{self.texture_id}-{self.clut_id}"
        else:
            self.material = None  # fallback (normal/debug)
            self.material_id = "0"

            # ---- Transform (matches JS) ----
        self.rotation_x = math.pi
        self.scale = (0.1, 0.1, 0.1)