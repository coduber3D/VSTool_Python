import math

class Vector3:
    def __init__(self, x=0, y=0, z=0):
        self.x = x
        self.y = y
        self.z = z

    def cross(self, other):
        return Vector3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x
        )

    def normalize(self):
        l = math.sqrt(self.x**2 + self.y**2 + self.z**2)
        if l > 0:
            self.x /= l
            self.y /= l
            self.z /= l

    def negate(self):
        self.x *= -1
        self.y *= -1
        self.z *= -1


class MPDFace:
    def __init__(self, reader, group):
        self.reader = reader
        self.group = group

    def read(self, quad: bool):
        r = self.reader
        self.quad = quad

        self.p1x = r.s16()
        self.p1y = r.s16()
        self.p1z = r.s16()

        self.p2x = r.s8()
        self.p2y = r.s8()
        self.p2z = r.s8()

        self.p3x = r.s8()
        self.p3y = r.s8()
        self.p3z = r.s8()

        self.r1 = r.u8()
        self.g1 = r.u8()
        self.b1 = r.u8()

        self.type = r.u8()

        self.r2 = r.u8()
        self.g2 = r.u8()
        self.b2 = r.u8()

        self.u1 = r.u8()

        self.r3 = r.u8()
        self.g3 = r.u8()
        self.b3 = r.u8()

        self.v1 = r.u8()
        self.u2 = r.u8()
        self.v2 = r.u8()

        self.clutId = r.u16()

        self.u3 = r.u8()
        self.v3 = r.u8()

        self.textureId = r.s16()

        if quad:
            self.p4x = r.s8()
            self.p4y = r.s8()
            self.p4z = r.s8()

            self.u4 = r.u8()

            self.r4 = r.u8()
            self.g4 = r.u8()
            self.b4 = r.u8()

            self.v4 = r.u8()

    def build(self):
        s = self.group.scale

        self.p1 = Vector3(self.p1x, self.p1y, self.p1z)

        self.p2 = Vector3(
            self.p2x * s + self.p1x,
            self.p2y * s + self.p1y,
            self.p2z * s + self.p1z
        )

        self.p3 = Vector3(
            self.p3x * s + self.p1x,
            self.p3y * s + self.p1y,
            self.p3z * s + self.p1z
        )

        if self.quad:
            self.p4 = Vector3(
                self.p4x * s + self.p1x,
                self.p4y * s + self.p1y,
                self.p4z * s + self.p1z
            )

        n = Vector3(self.p2x, self.p2y, self.p2z)
        n = n.cross(Vector3(self.p3x, self.p3y, self.p3z))
        n.normalize()
        n.negate()

        self.n = n
