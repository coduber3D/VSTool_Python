from src.VSTOOLS import hex, parse_color


class WEPVertex:
    def __init__(self, reader):
        self.reader = reader
        self.x = None
        self.y = None
        self.z = None

    def read(self):
        r = self.reader

        self.x = r.s16()
        self.y = r.s16()
        self.z = r.s16()
        r.padding(2)

class WEPFace:
    def __init__(self, reader):
        self.reader = reader

    def read(self):
        r = self.reader

        self.type = r.u8()  # 1

        if self.type != 0x24 and self.type != 0x2C:
            raise ValueError(f"Unknown face type: {hex(self.type)}")

        self.size = r.u8()  # 2
        self.info = r.u8()  # 3
        r.skip(1)           # TODO whats this? 4

        self.vertex1 = r.u16() // 4  # 6
        self.vertex2 = r.u16() // 4  # 8
        self.vertex3 = r.u16() // 4  # 10

        if self.quad():
            self.vertex4 = r.u16() // 4  # + 2

        self.u1 = r.u8()  # 11
        self.v1 = r.u8()  # 12
        self.u2 = r.u8()  # 13
        self.v2 = r.u8()  # 14
        self.u3 = r.u8()  # 15
        self.v3 = r.u8()  # 16

        if self.quad():
            self.u4 = r.u8()  # + 3
            self.v4 = r.u8()  # + 4

        # size of triangle is 16, quad is 20

        # default vertex color is 0x80
        self.r1 = self.g1 = self.b1 = 0x80
        self.r2 = self.g2 = self.b2 = 0x80
        self.r3 = self.g3 = self.b3 = 0x80

        if self.quad():
            self.r4 = self.g4 = self.b4 = 0x80

    def read_colored(self):
        r = self.reader

        self.type = r.data[r.pos + 11]

        if self.type == 0x34:
            return self.read_triangle_colored()
        elif self.type == 0x3C:
            return self.read_quad_colored()
        else:
            raise ValueError(f"Unknown face type: {hex(self.type)}")

    def read_triangle_colored(self):
        r = self.reader

        self.vertex1 = r.u16() // 4
        self.vertex2 = r.u16() // 4
        self.vertex3 = r.u16() // 4

        self.u1 = r.u8()
        self.v1 = r.u8()

        self.r1 = r.u8()
        self.g1 = r.u8()
        self.b1 = r.u8()
        r.constant([0x34])  # type

        self.r2 = r.u8()
        self.g2 = r.u8()
        self.b2 = r.u8()
        self.size = r.u8()

        self.r3 = r.u8()
        self.g3 = r.u8()
        self.b3 = r.u8()
        self.info = r.u8()

        self.u2 = r.u8()
        self.v2 = r.u8()
        self.u3 = r.u8()
        self.v3 = r.u8()

        # 28 bytes total

    def read_quad_colored(self):
        r = self.reader

        self.vertex1 = r.u16() // 4
        self.vertex2 = r.u16() // 4
        self.vertex3 = r.u16() // 4
        self.vertex4 = r.u16() // 4

        self.r1 = r.u8()
        self.g1 = r.u8()
        self.b1 = r.u8()
        r.constant([0x3C])  # type

        self.r2 = r.u8()
        self.g2 = r.u8()
        self.b2 = r.u8()
        self.size = r.u8()

        self.r3 = r.u8()
        self.g3 = r.u8()
        self.b3 = r.u8()
        self.info = r.u8()

        self.r4 = r.u8()
        self.g4 = r.u8()
        self.b4 = r.u8()
        r.skip(1)  # always 0x00 except for B1.SHP (0x01)

        self.u1 = r.u8()
        self.v1 = r.u8()
        self.u2 = r.u8()
        self.v2 = r.u8()

        self.u3 = r.u8()
        self.v3 = r.u8()
        self.u4 = r.u8()
        self.v4 = r.u8()

        # 36 bytes total

    def quad(self):
        return self.type in (0x2C, 0x3C)

    def double(self):
        return self.info == 0x05


class WEPBone:
    def __init__(self, reader, id):
        self.reader = reader
        self.id = id

        self.length = None
        self.parent_id = None
        self.group_id = None
        self.mount_id = None
        self.body_part_id = None
        self.mode = None
        self.u1 = None
        self.u2 = None
        self.u3 = None

    def read(self):
        r = self.reader

        self.length = r.s32()
        self.parent_id = r.s8()
        self.group_id = r.s8()   # doubly linked (groups reference bones as well)
        self.mount_id = r.u8()   # for mounting weapons etc.
        self.body_part_id = r.u8()

        # TODO mode
        # 0 - 2 normal ?
        # 3 - 6 normal + roll 90 degrees
        # 7 - 255 absolute, different angles
        # values found in the game: 0, 1, 2, 3, 4, 5, 6, 7, 8
        self.mode = r.s8()

        # print(self.id, self.mode, self.length, self.parent_id)

        self.u1 = r.u8()  # TODO unknown
        self.u2 = r.u8()  # TODO unknown
        self.u3 = r.u8()  # TODO unknown
        r.padding(4)

        if self.u1 != 0 or self.u2 != 0 or self.u3 != 0:
            # print(self.id, self.mode, self.u1, self.u2, self.u3)
            pass



class WEPGroup:
    def __init__(self, reader, id):
        self.reader = reader
        self.id = id

        self.bone_id = None
        self.last_vertex = None

    def read(self):
        r = self.reader

        self.bone_id = r.s16()
        self.last_vertex = r.u16()




class WEPPalette:
    def __init__(self, reader):
        self.reader = reader
        self.colors = []

    def read(self, num):
        r = self.reader

        for _ in range(num):
            self.colors.append(parse_color(r.u16()))

    def add(self, colors):
        self.colors.extend(colors)


# from three import DataTexture, RGBAFormat, NearestFilter, RepeatWrapping
# from WEPPalette import WEPPalette


class WEPTextureMap:
    def __init__(self, reader):
        self.map = None
        self.textures = None
        self.palettes = None
        self.colors_per_palette = None
        self.height = None
        self.width = None
        self.version = None
        self.size = None
        self.reader = reader

    def read(self, number_of_palettes, wep):
        r = self.reader

        self.size = r.u32()

        # version
        # always 1 for WEP
        # SHP and ZUD may have different values
        # 16 is notably used for SHPs with vertex colors
        self.version = r.u8()

        self.width = r.u8() * 2
        self.height = r.u8() * 2
        self.colors_per_palette = r.u8()

        self.palettes = []

        handle = None
        if wep:
            handle = WEPPalette(self.reader)
            handle.read(self.colors_per_palette // 3)

        for _ in range(number_of_palettes):
            palette = WEPPalette(self.reader)

            if wep:
                palette.add(handle.colors)
                palette.read((self.colors_per_palette // 3) * 2)
            else:
                palette.read(self.colors_per_palette)
            #palette.colors[0] = [255, 0, 255, 255]
            self.palettes.append(palette)

        self.map = []

        for y in range(self.height):
            for x in range(self.width):
                if x >= len(self.map):
                    self.map.append([])
                self.map[x].append(r.u8())

    def build(self):
        self.textures = []

        for palette in self.palettes:
            if self.version == 1:
                texture = self.build_v1(palette)
            elif self.version == 16:
                texture = self.build_v16(palette)
            else:
                texture = None  # TODO

            if texture:
                '''texture.magFilter = NearestFilter
                texture.minFilter = NearestFilter
                texture.wrapS = RepeatWrapping
                texture.wrapT = RepeatWrapping
                texture.needsUpdate = True'''

                self.textures.append(texture)

    def build_v1(self, palette):
        buffer = bytearray()

        for y in range(self.height):
            for x in range(self.width):
                c = self.map[x][y]

                # TODO sometimes c >= colorsPerPalette
                if c < self.colors_per_palette:
                    r, g, b, a = palette.colors[c]
                    buffer.extend((r, g, b, a))
                else:
                    buffer.extend((0, 0, 0, 0))

        return {
            "data": buffer,
            "width": self.width,
            "height": self.height
        }

    def build_v16(self, palette):
        buffer = bytearray()

        for y in range(self.height):
            for x in range(self.width):
                c = self.map[x][y]

                hi = c >> 4
                lo = c & 0xF

                if lo < self.colors_per_palette:
                    r, g, b, a = palette.colors[lo]
                    buffer.extend((r, g, b, a))
                else:
                    buffer.extend((0, 0, 0, 0))

                if hi < self.colors_per_palette:
                    r, g, b, a = palette.colors[hi]
                    buffer.extend((r, g, b, a))
                else:
                    buffer.extend((0, 0, 0, 0))

        return {
            "data": buffer,
            "width": self.width * 2,
            "height": self.height
        }


    def get_width(self):
        return self.width * 2 if self.version == 16 else self.width
