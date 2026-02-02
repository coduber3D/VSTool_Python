import random
import numpy as np
from src.VSTOOLS import parse_color, bytearray_to_image, flip_image, image_to_bytearray
from PIL import Image
import io

class TIM:
    def __init__(self, reader):
        self.reader = reader
        self.magic = None
        self.bpp = 0
        self.img_len = 0
        self.data_len = 0
        self.fx = 0
        self.fy = 0
        self.width = 0
        self.height = 0
        self.data_ptr = 0

    def read(self):
        r = self.reader

        r.skip(4)  # magic 10 00 00 00
        self.bpp = r.u32()
        self.img_len = r.u32()
        self.data_len = self.img_len - 12

        self.fx = r.u16()
        self.fy = r.u16()
        self.width = r.u16()
        self.height = r.u16()

        self.data_ptr = r.pos
        r.skip(self.data_len)

    def copy_to_framebuffer(self, fb):
        r = self.reader
        r.seek(self.data_ptr)

        for y in range(self.height):
            for x in range(self.width):
                c = parse_color(r.s16())
                fb.set_pixel(self.fx + x, self.fy + y, c)

    def mark_framebuffer(self, fb):
        c = [
            255,
            int(random.random() * 255),
            int(random.random() * 255),
            int(random.random() * 255),
        ]

        for y in range(self.height):
            for x in range(self.width):
                fb.set_pixel(self.fx + x, self.fy + y, c)

    def build_clut(self, x, y):
        r = self.reader
        ox = x - self.fx
        oy = y - self.fy

        r.seek(self.data_ptr + (oy * self.width + ox) * 2)

        # 16 colors * 4 bytes (RGBA) = 64
        buffer = bytearray(64)

        for i in range(0, 64, 4):
            c = parse_color(r.s16())
            buffer[i + 0] = c[0]
            buffer[i + 1] = c[1]
            buffer[i + 2] = c[2]
            buffer[i + 3] = c[3]

        return buffer

    def build(self, clut):
        r = self.reader
        r.seek(self.data_ptr)

        # 4-bit indexed texture logic:
        # Each byte contains 2 pixels, each pixel expands to 4 bytes RGBA
        # (width * height * 2 pixels per byte) * 4 bytes per pixel = size * 8
        # The JS uses width * height * 16, which implies 4 pixels per "unit"
        size = self.width * self.height * 16
        buffer = bytearray(size)

        for i in range(0, size, 8):
            c = r.u8()

            # Split byte into high and low nibbles (4-bit indices)
            hi = ((c & 0xF0) >> 4) * 4
            lo = (c & 0x0F) * 4

            # Pixel 1 (Lower nibble)
            buffer[i + 0:i + 4] = clut[lo:lo + 4]
            # Pixel 2 (Higher nibble)
            buffer[i + 4:i + 8] = clut[hi:hi + 4]

        # In Python, 'texture' would usually be a PIL Image or a NumPy array
        # since DataTexture is Three.js specific.

        return {
            "data": buffer,
            "width": self.width * 4,  # Adjusting for the 4-bit expansion
            "height": self.height
        }

