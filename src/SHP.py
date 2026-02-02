from src.WEP import WEP


class SHP(WEP):
    def __init__(self, reader):
        super().__init__(reader)

    def header(self):
        r = self.reader

        # inherited from WEP
        self.header1()

        self.overlay_x = []
        self.overlay_y = []
        self.width = []
        self.height = []

        for _ in range(8):
            self.overlay_x.append(r.u8())
            self.overlay_y.append(r.u8())
            self.width.append(r.u8())
            self.height.append(r.u8())

        r.skip(0x24)  # TODO unknown
        r.skip(0x06)  # TODO collision? not sure

        self.menu_position_y = r.s16()
        r.skip(0x0C)  # TODO unknown

        self.shadow_radius = r.s16()
        self.shadow_size_increase = r.s16()
        self.shadow_size_decrease = r.s16()
        r.skip(4)  # TODO

        self.menu_scale = r.s16()
        r.skip(2)  # TODO
        self.target_sphere_position_y = r.s16()
        r.skip(8)  # TODO

        self.anim_lbas = []
        for _ in range(0x0C):
            self.anim_lbas.append(r.u32())

        self.chain_ids = []
        for _ in range(0x0C):
            self.chain_ids.append(r.u16())

        self.special_lbas = []
        for _ in range(4):
            self.special_lbas.append(r.u32())

        r.skip(0x20)  # TODO unknown, more LBAs?

        self.magic_ptr = r.u32() + 0xF8
        r.skip(0x30)  # TODO whats this?
        self.akao_ptr = r.u32() + 0xF8
        self.group_ptr = r.u32() + 0xF8
        self.vertex_ptr = r.u32() + 0xF8
        self.face_ptr = r.u32() + 0xF8

    def data(self):
        r = self.reader

        # inherited sections
        self.bone_section()
        self.group_section()
        self.vertex_section()
        self.face_section()

        # TODO skip AKAO
        r.skip(self.magic_ptr - self.akao_ptr)

        # TODO skip magic section
        r.skip(4)
        length = r.u32()
        r.skip(length)

        # inherited
        self.texture_section(2, False)  # 2 palettes, not WEP
