import math
import os
from PIL import Image
from PySide6.QtGui import QQuaternion, QVector3D
import io
import numpy as np



# Constants
TIME_SCALE = 1
ROT13_TO_RAD = (1 / 4096) * math.pi


# --- Utility Functions ---

def parse_ext(path):
    """Returns the file extension in lowercase."""
    _, ext = os.path.splitext(path)
    return ext[1:].lower() if ext else None


def hex_fmt(i, pad):
    """Equivalent to JS hex(i, pad)"""
    return f"0x{i:0{pad}x}"

def hex(i, pad=0):
    x = format(i, 'x')

    while len(x) < pad:
        x = '0' + x

    return '0x' + x

def hex2(i):
    return hex_fmt(i, 2)


def bin_fmt(i, pad):
    """Equivalent to JS bin(i, pad)"""
    return f"0b{i:0{pad}b}"


def assert_val(expr, expected=None):
    if expected is not None:
        if expr != expected:
            raise AssertionError(f"Assertion failed: {expr} != {expected}")
    elif not expr:
        raise AssertionError("Assertion failed")


# --- Image Processing ---

def export_png(data, width, height, output_path="output.png", flip=False):
    """
    Converts raw RGBA byte data to a PNG file.
    Note: Python's PIL doesn't require the 'canvas flip' logic used in JS
    unless your source data is specifically bottom-to-top.
    """
    # Create image from bytes
    img = Image.frombytes("RGBA", (width, height), bytes(data))

    # The JS version performs a vertical flip during the loop.
    # To match that behavior exactly:
    if flip:
        img = img.transpose(Image.FLIP_TOP_BOTTOM)
    os.makedirs(os.path.split(output_path)[0], exist_ok=True)
    img.save(output_path)
    return output_path


def bytearray_to_image(buffer: bytearray, width: int, height: int, byte_depth=4) -> Image.Image:
    """
    Convert raw RGBA bytearray into a PIL Image.
    """


    expected_size = width * height * byte_depth
    if len(buffer) != expected_size:
        raise ValueError(
            f"Buffer size mismatch: got {len(buffer)}, expected {expected_size}"
        )

    if byte_depth == 4:
        img = Image.frombytes(
            mode="RGBA",
            size=(width, height),
            data=bytes(buffer)
        )
    else:
        img = Image.frombytes(
            mode="I;16",
            size=(width, height),
            data=bytes(buffer),
        )

    return img

def bytearray_to_image_rg8(buffer, width, height):
    expected = width * height * 2
    if len(buffer) != expected:
        raise ValueError("Size mismatch")

    arr = np.frombuffer(buffer, dtype=np.uint8)
    arr = arr.reshape((height, width, 2))

    # Expand to RGBA for display
    rgba = np.zeros((height, width, 4), dtype=np.uint8)
    rgba[..., 0] = arr[..., 0]  # R
    rgba[..., 1] = arr[..., 1]  # G
    rgba[..., 3] = 255          # A

    return Image.fromarray(rgba, "RGBA")


def flip_image(image):
    return image.transpose(Image.FLIP_TOP_BOTTOM)


def image_to_bytearray(image: Image) -> bytes:
  # BytesIO is a file-like buffer stored in memory
  imgByteArr = io.BytesIO()
  # image.save expects a file-like as a argument
  image.save(imgByteArr, format='PNG')
  # Turn the BytesIO object back into a bytes object
  imgByteArr = imgByteArr.getvalue()
  return bytearray(imgByteArr)


def parse_color(c):
    """
    Converts 16-bit PS1 color (BGR555) to RGBA list.
    """
    if c == 0:
        return [0, 0, 0, 0]

    # b = (c & 0x7c00) >> 10
    # g = (c & 0x03e0) >> 5
    # r = c & 0x001f
    b = (c >> 10) & 0x1F
    g = (c >> 5) & 0x1F
    r = c & 0x1F

    # 5bit -> 8bit is factor of 8
    return [r * 8, g * 8, b * 8, 255]




# --- Math & Rotations ---

def rot13_to_rad_func(angle):
    return angle * ROT13_TO_RAD

def time_to_frame(time_sec: float) -> int:
    return int(time_sec / TIME_SCALE)

def rot2quat(rx, ry, rz):
    """
    Matches Three.js:
    Q = Qz * (Qy * Qx)
    Apply X, then Y, then Z
    Angles are in radians
    """

    qx = QQuaternion.fromAxisAndAngle(QVector3D(1, 0, 0), math.degrees(rx))
    qy = QQuaternion.fromAxisAndAngle(QVector3D(0, 1, 0), math.degrees(ry))
    qz = QQuaternion.fromAxisAndAngle(QVector3D(0, 0, 1), math.degrees(rz))

    q = qz * (qy * qx)
    q.normalize()

    return (q.x(), q.y(), q.z(), q.scalar())

# --- Note on Mesh and Material Functions ---
# Functions like 'cloneMeshWithPose' and 'newVSMaterial' are deeply tied
# to the Three.js WebGL engine. In Python, there is no direct equivalent
# unless you are using a 3D engine like 'Panda3D' or 'PyOpenGL'.


def bit_merge(a, b):
    # Shift 'a' left by 32 bits and add 'b'
    return (a << 32) | b

def float32_buffer_attribute(buffer, shape):

    array = np.array(buffer, dtype=np.float32)
    return array.reshape((-1, shape))

def compute_vertex_normals(positions, indices, face_sizes):
    positions = np.asarray(positions, dtype=np.float32).reshape(-1, 3)
    normals = np.zeros_like(positions, dtype=np.float32)

    idx = 0
    for size in face_sizes:
        face = indices[idx:idx + size]
        idx += size

        if size == 3:
            tris = [face]
        elif size == 4:
            tris = [
                (face[0], face[1], face[2]),
                (face[0], face[2], face[3])
            ]
        else:
            raise ValueError("Only triangles and quads supported")

        for i0, i1, i2 in tris:
            v0, v1, v2 = positions[i0], positions[i1], positions[i2]
            face_normal = np.cross(v1 - v0, v2 - v0)

            normals[i0] += face_normal
            normals[i1] += face_normal
            normals[i2] += face_normal

    # Normalize
    lengths = np.linalg.norm(normals, axis=1)
    lengths[lengths == 0] = 1.0
    normals /= lengths[:, None]

    return normals.flatten()

