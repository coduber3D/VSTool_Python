from src.VSTOOLS import hex2
class Reader:
    def __init__(self, data):
        """
        data: bytes | bytearray | list[int]
        """
        self.data = data
        self.pos = 0

        # Match JS Int8Array behavior
        self.type = [0] * len(data)
        self.info = [0] * len(data)

    # -------------------------
    # Position control
    # -------------------------

    def seek(self, i):
        self.pos = i
        return self

    def skip(self, i):
        self.pos += i
        return self

    # -------------------------
    # Integer reads
    # -------------------------

    def u8(self):
        if self.pos >= len(self.data):
            raise IndexError("Out of bounds")

        r = self.data[self.pos]
        self.type[self.pos] = 1
        self.pos += 1
        return r

    def s8(self):
        r = self.u8()
        # sign extend
        if r & 0x80:
            r -= 0x100
        self.type[self.pos - 1] = -1
        return r

    def s16(self):
        r = self.u8() | (self.s8() << 8)
        self.type[self.pos - 1] = -2
        self.type[self.pos - 2] = -2
        return r

    def s16big(self):
        r = (self.s8() << 8) | self.u8()
        self.type[self.pos - 1] = -20
        self.type[self.pos - 2] = -20
        return r

    def u16(self):
        r = self.s16() & 0xFFFF
        self.type[self.pos - 1] = 2
        self.type[self.pos - 2] = 2
        return r

    def s32(self):
        r = (
            self.u8()
            | (self.u8() << 8)
            | (self.u8() << 16)
            | (self.u8() << 24)
        )

        # sign extend 32-bit
        if r & 0x80000000:
            r -= 0x100000000

        for i in range(4):
            self.type[self.pos - 1 - i] = -4

        return r

    def u32(self):
        r = self.s32()

        if r < 0:
            raise ValueError("Got unsigned int > 0x7fffffff")

        for i in range(4):
            self.type[self.pos - 1 - i] = 4

        return r

    # -------------------------
    # Buffers & validation
    # -------------------------

    def buffer(self, length):
        arr = []
        for _ in range(length):
            arr.append(self.u8())
            self.type[self.pos - 1] = 3
        return arr

    def constant(self, expected_bytes):
        actual = self.buffer(len(expected_bytes))

        for i, (a, e) in enumerate(zip(actual, expected_bytes)):
            if a != e:
                raise ValueError(
                    f"Expected {expected_bytes}, got {actual}"
                )
            self.type[self.pos - i - 1] = 5

        return self

    def padding(self, length, byte=0):
        actual = self.buffer(length)

        for i, b in enumerate(actual):
            if b != byte:
                raise ValueError(
                    f"Expected padding {hex2(byte)} ({length}), got "
                    + " ".join(hex2(x) for x in actual)
                )
            self.type[self.pos - i - 1] = 7

        return self

    # -------------------------
    # Debug marking
    # -------------------------

    def mark(self, i=1, offset=0):
        idx = self.pos + offset
        if 0 <= idx < len(self.info):
            self.info[idx] = i
        return self
