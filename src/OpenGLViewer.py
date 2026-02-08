import time

from PySide6.QtOpenGL import QOpenGLShaderProgram, QOpenGLShader
from PySide6.QtGui import QMatrix4x4, QVector3D, QImage
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtCore import Qt, QTimer
from src.FBX_exporter import *
from src.VSTOOLS import rot2quat, rot13_to_rad_func
from src.V3DClasses import *
from OpenGL.GL import *
from OpenGL.GLU import *
import math
from src.vs_strings import *
import numpy as np


class GLViewport(QOpenGLWidget):
    def __init__(self, parent):
        super().__init__()

        self.dt = None
        self.draw_bones_mode = False
        self.program = None
        self.bg_shader = None
        self.bg_texture = None
        self.meshes = []
        self.last_pos = None
        self.grey_background = False
        self.disable_textures = False
        self.scanline_mode = False
        self.wireframe_mode = False
        self.disable_vertex_color = False
        self.main_app = parent
        self.target = QVector3D(0, 0, 0)
        self.pan_offset = QVector3D(0, 0, 0)


        self.rot_x = 20.0
        self.rot_y = 30.0

        self.fov = 45.0

        self.pan_offset = QVector3D(0, 0, 0)

        self.uvs = None
        self.colors = None
        self.texture_id = None
        self.vbo = None
        self.vao = None
        self.vertices = None
        self.faces = None
        self.rot_x = -30
        self.rot_y = 45
        self.distance = 5
        self.vertex_count = None
        self.bind_rotations = None
        self.scan_time = 0
        self.activeSEQ = None
        self.activeSHP = None
        self.current_animation = None
        self.scene_vertices = None
        self.current_anim_id = 0
        self.anim_time = 0.0
        self.playing = False
        self.fps = 30
        self.last_time = time.time()

        self.keys = set()
        self.move_speed = 500.0  # units per second
        self.shift_multiplier = 3  # fast move
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.timer.start(16)  # ~60 FPS
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)




    @staticmethod
    def load_gl_texture(path):
        img = QImage(path).convertToFormat(QImage.Format.Format_RGBA8888)
        img = img.mirrored()

        tex_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex_id)

        glTexImage2D(
            GL_TEXTURE_2D,
            0,
            GL_RGBA,
            img.width(),
            img.height(),
            0,
            GL_RGBA,
            GL_UNSIGNED_BYTE,
            img.bits()
        )

        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)

        glBindTexture(GL_TEXTURE_2D, 0)
        return tex_id
    @staticmethod
    def compute_bbox(vertices):
        min_v = QVector3D(vertices[0])
        max_v = QVector3D(vertices[0])

        for v in vertices[1:]:
            v = QVector3D(v)
            min_v.setX(min(min_v.x(), v.x()))
            min_v.setY(min(min_v.y(), v.y()))
            min_v.setZ(min(min_v.z(), v.z()))

            max_v.setX(max(max_v.x(), v.x()))
            max_v.setY(max(max_v.y(), v.y()))
            max_v.setZ(max(max_v.z(), v.z()))

        center = (min_v + max_v) * 0.5
        radius = (max_v - center).length()

        return center, radius*0.85



    def update_animation(self, dt):

        if not self.playing or not self.current_animation:
            return
        if not dt:
            dt = 1
        self.anim_time += dt
        length = self.current_animation.length * 24

        if self.anim_time >= length:
            self.anim_time %= length

        self.apply_pose(self.current_animation, self.anim_time)

    def eval_scale(self, animation, bone_id, frame):
        if animation.scale_flags & 0x1:
            base = animation.scale_per_bone[bone_id]
            sx = base["x"] / 64.0
            sy = base["y"] / 64.0
            sz = base["z"] / 64.0
        else:
            sx = sy = sz = 1.0

        if not (animation.scale_flags & 0x2):
            return sx, sy, sz

        keys = animation.scale_keys_per_bone[bone_id]

        f_acc = 0
        prev_x = prev_y = prev_z = 0

        for key in keys:
            kf = key["f"]

            if key["x"] is not None:
                prev_x = key["x"]
            if key["y"] is not None:
                prev_y = key["y"]
            if key["z"] is not None:
                prev_z = key["z"]

            for _ in range(kf):
                if f_acc >= frame:
                    return sx, sy, sz

                sx += (prev_x / 64.0)
                sy += (prev_y / 64.0)
                sz += (prev_z / 64.0)
                f_acc += 1

        return sx, sy, sz

    def eval_translation(self, animation, frame):
        base = animation.translation
        tx = base["x"]
        ty = base["y"]
        tz = base["z"]

        keys = animation.translation_keys

        f_acc = 0
        prev_x = prev_y = prev_z = 0

        for key in keys:
            kf = key["f"]

            if key["x"] is not None:
                prev_x = key["x"]
            if key["y"] is not None:
                prev_y = key["y"]
            if key["z"] is not None:
                prev_z = key["z"]

            for _ in range(kf):
                if f_acc >= frame:
                    return tx, ty, tz

                tx += prev_x
                ty += prev_y
                tz += prev_z
                f_acc += 1

        return tx, ty, tz

    def eval_rotation(self, animation, bone_id, frame):
        # base pose
        if animation.base_animation_id == -1:
            base = animation.rotation_per_bone[bone_id]
        else:
            base = animation.seq.animations[
                animation.base_animation_id
            ].rotation_per_bone[bone_id]

        rx = base['x'] * 2
        ry = base['y'] * 2
        rz = base['z'] * 2

        keys = animation.rotation_keys_per_bone[bone_id]

        f_acc = 0

        prev_x = prev_y = prev_z = 0

        for key in keys:
            kf = key["f"]

            if key["x"] is not None:
                prev_x = key["x"]
            if key["y"] is not None:
                prev_y = key["y"]
            if key["z"] is not None:
                prev_z = key["z"]

            for _ in range(kf):
                if f_acc >= frame:
                    return rot2quat(
                        rot13_to_rad_func(rx),
                        rot13_to_rad_func(ry),
                        rot13_to_rad_func(rz),
                    )

                rx += prev_x
                ry += prev_y
                rz += prev_z
                f_acc += 1

        return rot2quat(
            rot13_to_rad_func(rx),
            rot13_to_rad_func(ry),
            rot13_to_rad_func(rz),
        )

    def time_to_frame(self, time_sec: float) -> int:
        return int(time_sec / 24)

    def apply_pose(self, animation, time_sec):
        frame = self.time_to_frame(time_sec)

        skeleton = self.activeSHP.Skeleton
        bones = skeleton.bones

        for bone_id, bone in enumerate(bones):

            bone.quaternion = self.eval_rotation(animation, bone_id, frame)

            if animation.scale_flags & 0x3:
                bone.scale = self.eval_scale(animation, bone_id, frame)
            bone.updateMatrixWorld()

        # root translation
        tx, ty, tz = self.eval_translation(animation, frame)
        bones[0].position.x = tx
        bones[0].position.y = ty
        bones[0].position.z = tz



    def apply_animation(self, animation, time):
        skeleton = self.activeSHP.Skeleton
        bones = skeleton.bones

        for track in animation.tracks:
            bone_id = track.bone_id
            bone = bones[bone_id]

            value = track.sample(time)

            if track.type == "rotation":
                bone.quaternion = value
            elif track.type == "scale":
                bone.scale = value
            elif track.type == "translation":
                bone.position = value

    def stop_anim(self):
        self.playing = False
        self.anim_time = 0.0
        self.current_animation = None

    def parse_anim(self, anim_id_input: int) -> int:
        if not self.activeSEQ:
            return 0

        try:
            anim_id = int(anim_id_input)
        except (ValueError, TypeError):
            anim_id = 0

        anim_id = max(0, min(anim_id, len(self.activeSEQ.animations) - 1))
        return anim_id

    def load_mesh(self, vertices, uvs, faces, colors=None):
        ctx = self.context()
        if not ctx or not ctx.isValid():
            print("GL context not ready — skipping")
            return
        self.vertices = vertices
        self.uvs = uvs
        self.faces = faces
        if colors:
            self.colors = colors
        self.makeCurrent()
        self._upload_mesh()
        self.scene_vertices = []

        for v in self.vertices:
            self.scene_vertices.append(QVector3D(v[0], v[1], v[2]))
        self.doneCurrent()
        self.update()

    def load_batches(self, mesh_batches):
        ctx = self.context()
        if not ctx or not ctx.isValid():
            print("GL context not ready — skipping")
            return
        self.makeCurrent()

        self.meshes = []

        for batch in mesh_batches:
            mesh = GLMesh(
                vertices=batch["vertices"],
                uvs=batch["uvs"],
                faces=batch["faces"],
                colors=batch["colors"],
                texture_id=batch["texture"],
                material_id=batch["material_id"],
            )
            if 'SkinnedMesh' in batch:
                mesh.skinned_mesh = batch['SkinnedMesh']
                mesh.skeleton = batch['Skeleton']

            mesh.upload()
            self.meshes.append(mesh)
        self.scene_vertices = []
        for m in self.meshes:
            for v in m.vertices:
                self.scene_vertices.append(QVector3D(v[0],v[1],v[2]))
        self.vertex_count = 1
        self.doneCurrent()
        self.update()

    def draw_background_texture(self):
        glDisable(GL_DEPTH_TEST)
        glDepthMask(GL_FALSE)

        self.bg_shader.bind()
        loc = glGetUniformLocation(
            self.bg_shader.programId(), b"u_time"
        )
        if loc != -1:
            glUniform1f(loc, self.scan_time)

        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.bg_texture)

        loc = glGetUniformLocation(
            self.bg_shader.programId(), b"u_bgTexture"
        )
        if loc != -1:
            glUniform1i(loc, 0)

        glDrawArrays(GL_TRIANGLES, 0, 3)

        glBindTexture(GL_TEXTURE_2D, 0)
        self.bg_shader.release()

        glDepthMask(GL_TRUE)
        glEnable(GL_DEPTH_TEST)
        self.update()

    def export_fbx_scene(self, path):
        if self.meshes:
            export_fbx_scene(path, self.meshes)

    def initializeGL(self):
        self.makeCurrent()
        glEnable(GL_DEPTH_TEST)
        # Enable Alpha Blending
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        glClearColor(0, 0, 0, 1.0)

        glEnable(GL_CULL_FACE)
        glCullFace(GL_BACK)  # Cull back faces
        glFrontFace(GL_CCW)

        # ----- BACKGROUND SHADER-----#
        self.bg_shader = QOpenGLShaderProgram()
        self.bg_shader.addShaderFromSourceCode(
            QOpenGLShader.ShaderTypeBit.Vertex, BG_SHADER_VERTEX
        )
        self.bg_shader.addShaderFromSourceCode(
            QOpenGLShader.ShaderTypeBit.Fragment, BG_SHADER_FRAG
        )
        self.bg_shader.link()
        self.bg_texture = self.load_gl_texture("ui_elements/vagrant_background.jpg")

        # ---- SHADER ----
        self.program = QOpenGLShaderProgram()
        self.program.setUniformValue("u_use_skinning", True)
        self.program.addShaderFromSourceCode(
            QOpenGLShader.ShaderTypeBit.Vertex, ASSET_SHADER_VERTEX)

        self.program.addShaderFromSourceCode(
            QOpenGLShader.ShaderTypeBit.Fragment, ASSET_SHADER_FRAG)

        if not self.program.link():
            raise RuntimeError(self.program.log())

        # ---- VAO / VBO ----
        self.vao = glGenVertexArrays(1)
        self.vbo = glGenBuffers(1)

    def clean_scene(self):
        """
        Clears all GPU resources and resets the scene safely.
        """
        if hasattr(self, "meshes"):
            for m in self.meshes:
                if m.vbo:
                    glDeleteBuffers(1, [m.vbo])
                if m.vao:
                    glDeleteVertexArrays(1, [m.vao])
        self.meshes = []

        # --- Delete VBO ---
        if self.vbo:
            glDeleteBuffers(1, [self.vbo])
            self.vbo = None

        # --- Delete VAO ---
        if self.vao:
            glDeleteVertexArrays(1, [self.vao])
            self.vao = None

        # --- Delete texture ---
        if self.texture_id:
            glDeleteTextures(1, [self.texture_id])
            self.texture_id = None

        # --- Reset mesh data ---
        self.vertices = None
        self.uvs = None
        self.faces = None
        self.vertex_count = None

        self.doneCurrent()
        self.update()

    def _upload_mesh(self):
        if self.vertices is None or self.faces is None:
            return

        # Data structure: Position(3) + UV(2) + Color(4) = 9 floats per vertex
        data = []
        for face in self.faces:
            for v_idx, uv_idx in face:
                # 1. Add Position (already a tuple/list from your build loop)
                data.extend(self.vertices[v_idx])

                # 2. Add UV (already flipped and normalized)
                data.extend(self.uvs[uv_idx])

                # 3. Add Color
                if self.colors and v_idx < len(self.colors):
                    c = self.colors[v_idx]
                    # If your build function did r/255, c is already 0.0-1.0
                    # We add 1.0 for the Alpha channel
                    data.extend([c[0], c[1], c[2], 1.0])
                else:
                    # Default to PS1 Neutral Gray (0.5) so that 0.5 * 2 = 1.0 brightness
                    data.extend([0.5, 0.5, 0.5, 1.0])

        data = np.array(data, dtype=np.float32)
        self.vertex_count = len(data) // 9

        glBindVertexArray(self.vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, data.nbytes, data, GL_STATIC_DRAW)

        stride = 9 * 4
        # Position (Location 0)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))
        glEnableVertexAttribArray(0)

        # UV (Location 1)
        glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(12))
        glEnableVertexAttribArray(1)

        # Color (Location 2)
        glVertexAttribPointer(2, 4, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(20))
        glEnableVertexAttribArray(2)

        glBindVertexArray(0)

    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)

        glMatrixMode(GL_MODELVIEW)

    def extract_position(self, matrix4):
        # assuming column-major 4x4 matrix
        return (
            matrix4.elements[0][3],
            matrix4.elements[1][3],
            matrix4.elements[2][3],
        )

    def build_skeleton_lines(self, bones):
        lines = []

        for bone in bones:
            if bone.parent is None:
                continue

            bone.parent.updateMatrixWorld()
            bone.updateMatrixWorld()
            p0 = self.extract_position(bone.parent.matrixWorld)
            p1 = self.extract_position(bone.matrixWorld)

            lines.append((p0, p1))

        return lines

    def draw_skeleton(self, lines):
        glUseProgram(0)
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_LIGHTING)

        glLineWidth(2.5)

        glBegin(GL_LINES)
        for p0, p1 in lines:
            glColor4f(0.0, 1.0, 0.0, 1.0)  # start color
            glVertex3f(*p0)

            glColor4f(0.0, 1.0, 0.0, 1.0)  # end color
            glVertex3f(*p1)
        glEnd()

        glEnable(GL_DEPTH_TEST)


    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        self.scan_time += 0.016
        if not self.vertex_count:
            self.draw_background_texture()
            return
        self.update_animation(self.dt)
        glPolygonMode(
            GL_FRONT_AND_BACK,
            GL_LINE if self.wireframe_mode else GL_FILL
        )

        aspect = self.width() / max(self.height(), 1)

        # ---- Camera math (unchanged) ----
        yaw = math.radians(self.rot_y)
        pitch = math.radians(self.rot_x)

        forward = QVector3D(
            math.cos(pitch) * math.sin(yaw),
            math.sin(pitch),
            math.cos(pitch) * math.cos(yaw)
        ).normalized()

        right = QVector3D.crossProduct(forward, QVector3D(0, 1, 0)).normalized()
        up = QVector3D.crossProduct(right, forward).normalized()

        cam_pos = self.target + self.pan_offset - forward * self.distance

        view = QMatrix4x4()
        view.lookAt(cam_pos, self.target + self.pan_offset, up)

        proj = QMatrix4x4()
        proj.perspective(self.fov, aspect, 10.0, 10000.0)

        model = QMatrix4x4()
        model.scale(-1, -1, 1)

        mvp = proj * view * model

        # ---- Shader ----
        self.program.bind()


        if self.grey_background:
            glClearColor(0.1, 0.1, 0.1, 1.0)
            self.update()
        else:
            glClearColor(0, 0, 0, 1.0)
            self.update()

        def set_uniform(uniform_name, fn):
            loc = glGetUniformLocation(self.program.programId(), uniform_name)
            if loc != -1:
                fn(loc)

        set_uniform(b"u_mvp",
                    lambda loc: glUniformMatrix4fv(
                        loc, 1, GL_FALSE, np.array(mvp.data(), dtype=np.float32)
                    )
                    )

        set_uniform(b"u_time",
                    lambda loc: glUniform1f(loc, self.scan_time)
                    )

        set_uniform(b"u_scanlineIntensity",
                    lambda loc: glUniform1f(loc, 0.25 if self.scanline_mode else 0.0)
                    )

        set_uniform(b"u_scanlineCount",
                    lambda loc: glUniform1f(loc, 800.0)
                    )

        set_uniform(b"u_useVertexColor",
                    lambda loc: glUniform1i(loc, int(not self.disable_vertex_color))
                    )
        set_uniform(b"u_disableTexture",
                    lambda loc: glUniform1i(loc, int(not self.disable_textures))
                    )




        # ---- Texture ----

        glActiveTexture(GL_TEXTURE0)
        set_uniform(b"u_texture",
                    lambda loc: glUniform1i(loc, 0)
                    )

        # ---- Draw ----
        for mesh in self.meshes:
            glBindTexture(GL_TEXTURE_2D, mesh.texture_id)
            glBindVertexArray(mesh.vao)
            glDrawArrays(GL_TRIANGLES, 0, mesh.vertex_count)

        glBindVertexArray(0)
        glBindTexture(GL_TEXTURE_2D, 0)

        self.program.release()
        if self.draw_bones_mode:
        # ---- Draw skeleton LAST (no shader) ----
            glUseProgram(1)
            glDisable(GL_LIGHTING)
            glDisable(GL_TEXTURE_2D)
            # ---- Match fixed-pipeline matrices to shader ----
            glMatrixMode(GL_PROJECTION)
            glLoadMatrixf(np.array(proj.data(), dtype=np.float32))

            glMatrixMode(GL_MODELVIEW)
            glLoadMatrixf(np.array((view * model).data(), dtype=np.float32))

            lines = self.build_skeleton_lines(self.activeSHP.Skeleton.bones)
            self.draw_skeleton(lines)

    def create_gl_texture_from_rgba(self, buffer, width, height):
        self.makeCurrent()
        tex_id = glGenTextures(1)

        glBindTexture(GL_TEXTURE_2D, tex_id)

        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)

        glTexImage2D(
            GL_TEXTURE_2D,
            0,
            GL_RGBA,
            width,
            height,
            0,
            GL_RGBA,
            GL_UNSIGNED_BYTE,
            bytes(buffer),
        )

        glBindTexture(GL_TEXTURE_2D, 0)
        return tex_id

    """CAMERA CONTROLS"""

    def cameraVectors(self):
        yaw = math.radians(self.rot_y)
        pitch = math.radians(self.rot_x)

        forward = QVector3D(
            math.cos(pitch) * math.sin(yaw),
            math.sin(pitch),
            math.cos(pitch) * math.cos(yaw)
        ).normalized()

        right = QVector3D.crossProduct(forward, QVector3D(0, 1, 0)).normalized()
        up = QVector3D.crossProduct(right, forward).normalized()

        return forward, right, up

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_H:
            self.main_app.checkbox_hud.setChecked(not self.main_app.checkbox_hud.isChecked())
        if event.key() == Qt.Key.Key_F:
            self.fitCameraToScene(self.scene_vertices)
        if event.key() == Qt.Key.Key_G:
            self.distance = 5
            self.target = QVector3D(-250,100,300)

        self.keys.add(event.key())

    def keyReleaseEvent(self, event):
        self.keys.discard(event.key())

    def mousePressEvent(self, event):
        self.last_pos = event.position()

    def mouseMoveEvent(self, event):
        dx = event.position().x() - self.last_pos.x()
        dy = event.position().y() - self.last_pos.y()

        forward, right, up = self.cameraVectors()

        if event.buttons() & Qt.MouseButton.LeftButton:
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                # PAN
                pan_speed = 0.2 * min(self.distance, 50)
                self.pan_offset -= right * dx * pan_speed
                self.pan_offset += up * dy * pan_speed
            else:
                # ORBIT
                self.rot_x += dy * 0.2
                self.rot_y += dx * 0.2
                self.rot_x = max(-89, min(89, self.rot_x))

        elif event.buttons() & Qt.MouseButton.MiddleButton:
            # DOLLY
            dolly_speed = 1

            self.target += forward * dy * dolly_speed


        self.last_pos = event.position()
        self.update()

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            # FOV
            self.fov -= event.angleDelta().y() * 0.01
            self.fov = max(15, min(120, int(self.fov)))
        else:
            # Zoom (distance-based)
            self.distance -= event.angleDelta().y() * 0.1
            self.distance = max(0.1, self.distance)

        self.update()

    def update_time(self):
        if not self.keys:
            return

        forward, right, up = self.cameraVectors()

        speed = self.move_speed * 0.016
        if Qt.Key.Key_Shift in self.keys:
            speed *= self.shift_multiplier

        move = QVector3D(0, 0, 0)

        if Qt.Key.Key_W in self.keys:
            move += forward
        if Qt.Key.Key_S in self.keys:
            move -= forward
        if Qt.Key.Key_A in self.keys:
            move -= right
        if Qt.Key.Key_D in self.keys:
            move += right
        if Qt.Key.Key_Q in self.keys:
            move -= up
        if Qt.Key.Key_E in self.keys:
            move += up

        if not move.isNull():
            move.normalize()
            move *= speed
            self.target += move  # FPS-style movement

        current_time = time.time()
        self.dt = current_time - self.last_time  # delta time in seconds
        self.last_time = current_time


        self.update()  # request redraw

    def fitCameraToScene(self, vertices):
        center, radius = self.compute_bbox(vertices)

        # Reset orbit state
        self.target = center
        self.pan_offset = QVector3D(0, 0, 0)

        # FOV math
        aspect = self.width() / max(1, self.height())
        fov_y = math.radians(self.fov)
        fov_x = 2.0 * math.atan(math.tan(fov_y * 0.5) * aspect)

        dist_y = radius / math.tan(fov_y * 0.5)
        dist_x = radius / math.tan(fov_x * 0.5)

        self.distance = max(dist_x, dist_y) * 1.2  # padding


        self.update()

class GLMesh:
    def __init__(self, vertices, uvs, faces, colors, texture_id, material_id, skinned_mesh=None, skeleton=None):
        self.vertices = vertices
        self.uvs = uvs
        self.faces = faces
        self.colors = colors
        self.texture_id = texture_id
        self.material_id = material_id
        self.skinned_mesh = skinned_mesh
        self.skeleton = skeleton
        self.vao = None
        self.vbo = None
        self.vertex_count = 0

    def upload(self):
        data = []

        for face in self.faces:
            for v_idx, uv_idx in face:
                data.extend(self.vertices[v_idx])
                data.extend(self.uvs[uv_idx])
                if self.colors and v_idx < len(self.colors):
                    c = self.colors[v_idx]
                    # If your build function did r/255, c is already 0.0-1.0
                    # We add 1.0 for the Alpha channel
                    data.extend([c[0], c[1], c[2], 1.0])
                else:
                    # Default to PS1 Neutral Gray (0.5) so that 0.5 * 2 = 1.0 brightness
                    data.extend([0.5, 0.5, 0.5, 1.0])

        data = np.array(data, dtype=np.float32)
        self.vertex_count = len(data) // 9  # 3 pos + 2 uv + 4 color

        self.vao = glGenVertexArrays(1)
        self.vbo = glGenBuffers(1)

        glBindVertexArray(self.vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, data.nbytes, data, GL_STATIC_DRAW)

        stride = 9 * 4

        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))
        glEnableVertexAttribArray(0)

        glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(12))
        glEnableVertexAttribArray(1)

        glVertexAttribPointer(2, 4, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(20))
        glEnableVertexAttribArray(2)

        glBindVertexArray(0)
