from src.MPDGroup import MPDGroup

class MPD:
    def __init__(self, reader, znd=None):
        self.reader = reader
        self.znd = znd

    def read(self):
        self.header()
        self.room_header()
        self.room_section()
        # self.cleared_section()
        # self.script_section()

    # ------------------------
    # Header
    # ------------------------

    def header(self):
        r = self.reader

        self.ptrRoomSection = r.u32()
        self.lenRoomSection = r.u32()
        self.ptrClearedSection = r.u32()
        self.lenClearedSection = r.u32()
        self.ptrScriptSection = r.u32()
        self.lenScriptSection = r.u32()
        self.ptrDoorSection = r.u32()
        self.lenDoorSection = r.u32()
        self.ptrEnemySection = r.u32()
        self.lenEnemySection = r.u32()
        self.ptrTreasureSection = r.u32()
        self.lenTreasureSection = r.u32()

    # ------------------------
    # Room Header
    # ------------------------

    def room_header(self):
        r = self.reader

        self.lenGeometrySection = r.u32()
        self.lenCollisionSection = r.u32()
        self.lenSubSection03 = r.u32()
        self.lenDoorSectionRoom = r.u32()
        self.lenLightingSection = r.u32()

        self.lenSubSection06 = r.u32()
        self.lenSubSection07 = r.u32()
        self.lenSubSection08 = r.u32()
        self.lenSubSection09 = r.u32()
        self.lenSubSection0A = r.u32()
        self.lenSubSection0B = r.u32()

        self.lenTextureEffectsSection = r.u32()

        self.lenSubSection0D = r.u32()
        self.lenSubSection0E = r.u32()
        self.lenSubSection0F = r.u32()
        self.lenSubSection10 = r.u32()
        self.lenSubSection11 = r.u32()
        self.lenSubSection12 = r.u32()
        self.lenSubSection13 = r.u32()

        self.lenAKAOSubSection = r.u32()

        self.lenSubSection15 = r.u32()
        self.lenSubSection16 = r.u32()
        self.lenSubSection17 = r.u32()
        self.lenSubSection18 = r.u32()

    # ------------------------
    # Room Sections
    # ------------------------

    def room_section(self):
        self.geometry_section()
        self.collision_section()
        self.sub_section_03()
        self.door_section_room()
        self.lighting_section()
        self.sub_section_06()
        self.sub_section_07()
        self.sub_section_08()
        self.sub_section_09()
        self.sub_section_0A()
        self.sub_section_0B()
        self.texture_effects_section()
        self.sub_section_0D()
        self.sub_section_0E()
        self.sub_section_0F()
        self.sub_section_10()
        self.sub_section_11()
        self.sub_section_12()
        self.sub_section_13()
        self.akao_sub_section()
        self.sub_section_15()
        self.sub_section_16()
        self.sub_section_17()
        self.sub_section_18()

    # ------------------------
    # Geometry
    # ------------------------

    def geometry_section(self):
        r = self.reader

        self.numGroups = r.u32()
        self.groups = []

        # read group headers
        for _ in range(self.numGroups):
            g = MPDGroup(self.reader, self)
            g.header()
            self.groups.append(g)

        # read group data
        for g in self.groups:
            g.data()

    # ------------------------
    # Skipped sections
    # ------------------------

    def collision_section(self):
        self.reader.skip(self.lenCollisionSection)

    def sub_section_03(self):
        self.reader.skip(self.lenSubSection03)

    def door_section_room(self):
        self.reader.skip(self.lenDoorSectionRoom)

    def lighting_section(self):
        self.reader.skip(self.lenLightingSection)

    def sub_section_06(self):
        self.reader.skip(self.lenSubSection06)

    def sub_section_07(self):
        self.reader.skip(self.lenSubSection07)

    def sub_section_08(self):
        self.reader.skip(self.lenSubSection08)

    def sub_section_09(self):
        self.reader.skip(self.lenSubSection09)

    def sub_section_0A(self):
        self.reader.skip(self.lenSubSection0A)

    def sub_section_0B(self):
        self.reader.skip(self.lenSubSection0B)

    def texture_effects_section(self):
        self.reader.skip(self.lenTextureEffectsSection)

    def sub_section_0D(self):
        self.reader.skip(self.lenSubSection0D)

    def sub_section_0E(self):
        self.reader.skip(self.lenSubSection0E)

    def sub_section_0F(self):
        self.reader.skip(self.lenSubSection0F)

    def sub_section_10(self):
        self.reader.skip(self.lenSubSection10)

    def sub_section_11(self):
        self.reader.skip(self.lenSubSection11)

    def sub_section_12(self):
        self.reader.skip(self.lenSubSection12)

    def sub_section_13(self):
        self.reader.skip(self.lenSubSection13)

    def akao_sub_section(self):
        self.reader.skip(self.lenAKAOSubSection)

    def sub_section_15(self):
        self.reader.skip(self.lenSubSection15)

    def sub_section_16(self):
        self.reader.skip(self.lenSubSection16)

    def sub_section_17(self):
        self.reader.skip(self.lenSubSection17)

    def sub_section_18(self):
        self.reader.skip(self.lenSubSection18)

    # ------------------------
    # Optional Sections
    # ------------------------

    def cleared_section(self):
        self.reader.skip(self.lenClearedSection)

    def script_section(self):
        r = self.reader

        r.u16()  # length
        self.ptrDialogText = r.u16()
        r.skip(self.ptrDialogText)

        data = r.buffer(700)
        # Text.convert(data, 700)  # left unimplemented

    # ------------------------
    # Build
    # ------------------------

    def build(self):
        """
        Builds all geometry buffers.
        Result:
          self.meshes → list of MPDMesh
        """
        self.meshes = []

        for g in self.groups:
            g.build()
            for mesh in g.meshes.values():
                self.meshes.append(mesh)

    def set_material(self, material):
        """
        Placeholder for compatibility with JS version.
        """
        for g in self.groups:
            for mesh in g.meshes.values():
                mesh.material = material
