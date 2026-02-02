from OpenGL.GL import *

WIDTH = 1024
HEIGHT = 512


class FrameBuffer:
    def __init__(self):
        # Create a raw byte buffer (RGBA)
        self.buffer = bytearray(WIDTH * HEIGHT * 4)
        self.texture_id = None
        self._needs_update = False

    def set_pixel(self, x, y, c):
        """
        Sets a pixel in the buffer.
        c is expected to be [R, G, B, A] in range 0-255.
        """
        if 0 <= x < WIDTH and 0 <= y < HEIGHT:
            i = (y * WIDTH + x) * 4
            self.buffer[i + 0] = int(c[0])
            self.buffer[i + 1] = int(c[1])
            self.buffer[i + 2] = int(c[2])
            self.buffer[i + 3] = int(c[3])
            self._needs_update = True

    def init_texture(self):

        """Initializes the OpenGL texture for this buffer."""

        self.texture_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.texture_id)

        # PS1 style rendering usually requires Nearest filtering
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)

        # Initialize with empty data
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, WIDTH, HEIGHT, 0,
                     GL_RGBA, GL_UNSIGNED_BYTE, bytes(self.buffer))
        glBindTexture(GL_TEXTURE_2D, 0)



    def update_texture_gpu(self):
        """Uploads the current CPU buffer to the GPU if it has changed."""
        if not self._needs_update or self.texture_id is None:
            return

        glBindTexture(GL_TEXTURE_2D, self.texture_id)
        # glTexSubImage2D is faster than glTexImage2D for updating existing textures
        glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, WIDTH, HEIGHT,
                        GL_RGBA, GL_UNSIGNED_BYTE, bytes(self.buffer))
        glBindTexture(GL_TEXTURE_2D, 0)
        self._needs_update = False

    def mark_clut(self, clut_id):
        """Debug helper to highlight a specific CLUT area in the buffer."""
        ilo = clut_id * 64
        # Mark first 4 bytes red
        if ilo + 3 < len(self.buffer):
            self.buffer[ilo + 0] = 255
            self.buffer[ilo + 1] = 0
            self.buffer[ilo + 2] = 0
            self.buffer[ilo + 3] = 255
            self._needs_update = True

    def build(self):
        """
        In JS, this creates a Three.js Mesh.
        In your Python GL_Viewer, you would instead bind self.texture_id
        when drawing your quad/mesh.
        """
        pass
        #self.init_texture()