import os
import sys
import uuid
import glob

from PIL.ImageQt import ImageQt
from PySide6.QtCore import Qt, QTimer, QFile, QTextStream
from PySide6.QtGui import  QFontDatabase
from PySide6.QtWidgets import (
    QApplication, QMainWindow,
    QVBoxLayout, QGroupBox,
     QLabel, QCheckBox, QGridLayout,
    QSpinBox, QFileDialog,
    QScrollArea)
from ui_elements.ui_elements import *
from src.MPD import MPD
from src.OpenGLViewer import GLViewport
from src.Reader import Reader
from src.SEQ import SEQ
from src.SHP import SHP
from src.VSTOOLS import bytearray_to_image, export_png
from src.WEP import WEP
from src.ZND import ZND
from src.vs_strings import HUD_TEXT

SEQ_TO_DEG = 360.0 / 4096.0



class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.texture_list = None
        self.level_selector = None
        self.weapon_selector = None
        self.setWindowTitle("Vagrant Story Tool")
        self.resize(1920, 1080)

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        self.map_names = json.load(open('VagrantStory_data/level_map_names.json'))
        # Viewport placeholder
        viewport = QWidget()
        viewport.setStyleSheet("background-color: #202020;")
        viewport_layout = QVBoxLayout(viewport)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        self.viewport = GLViewport(self)
        layout.addWidget(self.viewport)

        font_id = QFontDatabase.addApplicationFont("ui_elements/animeace2_reg.ttf")
        font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
        comic_font = QFont(font_family, 6)

        # Load paper texture
        paper_texture = QPixmap("ui_elements/paper_noise.jpg")  # grayscale or color paper texture

        self.hud = HudComicStyle(HUD_TEXT, comic_font, paper_texture, parent=self.viewport)
        self.hud.move(20, 20)  # top-left corner
        self.hud.show()

        viewport_layout.addWidget(
            self.viewport
        )
        self.opened_file = None

        # Sidebar
        sidebar = QWidget()
        sidebar.setFixedWidth(300)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        sidebar_layout.addWidget(self.selector_panel())
        sidebar_layout.addWidget(self.file_panel())
        sidebar_layout.addWidget(self.animation_panel())
        sidebar_layout.addWidget(self.textures_panel())
        sidebar_layout.addWidget(self.export_textures_panel())
        sidebar_layout.addWidget(self.settings_panel())
        sidebar_layout.addWidget(self.export_panel())

        main_layout.addWidget(sidebar)
        main_layout.addWidget(viewport)

    # ---------- Panels ----------

    def selector_panel(self):
        box = QGroupBox("Selectors")
        layout = QVBoxLayout(box)
        self.weapon_selector = WeaponSelector(self)
        self.level_selector = LevelSelector(self)
        self.character_selector = CharacterSelector(self)
        layout.addWidget(QLabel('Weapons'))
        layout.addWidget(self.weapon_selector)
        layout.addWidget(QLabel('Levels'))
        layout.addWidget(self.level_selector)
        layout.addWidget(QLabel('Characters'))
        layout.addWidget(self.character_selector)

        return box

    def file_panel(self):
        box = QGroupBox("File")
        layout = QVBoxLayout(box)

        btn_file2 = QPushButton("Open Map")

        btn_open_character = QPushButton('Open Character')

        btn_open_character.clicked.connect(lambda: self.open_shp())
        btn_file2.clicked.connect(lambda: self.open_mpd())

        layout.addWidget(btn_file2)

        layout.addWidget(btn_open_character)

        return box

    def open_this(self, path):
        if path:
            self.open_wep("VagrantStory_data/OBJ/{}".format(path))

    def animation_panel(self):
        box = QGroupBox("Animation")
        layout = QHBoxLayout(box)

        prev_btn = QPushButton("<")
        next_btn = QPushButton(">")
        anim_index = QSpinBox()
        anim_index.setMaximum(9999)
        anim_count = QLabel("/ 0")

        layout.addWidget(prev_btn)
        layout.addWidget(anim_index)
        layout.addWidget(next_btn)
        layout.addWidget(anim_count)

        return box

    def textures_panel(self):
        box = QGroupBox("Textures")
        layout = QVBoxLayout(box)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        self.texture_list = QWidget()
        self.texture_list.setLayout(QGridLayout())
        scroll.setWidget(self.texture_list)

        layout.addWidget(scroll)
        return box

    def export_textures_panel(self):
        box = QGroupBox("Export Textures")
        layout = QVBoxLayout(box)

        layout.addWidget(QPushButton("Download textures"))
        return box

    def settings_panel(self):
        box = QGroupBox("Settings")
        layout = QVBoxLayout(box)

        self.checkbox_hud = QCheckBox('Show HUD')
        self.checkbox_hud.setChecked(True)
        self.checkbox_hud.checkStateChanged.connect(self.toggle_hud)
        layout.addWidget(self.checkbox_hud)

        self.checkbox_wireframe = QCheckBox('Wireframe')
        self.checkbox_wireframe.checkStateChanged.connect(self.toggle_wireframe)
        layout.addWidget(self.checkbox_wireframe)

        self.checkbox_vertex_colors = QCheckBox('Disable Vertex Colors')
        self.checkbox_vertex_colors.checkStateChanged.connect(self.toggle_vertex_color)
        layout.addWidget(self.checkbox_vertex_colors)

        self.checkbox_scanlines = QCheckBox('Scan lines mode')
        self.checkbox_scanlines.checkStateChanged.connect(self.toggle_scanline)
        layout.addWidget(self.checkbox_scanlines)

        self.checkbox_disable_textures = QCheckBox('Disable Texture')
        self.checkbox_disable_textures.checkStateChanged.connect(self.toggle_textures)
        layout.addWidget(self.checkbox_disable_textures)

        self.checkbox_gray_background = QCheckBox('Gray Background')
        self.checkbox_gray_background.checkStateChanged.connect(self.toggle_background)
        layout.addWidget(self.checkbox_gray_background)

        self.checkbox_show_skeleton = QCheckBox('Show Skeleton')
        self.checkbox_show_skeleton.checkStateChanged.connect(self.toogle_skeleton)
        layout.addWidget(self.checkbox_show_skeleton)

        for text in [
            "Use Normal Material",
            "Show Skeleton",
        ]:
            layout.addWidget(QCheckBox(text))

        return box

    def toogle_skeleton(self):
        self.viewport.draw_bones_mode = self.checkbox_show_skeleton.isChecked()
        self.viewport.update()

    def toggle_background(self):
        self.viewport.grey_background = self.checkbox_gray_background.isChecked()
        self.viewport.update()

    def toggle_textures(self):
        self.viewport.disable_textures = self.checkbox_disable_textures.isChecked()
        self.viewport.update()

    def toggle_scanline(self):
        self.viewport.scanline_mode = self.checkbox_scanlines.isChecked()
        self.viewport.update()

    def toggle_wireframe(self):
        self.viewport.wireframe_mode = self.checkbox_wireframe.isChecked()
        self.viewport.update()

    def toggle_vertex_color(self):
        self.viewport.disable_vertex_color = self.checkbox_vertex_colors.isChecked()
        self.viewport.update()

    def toggle_hud(self):

        self.hud.setVisible(not self.hud.isVisible())

    def export_panel(self):
        box = QGroupBox("Export")
        layout = QVBoxLayout(box)
        bt_export_fbx = QPushButton('Export FBX')
        layout.addWidget(bt_export_fbx)
        bt_export_fbx.clicked.connect(self.export_to_fbx)
        layout.addWidget(QPushButton("Export OBJ"))
        layout.addWidget(
            QLabel(
                "Exports the geometry as is,\nwithout skeleton and animations.",
                wordWrap=True
            )
        )
        return box

    def export_to_fbx(self):
        if isinstance(self.opened_file, WEP):
            asset_type = "weapons"
            file_name = self.weapon_selector.combo.currentText().casefold().replace(" ", "_")
            folder_path = "{}/{}".format(asset_type, file_name)
            for i_texture, texture in enumerate(self.opened_file.texture_map.textures):
                if not os.path.exists(asset_type):
                    os.mkdir(asset_type)

                if not os.path.exists(folder_path):
                    os.mkdir(folder_path)

                export_png(texture['data'], self.opened_file.texture_map.get_width(), texture['height'],
                           "{}/{}_{}.png".format(folder_path, file_name, i_texture), False)
            self.viewport.export_fbx_scene("{}/{}.fbx".format(folder_path, file_name))
            return
        elif isinstance(self.opened_file, MPD):
            asset_type = "levels"

            file_name = "{}_{}".format(self.get_map_name(element=1), "".join(self.get_map_name().title().split()))

            folder_path = "{}/{}/{}".format(asset_type, "".join(self.get_map_name(element='area').title().split()),
                                            file_name)
            exported_textures = []

            os.makedirs(folder_path, exist_ok=True)
            for imesh, mesh in enumerate(self.opened_file.meshes):

                material = mesh.material
                if material['data'] not in exported_textures:
                    exported_textures.append(material['data'])
                    export_png(material['data'], material['width'], material['height'],
                               "{}/{}/textures/{}-{}.png".format(asset_type, "".join(
                                   self.get_map_name(element='area').title().split()), mesh.texture_id, mesh.clut_id),
                               False)

            self.viewport.export_fbx_scene("{}/{}.fbx".format(folder_path, file_name))
            return
        else:
            export_path = QFileDialog.getSaveFileName(self, 'Save FBX', "", "FBX *.fbx")
            if export_path[0]:
                self.viewport.export_fbx_scene(export_path[0])
            return

    def get_map_name(self, map_file=None, element=None):
        if not map_file:
            map_file = os.path.basename(self.current_path)

        for area in self.map_names:
            for level in self.map_names[area]:
                if map_file in level:
                    if element == 'area':
                        return area
                    if element:
                        return level[element]
                    else:
                        return level[-1]
        return "0_{}".format(map_file)

    def get_reader(self, path, file_type="*"):

        self.viewport.clean_scene()
        if not path:
            path, _ = QFileDialog.getOpenFileName(
                self, "Open {}".format(file_type), "", "{} Files (*.{})".format(file_type, file_type)
            )
        if path == "":
            return False
        with open(path, "rb") as f:
            data = f.read()
        if 'mpd' in path.lower():
            self.current_path = path
        return Reader(data)

    def open_mpd(self, path=None, zndpath=None):
        self.viewport.update()
        reader = self.get_reader(path, 'MPD')

        if not reader:
            return
        if zndpath:
            znd = self.open_znd(zndpath)
        else:
            znd = self.open_znd()

        mpd = MPD(reader, znd)
        mpd.read()
        mpd.build()

        self.opened_file = mpd

        mesh_batches = []
        materials_used = []
        counter = 0
        for mesh in mpd.meshes:
            material = mesh.material
            if material is None:
                continue
            if mesh.material_id not in materials_used:
                qim = ImageQt(
                    bytearray_to_image(material['data'], material['width'], material['height']).resize((64, 64)))
                pix = QPixmap.fromImage(qim)
                label = QLabel(pixmap=pix)
                label.setToolTip(mesh.material_id)
                self.texture_list.layout().addWidget(label, int(counter / 3), counter % 3)
                materials_used.append(mesh.material_id)
                counter += 1

            batch = {
                "texture": self.viewport.create_gl_texture_from_rgba(material["data"], material["width"],
                                                                     material["height"]),  # OpenGL texture ID
                "material_id": mesh.material_id,
                "vertices": [],
                "uvs": [],
                "faces": [],
                "colors": [],
            }

            batch = self.sort_geometry(batch, mesh, 'mpd')
            mesh_batches.append(batch)

        self.viewport.load_batches(mesh_batches)

    def open_znd(self, path=None):
        reader = self.get_reader(path, 'ZND')
        """
            Loads a ZND file, updates textures, and prepares framebuffer data.
            """
        # --- Read ZND ---
        znd = ZND(reader)
        znd.read()
        QTimer.singleShot(0, znd.frameBuffer.build)
        return znd

    def open_seq(self, path=None):
        reader = self.get_reader(path, 'SEQ')

        # --- Read SEQ ---
        seq = SEQ(reader)
        seq.read()
        seq.build()

        return seq

    def open_shp(self, path=None, autoload_anim=False):
        reader = self.get_reader(path, 'SHP')
        if not reader:
            return

        shp = SHP(reader)
        shp.read()
        shp.build()
        if autoload_anim:
            sample_animations = glob.glob('{}**.SEQ'.format(path[:-4]))
            seq = self.open_seq(sample_animations[0] if len(sample_animations) else '')
        else:
            seq = self.open_seq()

        bone_index = {x: shp.Skeleton.bones.index(x) for x in shp.Skeleton.bones}
        parent_h = {}
        for b in shp.Skeleton.bones:
            parent_h[bone_index[b]] = []
            for c in b.children:
                parent_h[bone_index[b]].append(bone_index[c])

        self.viewport.activeSHP = shp
        self.viewport.activeSEQ = seq
        self.viewport.playing = True
        self.viewport.current_animation = seq.animations[0]


        for w in self.texture_list.findChildren(QLabel):
            w.deleteLater()

        self.opened_file = shp

        for i_texture, texture in enumerate(shp.texture_map.textures):
            qim = ImageQt(bytearray_to_image(texture['data'], shp.texture_map.get_width(), texture['height']))
            pix = QPixmap.fromImage(qim)
            self.texture_list.layout().addWidget(QLabel(pixmap=pix), int(i_texture / 3), i_texture % 3)

        batch = {
            "texture": self.viewport.create_gl_texture_from_rgba(shp.mesh.material.texture["data"],
                                                                 shp.texture_map.get_width(),
                                                                 shp.mesh.material.texture["height"]),
            "material_id": str(random.randint(0, 99999)),
            "vertices": [],
            "uvs": [],
            "faces": [],
            "colors": [],
        }
        self.sort_geometry(batch, shp.mesh, 'wep')
        self.viewport.load_batches([batch])

    def open_wep(self, path=None):
        reader = self.get_reader(path, 'WEP')
        if not reader:
            return

        wep = WEP(reader)
        wep.read()
        wep.build()
        for w in self.texture_list.findChildren(QLabel):
            w.deleteLater()

        self.opened_file = wep

        for i_texture, texture in enumerate(wep.texture_map.textures):
            qim = ImageQt(bytearray_to_image(texture['data'], wep.texture_map.get_width(), texture['height']))
            pix = QPixmap.fromImage(qim)
            self.texture_list.layout().addWidget(QLabel(pixmap=pix), int(i_texture / 3), i_texture % 3)

        batch = {
            "texture": self.viewport.create_gl_texture_from_rgba(wep.mesh.material.texture["data"],
                                                                 wep.texture_map.get_width(),
                                                                 wep.mesh.material.texture["height"]),
            "material_id": uuid.uuid4(),
            "vertices": [],
            "uvs": [],
            "faces": [],
            "colors": [],
        }
        self.sort_geometry(batch, wep.mesh, 'wep')
        self.viewport.load_batches([batch])

    def sort_geometry(self, batch, mesh, asset_type):

        pos = mesh.geometry.attributes["positions"]
        uv = mesh.geometry.attributes["uvs"]
        idx = mesh.geometry.attributes["indices"]
        col = mesh.geometry.attributes["colors"]

        if asset_type == 'wep':
            batch['SkinnedMesh'] = mesh
            batch['Skeleton'] = self.opened_file.Skeleton
            batch['skinIndex'] = mesh.geometry.attributes['skin_index']
            batch['skinWeight'] = mesh.geometry.attributes['skin_weight']

        # ---- vertices ----
        for i in range(0, len(pos), 3):
            batch["vertices"].append((
                pos[i],
                pos[i + 1],
                pos[i + 2],
            ))

        # ---- uvs ----
        for i in range(0, len(uv), 2):
            batch["uvs"].append((
                uv[i],
                1.0 - uv[i + 1],  # OpenGL flip
            ))

        # ---- colors ----
        for i in range(0, len(col), 3):
            batch["colors"].append((
                col[i],
                col[i + 1],
                col[i + 2],
            ))

        # ---- faces ----
        for i in range(0, len(idx), 3):
            batch["faces"].append([
                (idx[i], idx[i]),
                (idx[i + 1], idx[i + 1]),
                (idx[i + 2], idx[i + 2]),
            ])

        return batch



if __name__ == "__main__":
    app = QApplication(sys.argv)
    file = QFile("ui_elements/combinear.qss")
    file.open(QFile.OpenModeFlag.ReadOnly | QFile.OpenModeFlag.Text)
    stream = QTextStream(file)
    app.setStyleSheet(stream.readAll())
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
