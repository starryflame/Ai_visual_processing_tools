"""
图片裁剪工具 - 支持比例裁剪、预览、逐张/批量操作
拖拽文件夹导入图片，选择比例和位置后裁剪导出
"""
import os
import sys
import math
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QListWidget, QFileDialog, QProgressBar,
    QComboBox, QTextEdit, QGroupBox, QFrame, QMessageBox,
    QListWidgetItem, QSplitter, QSpinBox, QAbstractItemView,
)
from PyQt5.QtCore import Qt, QMimeData, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QPixmap, QImage, QPainter, QColor, QPen


IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.tiff', '.tif'}

# 预设比例
ASPECT_PRESETS = [
    ("原始比例 (自适应)", None),
    ("1:1 (正方形)", (1, 1)),
    ("4:3", (4, 3)),
    ("3:4", (3, 4)),
    ("16:9", (16, 9)),
    ("9:16", (9, 16)),
    ("3:2", (3, 2)),
    ("2:3", (2, 3)),
    ("5:4", (5, 4)),
    ("4:5", (4, 5)),
    ("21:9", (21, 9)),
    ("9:21", (9, 21)),
]


def resolve_path(path):
    """如果文件已存在，返回加序号的不重名路径"""
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    i = 1
    while True:
        new_path = f"{base}_{i}{ext}"
        if not os.path.exists(new_path):
            return new_path
        i += 1


# =============================================================================
#  Crop data structure
# =============================================================================

class CropConfig:
    """单张图片的裁剪配置"""
    def __init__(self, aspect_ratio=None, position='center'):
        self.aspect_ratio = aspect_ratio  # (w, h) or None = auto
        self.position = position  # 'top'/'bottom'/'left'/'right'/'center'


# =============================================================================
#  Worker thread
# =============================================================================

class CropWorker(QThread):
    """批量裁剪工作线程"""
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(int, int)

    def __init__(self, tasks):
        """
        tasks: list of (src_path, dst_path, crop_config, orig_index)
        """
        super().__init__()
        self.tasks = tasks

    def run(self):
        from PIL import Image
        total = len(self.tasks)
        success = 0
        failed = 0
        for idx, (src, dst, config, _orig_idx) in enumerate(self.tasks):
            self.progress.emit(idx + 1, total, f"处理中: {os.path.basename(src)}")
            try:
                img = Image.open(src)
                w, h = img.size

                # 计算裁剪区域
                x1, y1, x2, y2 = compute_crop_box(w, h, config)
                cropped = img.crop((x1, y1, x2, y2))

                os.makedirs(os.path.dirname(dst), exist_ok=True)
                ext = os.path.splitext(src)[1].lower()
                if ext in ('.jpg', '.jpeg'):
                    if cropped.mode in ('RGBA', 'P', 'LA'):
                        cropped = cropped.convert('RGB')
                    cropped.save(dst, 'JPEG', quality=95)
                elif ext == '.png':
                    cropped.save(dst, 'PNG')
                elif ext == '.webp':
                    cropped.save(dst, 'WEBP', quality=95)
                else:
                    if cropped.mode in ('RGBA', 'P', 'LA'):
                        cropped = cropped.convert('RGB')
                    cropped.save(dst, 'JPEG', quality=95)
                success += 1
            except Exception:
                failed += 1
        self.finished.emit(success, failed)


def compute_crop_box(img_w, img_h, config):
    """根据图片和配置，计算裁剪区域 (x1, y1, x2, y2)"""
    aspect = config.aspect_ratio

    if aspect is None:
        # 原始比例 → 不裁剪，返回全图
        return (0, 0, img_w, img_h)

    ratio_w, ratio_h = aspect
    target_ratio = ratio_w / ratio_h
    img_ratio = img_w / img_h

    if abs(img_ratio - target_ratio) < 1e-6:
        return (0, 0, img_w, img_h)

    if img_ratio > target_ratio:
        # 图片更宽 → 裁左右
        new_w = int(img_h * target_ratio)
        new_h = img_h
        pos = config.position
        if pos == 'left':
            x1 = 0
        elif pos == 'right':
            x1 = img_w - new_w
        else:
            x1 = (img_w - new_w) // 2
        y1 = 0
    else:
        # 图片更高 → 裁上下
        new_w = img_w
        new_h = int(img_w / target_ratio)
        pos = config.position
        if pos == 'top':
            y1 = 0
        elif pos == 'bottom':
            y1 = img_h - new_h
        else:
            y1 = (img_h - new_h) // 2
        x1 = 0

    x2 = min(x1 + new_w, img_w)
    y2 = min(y1 + new_h, img_h)

    # 安全修正
    if x2 <= x1:
        x2 = img_w
        x1 = 0
    if y2 <= y1:
        y2 = img_h
        y1 = 0

    return (x1, y1, x2, y2)


# =============================================================================
#  Preview widget with crop overlay
# =============================================================================

class PreviewLabel(QLabel):
    """带裁剪区域叠加显示的预览标签"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("background-color: #2b2b2b; border-radius: 5px;")
        self.setMinimumSize(300, 300)
        self.pixmap = None
        self.crop_box = None  # (x1, y1, x2, y2) in scaled coords
        self.img_w = 0
        self.img_h = 0

    def set_image_and_crop(self, pixmap, crop_box, img_w, img_h):
        self.pixmap = pixmap
        self.crop_box = crop_box
        self.img_w = img_w
        self.img_h = img_h
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.pixmap is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        pw = self.width()
        ph = self.height()
        pm_w = self.pixmap.width()
        pm_h = self.pixmap.height()

        # 居中偏移
        ox = (pw - pm_w) // 2
        oy = (ph - pm_h) // 2

        # 绘制图片
        painter.drawPixmap(ox, oy, self.pixmap)

        if self.crop_box:
            x1, y1, x2, y2 = self.crop_box

            # 裁剪区域外的暗化区域
            painter.setBrush(QColor(0, 0, 0, 140))
            painter.setPen(Qt.NoPen)
            # 上
            painter.drawRect(0, 0, pw, y1)
            # 下
            painter.drawRect(0, y2, pw, ph - y2)
            # 左
            painter.drawRect(0, y1, x1, y2 - y1)
            # 右
            painter.drawRect(x2, y1, pw - x2, y2 - y1)

            # 裁剪框边框
            pen = QPen(QColor(255, 255, 255), 2, Qt.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(x1, y1, x2 - x1, y2 - y1)

            # 九宫格辅助线
            pen = QPen(QColor(255, 255, 255, 100), 1, Qt.DashLine)
            painter.setPen(pen)
            # 竖线
            cw = (x2 - x1) / 3
            painter.drawLine(int(x1 + cw), y1, int(x1 + cw), y2)
            painter.drawLine(int(x1 + cw * 2), y1, int(x1 + cw * 2), y2)
            # 横线
            ch = (y2 - y1) / 3
            painter.drawLine(x1, int(y1 + ch), x2, int(y1 + ch))
            painter.drawLine(x1, int(y1 + ch * 2), x2, int(y1 + ch * 2))

        painter.end()


# =============================================================================
#  Drop frame for drag & drop
# =============================================================================

class DropFrame(QFrame):
    """支持拖拽的容器"""
    folder_dropped = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setStyleSheet("""
            QFrame {
                border: 2px dashed #aaa;
                border-radius: 8px;
                padding: 20px;
                background-color: #f8f8f8;
            }
            QFrame.drag-over {
                border: 2px solid #4CAF50;
                background-color: #e8f5e9;
            }
        """)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setProperty("class", "drag-over")
            self.style().unpolish(self)
            self.style().polish(self)

    def dragLeaveEvent(self, event):
        self.setProperty("class", "")
        self.style().unpolish(self)
        self.style().polish(self)

    def dropEvent(self, event):
        self.setProperty("class", "")
        self.style().unpolish(self)
        self.style().polish(self)
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if os.path.isdir(path):
                self.folder_dropped.emit(path)
            elif os.path.isfile(path):
                self.folder_dropped.emit(os.path.dirname(path))
        event.acceptProposedAction()


# =============================================================================
#  Thumbnail widget with custom painting
# =============================================================================

class ThumbnailItem(QWidget):
    """缩略图列表项"""
    clicked = pyqtSignal(int)

    def __init__(self, index, filename, pixmap, parent=None):
        super().__init__(parent)
        self.index = index
        self.filename = filename
        self.pixmap = pixmap
        self.setFixedHeight(80)
        self._selected = False

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        w = self.width()
        h = self.height()

        # 背景
        if self._selected:
            painter.fillRect(0, 0, w, h, QColor(33, 150, 243, 60))
            painter.fillRect(0, 0, 3, h, QColor(33, 150, 243))
        else:
            painter.fillRect(0, 0, w, h, QColor(255, 255, 255))

        # 缩略图
        if self.pixmap:
            thumb = self.pixmap.scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            painter.drawImage(10, (h - 60) // 2, thumb.toImage())

        # 文件名
        painter.setPen(QColor(50, 50, 50))
        font = painter.font()
        font.setPixelSize(36)
        painter.setFont(font)
        painter.drawText(80, h // 2 - 8, f"{self.index + 1}. {self.filename}")
        painter.end()

    def set_selected(self, selected):
        self._selected = selected
        self.update()

    def mousePressEvent(self, event):
        self.clicked.emit(self.index)


# =============================================================================
#  Main Window
# =============================================================================

class ImageCropperApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.image_paths = []
        self.crop_configs = {}  # index -> CropConfig
        self.current_index = -1
        self.worker = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("图片裁剪工具")
        self.resize(1200, 800)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # ===================== 左侧面板 =====================
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(8)
        left_layout.setContentsMargins(5, 5, 5, 5)

        # 拖拽区域
        self.drop_frame = DropFrame(self)
        drop_layout = QVBoxLayout(self.drop_frame)
        drop_layout.setSpacing(3)
        lbl = QLabel("将文件夹拖拽到此处")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("font-size: 54px; color: #666;")
        drop_layout.addWidget(lbl)
        sub = QLabel("或点击下方按钮选择")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet("font-size: 39px; color: #999;")
        drop_layout.addWidget(sub)
        left_layout.addWidget(self.drop_frame)

        self.drop_frame.folder_dropped.connect(self.on_folder_selected)

        # 按钮行
        btn_row = QHBoxLayout()
        self.select_btn = QPushButton("选择文件夹")
        self.select_btn.setStyleSheet(self._btn_style("#2196F3"))
        self.select_btn.clicked.connect(self.browse_folder)
        btn_row.addWidget(self.select_btn)

        self.clear_btn = QPushButton("清空")
        self.clear_btn.setStyleSheet(self._btn_style("#9e9e9e"))
        self.clear_btn.clicked.connect(self.clear_list)
        btn_row.addWidget(self.clear_btn)
        left_layout.addLayout(btn_row)

        self.folder_label = QLabel("未选择文件夹")
        self.folder_label.setStyleSheet("color: #666; font-size: 36px;")
        self.folder_label.setWordWrap(True)
        left_layout.addWidget(self.folder_label)

        # 图片列表
        list_label = QLabel("图片列表:")
        list_label.setFont(QFont("", 30, QFont.Bold))
        left_layout.addWidget(list_label)

        self.list_widget = QListWidget()
        self.list_widget.setSpacing(2)
        self.list_widget.setStyleSheet("""
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 5px;
                background-color: #fff;
            }
            QListWidget::item {
                padding: 4px;
                border-bottom: 1px solid #f0f0f0;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
            }
        """)
        self.list_widget.currentRowChanged.connect(self.on_image_selected)
        left_layout.addWidget(self.list_widget, 1)

        main_layout.addWidget(left_panel, 1)

        # ===================== 中间面板 - 预览 =====================
        center_panel = QWidget()
        center_layout = QVBoxLayout(center_panel)
        center_layout.setSpacing(8)
        center_layout.setContentsMargins(5, 5, 5, 5)

        self.preview_label = PreviewLabel()
        center_layout.addWidget(self.preview_label, 1)

        # 图片信息
        self.info_label = QLabel("请导入图片文件夹")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setStyleSheet("color: #999; font-size: 39px;")
        center_layout.addWidget(self.info_label)

        # 导航
        nav_row = QHBoxLayout()
        self.prev_btn = QPushButton("上一张")
        self.prev_btn.setStyleSheet(self._btn_style("#607d8b"))
        self.prev_btn.clicked.connect(self.prev_image)
        nav_row.addWidget(self.prev_btn)

        self.img_counter = QLabel("0 / 0")
        self.img_counter.setAlignment(Qt.AlignCenter)
        nav_row.addWidget(self.img_counter)

        self.next_btn = QPushButton("下一张")
        self.next_btn.setStyleSheet(self._btn_style("#607d8b"))
        self.next_btn.clicked.connect(self.next_image)
        nav_row.addWidget(self.next_btn)
        center_layout.addLayout(nav_row)

        main_layout.addWidget(center_panel, 3)

        # ===================== 右侧面板 - 设置 =====================
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(8)
        right_layout.setContentsMargins(5, 5, 5, 5)

        # 比例设置
        ratio_group = QGroupBox("裁剪比例")
        ratio_layout = QVBoxLayout(ratio_group)
        self.aspect_combo = QComboBox()
        for name, _ in ASPECT_PRESETS:
            self.aspect_combo.addItem(name)
        self.aspect_combo.setStyleSheet("font-size: 39px;")
        self.aspect_combo.setCurrentIndex(1)  # 默认 1:1
        self.aspect_combo.currentIndexChanged.connect(self.on_aspect_changed)
        ratio_layout.addWidget(self.aspect_combo)
        right_layout.addWidget(ratio_group)

        # 位置设置
        pos_group = QGroupBox("裁剪位置")
        pos_layout = QVBoxLayout(pos_group)

        self.pos_combo = QComboBox()
        self.pos_combo.addItems(["居中", "偏上", "偏下", "偏左", "偏右"])
        self.pos_combo.setStyleSheet("font-size: 39px;")
        self.pos_combo.currentIndexChanged.connect(self.on_position_changed)
        pos_layout.addWidget(self.pos_combo)

        self.pos_hint = QLabel("竖图: 上/下/居中 | 横图: 左/右/居中")
        self.pos_hint.setStyleSheet("color: #999; font-size: 33px;")
        self.pos_hint.setWordWrap(True)
        pos_layout.addWidget(self.pos_hint)
        right_layout.addWidget(pos_group)

        # 输出设置
        out_group = QGroupBox("输出设置")
        out_layout = QVBoxLayout(out_group)

        self.output_label = QLabel("输出目录: 与源文件同目录 /output_crop")
        self.output_label.setStyleSheet("font-size: 36px; color: #555;")
        self.output_label.setWordWrap(True)
        out_layout.addWidget(self.output_label)

        self.custom_output_btn = QPushButton("自定义输出目录")
        self.custom_output_btn.setStyleSheet(self._btn_style("#607d8b"))
        self.custom_output_btn.clicked.connect(self.browse_output)
        out_layout.addWidget(self.custom_output_btn)

        self.quality_label = QLabel("JPEG 质量:")
        out_layout.addWidget(self.quality_label)
        self.quality_spin = QSpinBox()
        self.quality_spin.setRange(50, 100)
        self.quality_spin.setValue(95)
        self.quality_spin.setStyleSheet("font-size: 39px;")
        out_layout.addWidget(self.quality_spin)
        right_layout.addWidget(out_group)

        # 操作按钮
        action_group = QGroupBox("操作")
        action_layout = QVBoxLayout(action_group)

        self.apply_btn = QPushButton("应用到当前图片")
        self.apply_btn.setStyleSheet(self._btn_style("#FF9800"))
        self.apply_btn.clicked.connect(self.apply_current)
        action_layout.addWidget(self.apply_btn)

        self.apply_all_btn = QPushButton("应用到全部图片")
        self.apply_all_btn.setStyleSheet(self._btn_style("#f44336"))
        self.apply_all_btn.clicked.connect(self.apply_all)
        action_layout.addWidget(self.apply_all_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 5px;
                text-align: center;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 4px;
            }
        """)
        action_layout.addWidget(self.progress_bar)

        self.export_btn = QPushButton("导出裁剪图片")
        self.export_btn.setStyleSheet(self._btn_style("#4CAF50", bold=True))
        self.export_btn.setFont(QFont("", 36, QFont.Bold))
        self.export_btn.clicked.connect(self.start_crop)
        action_layout.addWidget(self.export_btn)

        right_layout.addWidget(action_group)

        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #666; font-size: 36px;")
        self.status_label.setWordWrap(True)
        right_layout.addWidget(self.status_label)

        right_layout.addStretch(1)
        main_layout.addWidget(right_panel, 1)

        # 默认配置
        self._default_aspect_idx = 1  # 1:1
        self._default_position_idx = 0

    def keyPressEvent(self, event):
        """键盘快捷键: 上下左右选位置, 空格居中, 翻页切换图片"""
        if self.current_index < 0:
            super().keyPressEvent(event)
            return

        key = event.key()
        if key == Qt.Key_Up:
            self.pos_combo.setCurrentText("偏上")
        elif key == Qt.Key_Down:
            self.pos_combo.setCurrentText("偏下")
        elif key == Qt.Key_Left:
            self.pos_combo.setCurrentText("偏左")
        elif key == Qt.Key_Right:
            self.pos_combo.setCurrentText("偏右")
        elif key == Qt.Key_Space:
            self.pos_combo.setCurrentText("居中")
        elif key == Qt.Key_W or key == Qt.Key_Q:
            self.prev_image()
            return
        elif key == Qt.Key_E or key == Qt.Key_S:
            self.next_image()
            return
        else:
            super().keyPressEvent(event)
            return

        self._update_current_config()
        self.show_image(self.current_index)

    # =================================================================
    #  Style helpers
    # =================================================================

    def _btn_style(self, color, h=30, bold=False):
        weight = "bold" if bold else "normal"
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                padding: 5px 12px;
                font-size: 39px;
                font-weight: {weight};
                border-radius: 4px;
                min-height: {h}px;
            }}
            QPushButton:hover {{
                background-color: {self._darken(color)};
            }}
            QPushButton:pressed {{
                background-color: {self._darken(color, 40)};
            }}
            QPushButton:disabled {{
                background-color: #ccc;
            }}
        """

    def _darken(self, color, amount=20):
        from PyQt5.QtGui import QColor
        c = QColor(color)
        return c.darker(100 + amount).name()

    # =================================================================
    #  Folder operations
    # =================================================================

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择图片文件夹")
        if folder:
            self.on_folder_selected(folder)

    def on_folder_selected(self, folder):
        folder = os.path.normpath(folder)
        self.folder_label.setText(folder)
        self.image_paths = []
        self.crop_configs.clear()
        self.list_widget.clear()

        for root, dirs, files in os.walk(folder):
            for f in files:
                if os.path.splitext(f)[1].lower() in IMAGE_EXTENSIONS:
                    self.image_paths.append(os.path.join(root, f))

        self.image_paths.sort(key=lambda p: os.path.basename(p).lower())

        for p in self.image_paths:
            name = os.path.basename(p)
            item = QListWidgetItem(name)
            self.list_widget.addItem(item)

        self.status_label.setText(f"找到 {len(self.image_paths)} 张图片")
        self.img_counter.setText(f"0 / {len(self.image_paths)}")

        if self.image_paths:
            self.list_widget.setCurrentRow(0)
            self.show_image(0)

    def clear_list(self):
        self.image_paths = []
        self.crop_configs.clear()
        self.list_widget.clear()
        self.folder_label.setText("未选择文件夹")
        self.status_label.setText("已清空")
        self.img_counter.setText("0 / 0")
        self.preview_label.set_image_and_crop(None, None, 0, 0)
        self.info_label.setText("请导入图片文件夹")
        self.current_index = -1
        # 重置 UI 为默认值
        self.aspect_combo.setCurrentIndex(1)  # 1:1
        self.pos_combo.setCurrentText("居中")

    # =================================================================
    #  Image display
    # =================================================================

    def show_image(self, index):
        if index < 0 or index >= len(self.image_paths):
            return

        # 切换前先保存旧图的配置
        if self.current_index >= 0:
            self.crop_configs[self.current_index] = CropConfig(
                self._get_aspect(), self._get_position()
            )

        self.current_index = index
        path = self.image_paths[index]

        try:
            img = QImage(path)
            if img.isNull():
                self.info_label.setText(f"无法加载: {os.path.basename(path)}")
                return

            pm = QPixmap.fromImage(img)
            img_w, img_h = pm.width(), pm.height()

            # 获取当前配置
            config = self.crop_configs.get(index)
            if config is None:
                # 新图片默认使用1:1居中
                config = CropConfig((1, 1), "center")
                self.crop_configs[index] = config

            # 更新 UI 显示当前图片的配置
            self._sync_ui_to_config(config)

            # 计算裁剪区域（在预览缩放后坐标中）
            preview_w = self.preview_label.width()
            preview_h = self.preview_label.height()
            scale = min(preview_w / img_w, preview_h / img_h)
            scaled_w = int(img_w * scale)
            scaled_h = int(img_h * scale)
            offset_x = (preview_w - scaled_w) // 2
            offset_y = (preview_h - scaled_h) // 2

            # 计算裁剪框在原图中的位置
            box = compute_crop_box(img_w, img_h, config)
            bx1, by1, bx2, by2 = box

            # 转换到预览坐标
            sbx1 = int(bx1 * scale) + offset_x
            sby1 = int(by1 * scale) + offset_y
            sbx2 = int(bx2 * scale) + offset_x
            sby2 = int(by2 * scale) + offset_y

            crop_box = (sbx1, sby1, sbx2, sby2)

            # 缩放图片用于预览
            scaled_pm = pm.scaled(
                self.preview_label.width(),
                self.preview_label.height(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )

            self.preview_label.set_image_and_crop(scaled_pm, crop_box, img_w, img_h)

            # 更新信息
            size_kb = os.path.getsize(path) / 1024
            self.info_label.setText(
                f"{os.path.basename(path)}  |  {img_w} x {img_h}  |  {size_kb:.1f} KB"
            )
            self.img_counter.setText(f"{index + 1} / {len(self.image_paths)}")

            # 高亮列表项
            self.list_widget.setCurrentRow(index)

        except Exception as e:
            self.info_label.setText(f"错误: {e}")

    def _get_aspect(self):
        idx = self.aspect_combo.currentIndex()
        _, val = ASPECT_PRESETS[idx]
        return val

    def _get_position(self):
        text = self.pos_combo.currentText()
        mapping = {
            "居中": "center",
            "偏上": "top",
            "偏下": "bottom",
            "偏左": "left",
            "偏右": "right",
        }
        return mapping.get(text, "center")

    def _sync_ui_to_config(self, config):
        """将配置同步到 UI 控件（不触发事件）"""
        was_blocked = self.aspect_combo.blockSignals(True)
        # 找到对应的比例
        for i, (name, val) in enumerate(ASPECT_PRESETS):
            if val == config.aspect_ratio:
                self.aspect_combo.setCurrentIndex(i)
                break
        self.aspect_combo.blockSignals(was_blocked)

        was_blocked = self.pos_combo.blockSignals(True)
        pos_map = {"center": "居中", "top": "偏上", "bottom": "偏下",
                   "left": "偏左", "right": "偏右"}
        self.pos_combo.setCurrentText(pos_map.get(config.position, "居中"))
        self.pos_combo.blockSignals(was_blocked)

    # =================================================================
    #  Navigation
    # =================================================================

    def on_image_selected(self, row):
        if row >= 0 and row < len(self.image_paths):
            self.show_image(row)

    def prev_image(self):
        if self.current_index > 0:
            self.show_image(self.current_index - 1)

    def next_image(self):
        if self.current_index < len(self.image_paths) - 1:
            self.show_image(self.current_index + 1)

    # =================================================================
    #  Setting change handlers
    # =================================================================

    def on_aspect_changed(self):
        if self.current_index >= 0:
            self._update_current_config()
            self.show_image(self.current_index)

    def on_position_changed(self):
        if self.current_index >= 0:
            self._update_current_config()
            self.show_image(self.current_index)

    def _update_current_config(self):
        """用当前 UI 值更新当前图片的配置"""
        if self.current_index < 0:
            return
        self.crop_configs[self.current_index] = CropConfig(
            self._get_aspect(), self._get_position()
        )

    # =================================================================
    #  Apply settings
    # =================================================================

    def apply_current(self):
        """应用当前 UI 设置到当前图片"""
        if self.current_index < 0:
            QMessageBox.warning(self, "提示", "请先选择一张图片")
            return
        self._update_current_config()
        self.show_image(self.current_index)
        self.status_label.setText(f"已应用到: {os.path.basename(self.image_paths[self.current_index])}")

    def apply_all(self):
        """应用当前 UI 设置到所有图片"""
        if not self.image_paths:
            QMessageBox.warning(self, "提示", "请先导入图片文件夹")
            return

        aspect = self._get_aspect()
        pos = self._get_position()
        for i in range(len(self.image_paths)):
            self.crop_configs[i] = CropConfig(aspect, pos)

        if self.current_index >= 0:
            self.show_image(self.current_index)

        self.status_label.setText(f"已应用统一规则到全部 {len(self.image_paths)} 张图片")

    # =================================================================
    #  Export
    # =================================================================

    def browse_output(self):
        folder = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if folder:
            self.output_label.setText(f"输出目录: {folder}")

    def get_output_dir(self):
        text = self.output_label.text()
        if text.startswith("输出目录: "):
            path = text[len("输出目录: "):]
            if path and os.path.isdir(path):
                return path
        # 默认: 源文件同目录 /output_crop
        if self.image_paths:
            src_dir = os.path.dirname(self.image_paths[0])
            return os.path.join(src_dir, "output_crop")
        return "output_crop"

    def start_crop(self):
        if not self.image_paths:
            QMessageBox.warning(self, "提示", "请先导入图片文件夹")
            return

        # 确保所有图片都有配置，没有的用当前 UI 设置
        default_aspect = self._get_aspect()
        default_pos = self._get_position()
        for i in range(len(self.image_paths)):
            if i not in self.crop_configs:
                self.crop_configs[i] = CropConfig(default_aspect, default_pos)

        output_dir = self.get_output_dir()
        quality = self.quality_spin.value()

        # 构建任务
        tasks = []
        for i, path in enumerate(self.image_paths):
            config = self.crop_configs[i]
            name = os.path.basename(path)
            dst = os.path.join(output_dir, name)
            dst = resolve_path(dst)
            tasks.append((path, dst, config, i))

        if not tasks:
            return

        self.export_btn.setEnabled(False)
        self.apply_btn.setEnabled(False)
        self.apply_all_btn.setEnabled(False)
        self.progress_bar.setValue(0)

        self.worker = CropWorker(tasks)
        self.worker.progress.connect(self.on_crop_progress)
        self.worker.finished.connect(self.on_crop_finished)
        self.worker.start()

    def on_crop_progress(self, current, total, msg):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.status_label.setText(msg)

    def on_crop_finished(self, success, failed):
        self.export_btn.setEnabled(True)
        self.apply_btn.setEnabled(True)
        self.apply_all_btn.setEnabled(True)
        self.progress_bar.setValue(self.progress_bar.maximum())
        self.status_label.setText(
            f"完成！成功: {success}  失败: {failed}  "
            f"输出目录: {self.get_output_dir()}"
        )
        if failed > 0:
            QMessageBox.information(self, "完成",
                                    f"导出完成\n成功: {success}\n失败: {failed}")


# =============================================================================
#  Entry point
# =============================================================================

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Microsoft YaHei UI", 16))
    window = ImageCropperApp()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
