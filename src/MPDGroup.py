from src.MPDmesh import MPDMesh
from src.MPDFace import MPDFace

class MPDGroup:
    def __init__(self, reader, mpd):
        self.reader = reader
        self.mpd = mpd
        self.meshes = {}

    def read(self):
        self.header()
        self.data()

    def header(self):
        r = self.reader
        self.head = [r.u8() for _ in range(64)]

        if self.head[1] & 0x08:
            self.scale = 1
        else:
            self.scale = 8

    def data(self):
        r = self.reader

        self.triangle_count = r.u32()
        self.quad_count = r.u32()
        face_count = self.triangle_count + self.quad_count

        for _ in range(self.triangle_count):
            f = MPDFace(r, self)
            f.read(False)
            self.get_mesh(f.textureId, f.clutId).add(f)

        for _ in range(self.quad_count):
            f = MPDFace(r, self)
            f.read(True)
            self.get_mesh(f.textureId, f.clutId).add(f)

    def build(self):
        for mesh in self.meshes.values():
            mesh.build()

    def get_mesh(self, texture_id, clut_id):
        key = f"{texture_id}-{clut_id}"
        if key not in self.meshes:
            self.meshes[key] = MPDMesh(self.reader, self, texture_id, clut_id)
        return self.meshes[key]
