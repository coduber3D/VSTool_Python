from src.VSTOOLS import hex2, rot2quat, rot13_to_rad_func
import math

ACTIONS = {
    0x01: ("loop", 0),
    0x02: ("0x02", 0),
    0x04: ("0x04", 1),
    0x0A: ("0x0a", 1),
    0x0B: ("0x0b", 0),
    0x0C: ("0x0c", 1),
    0x0D: ("0x0d", 0),
    0x0F: ("0x0f", 1),
    0x13: ("unlockBone", 1),
    0x14: ("0x14", 1),
    0x15: ("0x15", 1),
    0x16: ("0x16", 2),
    0x17: ("0x17", 0),
    0x18: ("0x18", 0),
    0x19: ("0x19", 0),
    0x1A: ("0x1a", 1),
    0x1B: ("0x1b", 1),
    0x1C: ("0x1c", 1),
    0x1D: ("paralyze?", 0),
    0x24: ("0x24", 2),
    0x27: ("0x27", 4),
    0x34: ("0x34", 3),
    0x35: ("0x35", 5),
    0x36: ("0x36", 3),
    0x37: ("0x37", 1),
    0x38: ("0x38", 1),
    0x39: ("0x39", 1),
    0x3A: ("disappear", 0),
    0x3B: ("land", 0),
    0x3C: ("adjustShadow", 1),
    0x3F: ("0x3f", 0),
    0x40: ("0x40", 0),
}

class SEQAnimation:
    def __init__(self, reader, seq):
        self.reader = reader
        self.seq = seq

    # -----------------
    # Header
    # -----------------

    def header(self, anim_id):
        r = self.reader

        self.id = anim_id
        self.length = r.u16()

        # base animation pose
        self.base_animation_id = r.s8()

        # scale key flags
        self.scale_flags = r.u8()

        self.ptr_actions = r.u16()
        self.ptr_translation = r.u16()

        r.padding(2)

        self.ptr_bone_rotation = [
            r.u16() for _ in range(self.seq.num_bones)
        ]

        self.ptr_bone_scale = [
            r.u16() for _ in range(self.seq.num_bones)
        ]

    # -----------------
    # Data
    # -----------------

    def data(self):
        r = self.reader

        # translation
        r.seek(self.seq.ptr_data(self.ptr_translation))
        self.translation = self.read_xyz()
        self.translation_keys = self.read_keys()

        if self.ptr_actions > 0:
            r.seek(self.seq.ptr_data(self.ptr_actions))
            self.read_actions()

        self.rotation_per_bone = []
        self.rotation_keys_per_bone = []
        self.scale_per_bone = []
        self.scale_keys_per_bone = []

        for i in range(self.seq.num_bones):
            r.seek(self.seq.ptr_data(self.ptr_bone_rotation[i]))

            if self.base_animation_id == -1:
                self.rotation_per_bone.append(self.read_xyz())
            else:
                self.rotation_per_bone.append(None)

            self.rotation_keys_per_bone.append(self.read_keys())

            r.seek(self.seq.ptr_data(self.ptr_bone_scale[i]))

            if self.scale_flags & 0x1:
                self.scale_per_bone.append({
                    "x": r.u8(),
                    "y": r.u8(),
                    "z": r.u8(),
                })
            else:
                self.scale_per_bone.append(None)

            if self.scale_flags & 0x2:
                self.scale_keys_per_bone.append(self.read_keys())
            else:
                self.scale_keys_per_bone.append(None)

    # -----------------
    # Keyframes
    # -----------------

    def read_keys(self):
        keys = [{"f": 0, "x": 0, "y": 0, "z": 0}]
        f_accum = 0

        while True:
            key = self.read_key()
            if key is None:
                break

            keys.append(key)
            f_accum += key["f"]

            if f_accum >= self.length - 1:
                break

        return keys

    def read_key(self):
        r = self.reader

        code = r.u8()
        if code == 0x00:
            return None

        f = x = y = z = None

        if (code & 0xE0) > 0:
            f = code & 0x1F
            f = (0x20 + r.u8()) if f == 0x1F else (1 + f)
        else:
            f = code & 0x03
            f = (4 + r.u8()) if f == 0x03 else (1 + f)

            code <<= 3
            h = r.s16big()

            if h & 0x4:
                x = h >> 3
                code &= 0x60
                if h & 0x2:
                    y = r.s16big()
                    code &= 0xA0
                if h & 0x1:
                    z = r.s16big()
                    code &= 0xC0
            elif h & 0x2:
                y = h >> 3
                code &= 0xA0
                if h & 0x1:
                    z = r.s16big()
                    code &= 0xC0
            elif h & 0x1:
                z = h >> 3
                code &= 0xC0

        if code & 0x80:
            if x is not None:
                raise RuntimeError("Unexpected x")
            x = r.s8()

        if code & 0x40:
            if y is not None:
                raise RuntimeError("Unexpected y")
            y = r.s8()

        if code & 0x20:
            if z is not None:
                raise RuntimeError("Unexpected z")
            z = r.s8()

        return {"f": f, "x": x, "y": y, "z": z}

    # -----------------
    # Actions
    # -----------------

    def read_actions(self):
        r = self.reader
        self.actions = []

        while True:
            f = r.u8()
            if f == 0xFF:
                break

            if f > self.length:
                raise RuntimeError(
                    f"Unexpected frame {hex2(f)} > {self.length}"
                )

            a = r.u8()
            if a == 0x00:
                return

            if a not in ACTIONS:
                raise RuntimeError(f"Unknown SEQ action {hex2(a)} at frame {f}")

            name, param_count = ACTIONS[a]
            params = [r.u8() for _ in range(param_count)]

            self.actions.append({
                "f": f,
                "name": name,
                "params": params,
            })

    # -----------------
    # Helpers
    # -----------------

    def read_xyz(self):
        r = self.reader
        return {
            "x": r.s16big(),
            "y": r.s16big(),
            "z": r.s16big(),
        }

    # -----------------
    # Build (engine-facing)
    # -----------------
    # Left as data preparation — engine export comes next
    def build_scale_track(self, bone_id, time_scale=1.0):
        if self.scale_flags & 0x1:
            base = self.scale_per_bone[bone_id]
            sx = base["x"] / 64.0
            sy = base["y"] / 64.0
            sz = base["z"] / 64.0
        else:
            sx = sy = sz = 1.0

        if self.scale_flags & 0x2:
            keys = self.scale_keys_per_bone[bone_id]
        else:
            keys = [{"f": 0, "x": 0, "y": 0, "z": 0}]

        times = []
        values = []

        t = 0
        prev_x = prev_y = prev_z = 0

        for key in keys:
            f = key["f"]

            dx = key["x"] if key["x"] is not None else prev_x
            dy = key["y"] if key["y"] is not None else prev_y
            dz = key["z"] if key["z"] is not None else prev_z

            t += f

            sx += (dx / 64.0) * f
            sy += (dy / 64.0) * f
            sz += (dz / 64.0) * f

            times.append(t * time_scale)
            values.append((sx, sy, sz))

            prev_x, prev_y, prev_z = dx, dy, dz

        return {
            "bone": bone_id,
            "type": "scale",
            "times": times,
            "values": values,
        }

    def build_rotation_track(self, bone_id, time_scale=1.0):
        # Base rotation
        if self.base_animation_id == -1:
            base = self.rotation_per_bone[bone_id]
        else:
            base = self.seq.animations[
                self.base_animation_id
            ].rotation_per_bone[bone_id]

        # PS1 quirk: base * 2
        rx = base["x"] * 2
        ry = base["y"] * 2
        rz = base["z"] * 2

        keys = self.rotation_keys_per_bone[bone_id]

        times = []
        values = []

        t = 0
        prev_x = prev_y = prev_z = 0

        for key in keys:
            f = key["f"]

            dx = key["x"] if key["x"] is not None else prev_x
            dy = key["y"] if key["y"] is not None else prev_y
            dz = key["z"] if key["z"] is not None else prev_z

            t += f

            rx += dx * f
            ry += dy * f
            rz += dz * f

            q = rot2quat(
                rot13_to_rad_func(rx),
                rot13_to_rad_func(ry),
                rot13_to_rad_func(rz),
            )

            times.append(t * time_scale)
            values.append((q[0], q[1], q[2], q[3]))

            prev_x, prev_y, prev_z = dx, dy, dz

        return {
            "bone": bone_id,
            "type": "rotation",
            "times": times,
            "values": values,
        }

    def build(self, time_scale=1.0):
        """
        Builds engine-facing animation tracks.
        Result is independent of rendering backend.
        """

        tracks = []

        # TODO: translation track (root motion)
        # JS version intentionally skips this too

        for bone_id in range(self.seq.num_bones):
            tracks.append(self.build_rotation_track(bone_id, time_scale))

            if self.scale_flags & 0x3:
                tracks.append(self.build_scale_track(bone_id, time_scale))

        self.tracks = tracks
        self.duration = self.length * time_scale

