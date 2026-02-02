from src.SEQAnimation import SEQAnimation


class SEQ:
    def __init__(self, reader):
        self.reader = reader

    def read(self):
        self.header()
        self.data()

    def header(self):
        r = self.reader

        # base ptr needed because SEQ may be embedded
        self.base_offset = r.pos

        self.num_slots = r.u16()   # 'slots' is just some random name, purpose unknown
        self.num_bones = r.u8()
        r.padding(1)

        self.size = r.u32()        # file size
        self.data_offset = r.u32() + 8    # offset to animation data
        self.slot_offset = r.u32() + 8    # offset to slots
        self.header_offset = self.slot_offset + self.num_slots
        # offset to rotation and keyframe data

    def data(self):
        r = self.reader

        header_offset = self.header_offset

        # number of animations has to be computed
        # length of all headers / length of one animation header
        self.num_animations = (
            (header_offset - self.num_slots - 16)
            // (self.num_bones * 4 + 10)
        )

        # read animation headers
        self.animations = []

        for i in range(self.num_animations):
            animation = SEQAnimation(self.reader, self)
            animation.header(i)
            self.animations.append(animation)

        # read "slots"
        # these are animation ids, usable as self.animations[id]
        self.slots = []

        for _ in range(self.num_slots):
            slot = r.u8()

            if slot >= self.num_animations and slot != 255:
                raise RuntimeError("Invalid animation slot")

            self.slots.append(slot)

        # read animation data
        for animation in self.animations:
            animation.data()

    def build(self):
        for animation in self.animations:
            animation.build()

    def ptr_data(self, i):
        return i + self.header_offset + self.base_offset
