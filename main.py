import os, sys,  json, glob, random, uuid

from PySide6.QtGui import  QPixmap, QFontDatabase, QFont, QColor, QPainterPath, QPainter, QFontMetrics, QImage
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLabel, QCheckBox, QGridLayout,
    QSpinBox, QFileDialog,
    QScrollArea, QComboBox
)
from PySide6.QtCore import Qt, QTimer, QPoint
import numpy as np

from src.SEQ import SEQ
from src.VSTOOLS import bytearray_to_image, export_png, ROT13_TO_RAD

from src.OpenGLViewer import GLViewport
from src.MPD import MPD
from src.ZND import ZND
from src.WEP import WEP
from src.SHP import SHP
from src.Reader import Reader
from PIL.ImageQt import ImageQt

SEQ_TO_DEG = 360.0 / 4096.0
SEED = random.randint(0,100)

def update_seed():
    SEED = random.randint(0,100)

def drawPixelatedText(painter: QPainter, text: str, x: int, y: int, font: QFont, scale: int = 3,
                      color: QColor = QColor(0, 0, 0)):
    """
    Draws pixelated text by rendering it at small size then scaling up.
    :param painter: QPainter to draw on
    :param text: text to draw
    :param x, y: top-left position
    :param font: QFont
    :param scale: pixelation factor (higher = blockier)
    :param color: text color
    """
    # Measure text
    metrics = QFontMetrics(font)
    text_width = metrics.horizontalAdvance(text)
    text_height = metrics.height()

    # Create a small image
    img = QImage(text_width, text_height, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)

    temp_painter = QPainter(img)
    temp_painter.setFont(font)
    temp_painter.setPen(color)
    temp_painter.drawText(0, metrics.ascent(), text)
    temp_painter.end()

    # Scale up with a nearest-neighbor to pixelate
    pixelated = img.scaled(
        text_width * scale,
        text_height * scale,
        Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.FastTransformation  # must be positional, not keyword
    )

    painter.drawImage(x, y, pixelated)

def load_obj(path):
    vertices = []
    uvs = []
    faces = []

    with open(path, "r") as f:
        for line in f:
            if line.startswith("v "):
                vertices.append(list(map(float, line.split()[1:4])))
            elif line.startswith("vt "):
                uvs.append(list(map(float, line.split()[1:3])))
            elif line.startswith("f "):
                face = []
                for v in line.split()[1:]:
                    # OBJ format: v/vt/vn (vn optional)
                    vals = v.split("/")
                    v_idx = int(vals[0]) - 1
                    vt_idx = int(vals[1]) - 1 if len(vals) > 1 and vals[1] else 0
                    face.append((v_idx, vt_idx))
                faces.append(face)

    return np.array(vertices, dtype=np.float32), np.array(uvs, dtype=np.float32), faces


class ArrowComboWidget(QWidget):
    def __init__(self, parent, items_list=None, opener=None):
        super().__init__()
        self.main_widget = parent
        if items_list is None:
            items_list = []
        self.weapons_name = json.load(open('VagrantStory_data/weapon_name_map.txt'))

        self.opener = opener
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.left_button = QPushButton("◀")
        self.right_button = QPushButton("▶")
        self.combo = QComboBox()

        self.left_button.setFixedWidth(30)
        self.right_button.setFixedWidth(30)

        self.combo.addItems(list(self.weapons_name.keys()))

        layout.addWidget(self.left_button)
        layout.addWidget(self.combo)
        layout.addWidget(self.right_button)

        self.combo.currentTextChanged.connect(self.update_mesh)
        self.left_button.clicked.connect(self.prev_item)
        self.right_button.clicked.connect(self.next_item)

    def update_mesh(self):
        self.main_widget.open_this(self.get_current_file())

    def get_current_file(self):
        return "{}.wep".format(self.weapons_name[self.combo.currentText()])

    def prev_item(self):
        index = self.combo.currentIndex()
        if index > 0:
            self.combo.setCurrentIndex(index - 1)

    def next_item(self):
        index = self.combo.currentIndex()
        if index < self.combo.count() - 1:
            self.combo.setCurrentIndex(index + 1)


class LevelSelector(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.main_widget = parent

        self.levels_data = json.load(open('VagrantStory_data/level_map_names.json'))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.left_button = QPushButton("◀")
        self.right_button = QPushButton("▶")
        self.combo = QComboBox()

        self.left_button.setFixedWidth(30)
        self.right_button.setFixedWidth(30)

        for zone, rooms in self.levels_data.items():
            self.combo.addItem('--{}'.format(zone))
            for room in rooms:
                self.combo.addItem(room[-1],
                                   ('ZONE{}{}.ZND'.format('0' * (3 - len(str(room[0]))), room[0]), room[1], room[2]))
        # self.combo.addItems([self.prepare_list_entry(room[0],room[1],room[2], room[-1]) for rooms in self.levels_data.values() for room in rooms])

        layout.addWidget(self.left_button)
        layout.addWidget(self.combo)
        layout.addWidget(self.right_button)

        self.combo.currentTextChanged.connect(self.update_mesh)
        self.left_button.clicked.connect(self.prev_item)
        self.right_button.clicked.connect(self.next_item)

    def update_mesh(self):
        if '--' in self.combo.currentText():
            return
        z, i, m = self.combo.currentData()
        self.main_widget.open_mpd('VagrantStory_data/MAP/{}'.format(m), 'VagrantStory_data/MAP/{}'.format(z))
        self.main_widget.setWindowTitle('VSTOOL -- {}'.format(self.combo.currentText()))

    def get_current_file(self):
        print(self.combo.currentText())

    def prev_item(self):
        index = self.combo.currentIndex()
        if index > 0:
            self.combo.setCurrentIndex(index - 1)

    def next_item(self):
        index = self.combo.currentIndex()
        if index < self.combo.count() - 1:
            self.combo.setCurrentIndex(index + 1)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.level_selector = None
        self.weapon_selector = None
        self.setWindowTitle("VSTOOLS")
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

        font_id = QFontDatabase.addApplicationFont("animeace2_reg.ttf")
        font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
        comic_font = QFont(font_family, 6)

        # Load paper texture
        paper_texture = QPixmap("paper_noise.jpg")  # grayscale or color paper texture

        hud_text = """
        🖱 Camera Controls
        
        LMB ------------------ Orbit
        Shift + LMB ---------- Pan
        MMB ----------------- Dolly
        Wheel --------------- Zoom
        Ctrl + Wheel -------- FOV

        W/A/S/D ----------- Move Camera
        Q/E ----------------- Up/Down
        H -------------------- Hide HUD"""

        self.hud = ComicHUD(hud_text, comic_font, paper_texture, parent=self.viewport)
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
        weapon_list = glob.glob("VagrantStory_data/**/**.wep", recursive=True)

        self.weapon_selector = ArrowComboWidget(self, weapon_list, self.open_wep)
        self.level_selector = LevelSelector(self)
        layout.addWidget(QLabel('Weapons'))
        layout.addWidget(self.weapon_selector)
        layout.addWidget(QLabel('Levels'))
        layout.addWidget(self.level_selector)

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


        for text in [
            "Use Normal Material",
            "Show Skeleton",
        ]:
            layout.addWidget(QCheckBox(text))

        return box

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

    def open_shp(self, path=None):
        reader = self.get_reader(path, 'SHP')
        if not reader:
            return

        shp = SHP(reader)
        shp.read()
        shp.build()
        seq = self.open_seq()
        bone_index = {x: shp.skeleton.bones.index(x) for x in shp.skeleton.bones}
        parent_h = {}
        for b in shp.skeleton.bones:
            parent_h[bone_index[b]] = []
            for c in b.children:
                parent_h[bone_index[b]].append(bone_index[c])
        self.viewport.current_animation = seq.animations[0]
        # shp.skeleton.update()
        # export_bvh(  seq.animations[10], filename="walk.bvh", skeleton=shp.skeleton )
        # export_bvh(            'test.bvh',            seq,            0,            parent_h,            [(x.position.x, x.position.y, x.position.z) for x in shp.skeleton.bones],            fps=30)

        self.viewport.activeSHP = shp
        self.viewport.activeSEQ = seq

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

    def sort_geometry(self, batch, mesh, type):

        pos = mesh.geometry.attributes["positions"]
        uv = mesh.geometry.attributes["uvs"]
        idx = mesh.geometry.attributes["indices"]
        col = mesh.geometry.attributes["colors"]

        if type == 'wep':
            batch['SkinnedMesh'] = mesh
            batch['Skeleton'] = self.opened_file.skeleton
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



class ComicHUD(QWidget):
    def __init__(self, text: str, font: QFont, texture: QPixmap, parent=None, landscape_factor: float = 2.2):
        super().__init__(parent)
        self.needs_redraw = True
        self.text = text
        self.font = font
        self.texture = texture
        self.landscape_factor = landscape_factor
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.jag_count = 10  # jag points per side
        self.jag_amp_x = 8  # horizontal jag amplitude
        self.jag_amp_y = 6  # vertical jag amplitude
        self.tail_height = 50  # tail height
        self.tail_width = 30  # tail half-width
        self.bevel_max = 9  # max random bevel per corner
        self.updateSize()

    def updateText(self, text: str):
        self.text = text
        self.updateSize()
        self.update()

    def updateSize(self):
        """Calculate the widget size based on text and landscape factor."""
        metrics = self.fontMetrics()
        lines = self.text.splitlines()
        text_width = max([metrics.horizontalAdvance(line) for line in lines])
        text_height = metrics.height() * len(lines)

        padding = 24
        width = int((text_width + padding) * self.landscape_factor)
        height = int(text_height + padding + self.tail_height * 2.5)
        self.resize(width, height)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        w, h = self.width(), self.height() - self.tail_height
        path = QPainterPath()
        tail_path = QPainterPath()

        # --- Function to get jagged point with random bevel ---
        def jagged_x(base, amp):
            random.seed(SEED)
            return base + random.randint(-amp, amp)

        def jagged_y(base, amp):
            random.seed(SEED)
            return base + random.randint(-amp, amp)

        # --- Top edge ---
        step = w / self.jag_count
        x, y = 0, jagged_y(0, self.jag_amp_y)
        path.moveTo(x, y)
        for i in range(1, self.jag_count + 1):
            x = i * step
            y = jagged_y(0, self.jag_amp_y)
            # Apply random corner bevel occasionally
            if i % (self.jag_count // 2) == 0:
                random.seed(SEED)
                y += random.randint(-self.bevel_max, self.bevel_max)
            path.lineTo(x, y)

        # --- Right edge ---
        step = h / self.jag_count
        for i in range(1, self.jag_count + 1):
            x = w + jagged_x(0, self.jag_amp_x)
            y = i * step
            if i % (self.jag_count // 2) == 0:
                random.seed(SEED)
                x += random.randint(-self.bevel_max, self.bevel_max)
            path.lineTo(x, y)

        # --- Tail pointing down (centered horizontally) ---
        tail_center_x = w // 1.2
        tail_path.lineTo(tail_center_x + self.tail_width, h)
        tail_path.lineTo(tail_center_x + self.tail_width * 2, h + self.tail_height)
        tail_path.lineTo(tail_center_x - self.tail_width, h)
        tail_path.closeSubpath()

        # --- Bottom edge ---
        step = w / self.jag_count
        for i in range(1, self.jag_count + 1):
            x = w - i * step
            y = h + jagged_y(0, self.jag_amp_y)
            if i % (self.jag_count // 2) == 0:
                random.seed(SEED)
                y -= random.randint(0, self.bevel_max)
            path.lineTo(x, y)

        # --- Left edge ---
        step = h / self.jag_count
        for i in range(1, self.jag_count + 1):
            x = jagged_x(0, self.jag_amp_x)
            y = h - i * step
            if i % (self.jag_count // 2) == 0:
                random.seed(SEED)
                x += random.randint(-self.bevel_max, self.bevel_max)
            path.lineTo(x, y)
        path.closeSubpath()

        bubble_path = QPainterPath()
        bubble_path.setFillRule(Qt.FillRule.WindingFill)
        bubble_path.addPath(path)
        bubble_path.addPath(tail_path)
        # --- Comic shadow (ink offset) ---

        shadow_offset = QPoint(6, 6)
        shadow_path = bubble_path.translated(shadow_offset)

        painter.save()
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 255))  # semi-transparent ink
        painter.drawPath(shadow_path)
        painter.restore()

        # Outline
        painter.setPen(QColor(0, 0, 0))
        painter.drawPath(bubble_path)

        # Fill
        painter.save()
        painter.setClipPath(bubble_path)
        painter.drawTiledPixmap(self.rect(), self.texture)
        painter.restore()

        # --- Draw text ---
        painter.setFont(self.font)
        painter.setPen(QColor(0, 0, 0))
        metrics = painter.fontMetrics()
        x_pad, y_pad = 16, 16
        scale = 2  # how blocky the text is
        y_text = y_pad
        for line in self.text.splitlines():
            drawPixelatedText(painter, line, x_pad, y_text, self.font, scale=scale, color=QColor(0, 0, 0))
            metrics = painter.fontMetrics()
            y_text += metrics.height() * scale


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
