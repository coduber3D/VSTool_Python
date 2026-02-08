import random
import json
from PySide6.QtCore import QPoint
from PySide6.QtGui import QFont, QPixmap, QPainter, QColor, QFontMetrics, Qt, QImage, QPainterPath
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QComboBox

SEED = random.randint(0, 100)

class HudComicStyle(QWidget):
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

    @staticmethod
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
        painter.setPen(Qt.PenStyle.NoPen)
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

        x_pad, y_pad = 16, 16
        scale = 2  # how blocky the text is
        y_text = y_pad
        for line in self.text.splitlines():
            self.drawPixelatedText(painter, line, x_pad, y_text, self.font, scale=scale, color=QColor(0, 0, 0))
            metrics = painter.fontMetrics()
            y_text += metrics.height() * scale


class ArrowComboBase(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.main_widget = parent

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.left_button = QPushButton("<")
        self.right_button = QPushButton(">")
        self.combo = QComboBox()

        self.left_button.setFixedWidth(30)
        self.right_button.setFixedWidth(30)

        layout.addWidget(self.left_button)
        layout.addWidget(self.combo)
        layout.addWidget(self.right_button)

        self.left_button.clicked.connect(self.prev_item)
        self.right_button.clicked.connect(self.next_item)
        self.combo.currentIndexChanged.connect(self.on_changed)

    # ---- shared behavior ----

    def prev_item(self):
        index = self.combo.currentIndex()
        if index > 0:
            self.combo.setCurrentIndex(index - 1)

    def next_item(self):
        index = self.combo.currentIndex()
        if index < self.combo.count() - 1:
            self.combo.setCurrentIndex(index + 1)

    # ---- hooks for subclasses ----

    def populate(self):
        """Override: fill the combo"""
        raise NotImplementedError

    def on_changed(self, index):
        """Override: react to selection"""
        raise NotImplementedError


class WeaponSelector(ArrowComboBase):
    def __init__(self, parent):
        super().__init__(parent)

        self.weapons_name = json.load(
            open('VagrantStory_data/weapon_name_map.json')
        )

        self.populate()

    def populate(self):
        self.combo.addItems(self.weapons_name.keys())

    def on_changed(self, index):
        current_weapon = self.combo.currentText()
        if current_weapon:
            weapon_file_path = "{}.wep".format(self.weapons_name[current_weapon])
            self.main_widget.open_this(weapon_file_path)


class LevelSelector(ArrowComboBase):
    def __init__(self, parent):
        super().__init__(parent)

        self.levels_data = json.load(
            open('VagrantStory_data/level_map_names.json')
        )

        self.populate()

    def populate(self):
        for zone, rooms in self.levels_data.items():
            self.combo.addItem('--{}'.format(zone))
            for room in rooms:
                self.combo.addItem(
                    room[-1],
                    (
                        f"ZONE{room[0]:03}.ZND",
                        room[1],
                        room[2],
                    )
                )

    def on_changed(self, index):
        text = self.combo.currentText()
        if text.startswith('--'):
            return

        z, i, m = self.combo.currentData()
        self.main_widget.open_mpd(
            'VagrantStory_data/MAP/{}'.format(m),
            'VagrantStory_data/MAP/{}'.format(z)
        )
        self.main_widget.setWindowTitle('Vagrant Story Tool -- {}'.format(text))


class CharacterSelector(ArrowComboBase):
    def __init__(self, parent):
        super().__init__(parent)

        self.characters_data = json.load(
            open('VagrantStory_data/characters.json')
        )

        self.populate()

    def populate(self):
        self.combo.addItems(self.characters_data.values())

    def on_changed(self, index):
        current_character = self.combo.currentText()
        if '?????' not in current_character:
            character_path = "VagrantStory_data/OBJ/{}".format([x for x in self.characters_data if self.characters_data[x]== current_character][0])
            self.main_widget.open_shp(character_path, autoload_anim=True)