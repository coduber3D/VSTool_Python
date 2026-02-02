from src.TIM import TIM
from src.FrameBuffer import FrameBuffer
from src.VSTOOLS import bytearray_to_image, bit_merge


class ZND:
    def __init__(self, reader):
        self.reader = reader
        self.materials = {}   # cache: textureId-clutId → texture
        self.textures = []    # list of built textures (for UI / debug)

        self.frameBuffer = None
        self.tims = []

    # ------------------------
    # Read
    # ------------------------

    def read(self):
        self.header()
        self.data()

    def header(self):
        r = self.reader

        self.mpdPtr = r.u32()
        self.mpdLen = r.u32()
        self.mpdNum = self.mpdLen // 8

        self.enemyPtr = r.u32()
        self.enemyLen = r.u32()

        self.timPtr = r.u32()
        self.timLen = r.u32()

        self.wave = r.u8()
        r.skip(7)  # unknown padding

    def data(self):
        self.mpd_section()
        self.enemies_section()
        self.tim_section()

    # ------------------------
    # MPD section
    # ------------------------

    def mpd_section(self):
        r = self.reader

        self.mpdLBAs = []
        self.mpdSizes = []

        for _ in range(self.mpdNum):
            self.mpdLBAs.append(r.u32())
            self.mpdSizes.append(r.u32())

    # ------------------------
    # Enemies (skipped)
    # ------------------------

    def enemies_section(self):
        self.reader.skip(self.enemyLen)

    # ------------------------
    # TIM section
    # ------------------------

    def tim_section(self):
        r = self.reader

        self.timLen2 = r.u32()
        r.skip(12)  # unknown, usually zero
        self.timNum = r.u32()

        self.frameBuffer = FrameBuffer()
        self.tims = []

        for i in range(self.timNum):
            r.u32()  # TIM length (unused)

            tim = TIM(r)
            tim.read()
            tim.id = i

            # Small TIMs sometimes contain CLUTs
            if tim.height < 5:
                tim.copy_to_framebuffer(self.frameBuffer)

            tim.copy_to_framebuffer(self.frameBuffer)
            self.tims.append(tim)

    # ------------------------
    # TIM / CLUT lookup
    # ------------------------

    def get_tim(self, texture_id):
        x = (texture_id * 64) % 1024

        for tim in self.tims:
            if tim.fx == x:
                return tim

        return None

    # ------------------------
    # Texture builder (material equivalent)
    # ------------------------

    def get_materials(self, texture_id, clut_id):
        """
        Returns a built RGBA texture (cached).
        """
        key = f"{texture_id}-{clut_id}"

        if key in self.materials:
            return self.materials[key]

        texture_tim = self.get_tim(texture_id)
        if texture_tim is None:
            return None

        # Mark CLUT usage in framebuffer (debug / tracking)
        self.frameBuffer.mark_clut(clut_id)

        # Locate CLUT in framebuffer
        x = (clut_id * 16) % 1024
        y = (clut_id * 16) // 1024

        clut = None

        for tim in self.tims:
            if (
                tim.fx <= x < tim.fx + tim.width and
                tim.fy <= y < tim.fy + tim.height
            ):
                clut = tim.build_clut(x, y)
                break
        if clut:
            texture = texture_tim.build(clut)
        #texture.title = key

            self.textures.append(texture)
            self.materials[key] = texture

            return texture
