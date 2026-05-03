"""
图片尺寸缩放工具
支持拖拽文件夹，批量压缩图片到指定大小以下
"""
import os
import sys
import shutil
from pathlib import Path

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QListWidget,
                             QFileDialog, QProgressBar, QSpinBox, QDoubleSpinBox,
                             QComboBox, QTextEdit, QGroupBox, QFrame,
                             QMessageBox, QLineEdit)
from PyQt5.QtCore import Qt, QMimeData, QThread, pyqtSignal
from PyQt5.QtGui import QDragEnterEvent, QDropEvent, QFont, QPixmap


IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.tiff', '.tif', '.gif'}


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


class ImageResizeWorker(QThread):
    """图片压缩工作线程"""
    progress = pyqtSignal(int, int, str)  # current, total, message
    finished = pyqtSignal(int, int, int)  # success, failed, skipped
    one_result = pyqtSignal(str, str, str)  # filename, original_size, new_size

    def __init__(self, image_paths, max_size_bytes, quality_step=5, output_dir=None):
        super().__init__()
        self.image_paths = image_paths
        self.max_size_bytes = max_size_bytes
        self.quality_step = quality_step
        self.output_dir = output_dir
        self.success_count = 0
        self.failed_count = 0
        self.skipped_count = 0

    def run(self):
        from PIL import Image
        import io

        total = len(self.image_paths)
        for idx, path in enumerate(self.image_paths):
            filename = os.path.basename(path)
            self.progress.emit(idx + 1, total, f"处理中: {filename}")

            try:
                original_size = os.path.getsize(path)

                # 如果原图已经小于目标大小，跳过
                if original_size <= self.max_size_bytes:
                    self.skipped_count += 1
                    if self.output_dir:
                        out_path = resolve_path(os.path.join(self.output_dir, filename))
                        os.makedirs(self.output_dir, exist_ok=True)
                        shutil.copy2(path, out_path)
                    self.one_result.emit(filename, f"{original_size / 1024:.1f} KB", "已跳过（未超限）")
                    continue

                img = Image.open(path)
                ext = os.path.splitext(path)[1].lower()

                # 确定输出格式
                if ext in ('.jpg', '.jpeg'):
                    save_ext = 'JPEG'
                    if img.mode in ('RGBA', 'P', 'LA'):
                        img = img.convert('RGB')
                elif ext == '.png':
                    save_ext = 'PNG'
                elif ext == '.webp':
                    save_ext = 'WEBP'
                elif ext == '.bmp':
                    save_ext = 'BMP'
                else:
                    save_ext = None

                # 不支持的格式转为 JPEG
                if save_ext is None or save_ext == 'BMP':
                    if img.mode in ('RGBA', 'P', 'LA'):
                        img = img.convert('RGB')
                    save_ext = 'JPEG'
                    ext = '.jpg'

                # 用 BytesIO 测试压缩后的大小
                def test_size(**kwargs):
                    buf = io.BytesIO()
                    img.save(buf, format=save_ext, **kwargs)
                    return buf.getbuffer().nbytes

                # 二分法搜索最佳 quality
                if save_ext == 'PNG':
                    low, high = 1, 9
                    best_compress = 1
                    for _ in range(10):
                        mid = (low + high) // 2
                        size = test_size(compress_level=mid)
                        if size <= self.max_size_bytes:
                            best_compress = mid
                            low = mid + 1
                        else:
                            high = mid - 1
                    final_kwargs = {'compress_level': best_compress}
                else:
                    # JPEG / WEBP: quality 越低 → 文件越小
                    low, high = 10, 100
                    best_quality = 10
                    for _ in range(10):
                        mid = (low + high) // 2
                        kw = {'quality': mid, 'method': 2} if save_ext == 'WEBP' else {'quality': mid}
                        size = test_size(**kw)
                        if size <= self.max_size_bytes:
                            best_quality = mid
                            low = mid + 1
                        else:
                            high = mid - 1

                    final_kwargs = {'quality': best_quality}
                    if save_ext == 'WEBP':
                        final_kwargs['method'] = 2

                    # quality 已经很低但还不够小 → 缩小尺寸
                    if best_quality <= 15:
                        scale = 0.8
                        for _ in range(15):
                            new_w = max(int(img.width * scale), 1)
                            new_h = max(int(img.height * scale), 1)
                            resized = img.resize((new_w, new_h), Image.LANCZOS)
                            buf = io.BytesIO()
                            resized.save(buf, format=save_ext, **final_kwargs)
                            if buf.getbuffer().nbytes <= self.max_size_bytes:
                                img = resized
                                break
                            scale *= 0.75

                # 写入文件
                if self.output_dir:
                    out_path = resolve_path(os.path.join(self.output_dir, os.path.splitext(filename)[0] + ext))
                    os.makedirs(self.output_dir, exist_ok=True)
                else:
                    out_path = path

                buf = io.BytesIO()
                img.save(buf, format=save_ext, **final_kwargs)
                with open(out_path, 'wb') as f:
                    f.write(buf.getvalue())

                new_size = os.path.getsize(out_path)
                self.success_count += 1
                self.one_result.emit(
                    filename,
                    f"{original_size / 1024:.1f} KB",
                    f"{new_size / 1024:.1f} KB"
                )

            except Exception as e:
                self.failed_count += 1
                if self.output_dir:
                    try:
                        shutil.copy2(path, resolve_path(os.path.join(self.output_dir, filename)))
                    except Exception:
                        pass
                self.one_result.emit(filename, "错误", str(e))

        self.finished.emit(self.success_count, self.failed_count, self.skipped_count)


class DropLineEdit(QFrame):
    """支持拖拽的容器"""
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

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setProperty("class", "drag-over")
            self.style().unpolish(self)
            self.style().polish(self)

    def dragLeaveEvent(self, event):
        self.setProperty("class", "")
        self.style().unpolish(self)
        self.style().polish(self)

    def dropEvent(self, event: QDropEvent):
        self.setProperty("class", "")
        self.style().unpolish(self)
        self.style().polish(self)
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            app = self.window()
            if os.path.isdir(path):
                app.on_folder_selected(path)
            elif os.path.isfile(path):
                parent_dir = os.path.dirname(path)
                app.on_folder_selected(parent_dir)
        event.acceptProposedAction()


class ImageResizerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.image_paths = []
        self.worker = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("图片尺寸缩放工具")
        self.resize(900, 700)
        self.setAcceptDrops(False)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # 标题
        title = QLabel("图片尺寸缩放工具")
        title.setFont(QFont("Arial", 54, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        # ---- 文件夹选择区 ----
        folder_group = QGroupBox("选择文件夹")
        folder_layout = QVBoxLayout(folder_group)
        folder_layout.setSpacing(8)

        self.drop_frame = DropLineEdit(self)
        drop_layout = QVBoxLayout(self.drop_frame)
        drop_layout.setSpacing(5)

        drop_hint = QLabel("将文件夹拖拽到此处")
        drop_hint.setAlignment(Qt.AlignCenter)
        drop_hint.setStyleSheet("font-size: 42px; color: #666;")
        drop_layout.addWidget(drop_hint)

        drop_sub = QLabel("或点击下方按钮选择文件夹")
        drop_sub.setAlignment(Qt.AlignCenter)
        drop_sub.setStyleSheet("font-size: 33px; color: #999;")
        drop_layout.addWidget(drop_sub)

        folder_layout.addWidget(self.drop_frame)

        self.folder_label = QLabel("未选择文件夹")
        self.folder_label.setStyleSheet("color: #666; font-size: 36px;")
        self.folder_label.setWordWrap(True)
        folder_layout.addWidget(self.folder_label)

        btn_row = QHBoxLayout()
        self.select_btn = QPushButton("选择文件夹")
        self.select_btn.setStyleSheet(self._btn_style("#2196F3"))
        self.select_btn.clicked.connect(self.browse_folder)
        btn_row.addWidget(self.select_btn)

        self.clear_btn = QPushButton("清空列表")
        self.clear_btn.setStyleSheet(self._btn_style("#9e9e9e"))
        self.clear_btn.clicked.connect(self.clear_list)
        btn_row.addWidget(self.clear_btn)

        folder_layout.addLayout(btn_row)
        main_layout.addWidget(folder_group)

        # ---- 设置区 ----
        setting_group = QGroupBox("设置")
        setting_layout = QHBoxLayout(setting_group)

        size_label = QLabel("目标大小:")
        setting_layout.addWidget(size_label)

        self.size_value = QDoubleSpinBox()
        self.size_value.setRange(0.1, 1000)
        self.size_value.setValue(8)
        self.size_value.setDecimals(1)
        self.size_value.setStyleSheet("font-size: 42px;")
        setting_layout.addWidget(self.size_value)

        self.size_unit = QComboBox()
        self.size_unit.addItems(["KB", "MB"])
        self.size_unit.setCurrentIndex(1)
        setting_layout.addWidget(self.size_unit)

        setting_layout.addSpacing(20)

        output_label = QLabel("输出目录:")
        setting_layout.addWidget(output_label)

        self.output_dir = QLineEdit()
        self.output_dir.setPlaceholderText("留空则覆盖原图")
        self.output_dir.setStyleSheet("font-size: 36px;")
        setting_layout.addWidget(self.output_dir)

        self.output_btn = QPushButton("选择")
        self.output_btn.setStyleSheet(self._btn_style("#607d8b", h=28))
        self.output_btn.clicked.connect(self.browse_output)
        setting_layout.addWidget(self.output_btn)

        main_layout.addWidget(setting_group)

        # ---- 操作按钮 ----
        action_layout = QHBoxLayout()
        self.start_btn = QPushButton("开始处理")
        self.start_btn.setStyleSheet(self._btn_style("#4CAF50", h=40))
        self.start_btn.setFont(QFont("Arial", 42, QFont.Bold))
        self.start_btn.clicked.connect(self.start_resize)
        action_layout.addWidget(self.start_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 5px;
                text-align: center;
                font-size: 36px;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 4px;
            }
        """)
        action_layout.addWidget(self.progress_bar)
        main_layout.addLayout(action_layout)

        # ---- 状态提示 ----
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #666; font-size: 36px;")
        main_layout.addWidget(self.status_label)

        # ---- 结果列表 ----
        result_group = QGroupBox("处理结果")
        result_layout = QVBoxLayout(result_group)

        self.result_list = QListWidget()
        self.result_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 5px;
                background-color: #fff;
                font-size: 36px;
            }
            QListWidget::item {
                padding: 4px 8px;
                border-bottom: 1px solid #f0f0f0;
            }
        """)
        result_layout.addWidget(self.result_list)
        main_layout.addWidget(result_group)

    def _btn_style(self, color, h=32):
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                padding: 5px 15px;
                font-size: 39px;
                font-weight: bold;
                border-radius: 5px;
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

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择图片文件夹")
        if folder:
            self.on_folder_selected(folder)

    def on_folder_selected(self, folder):
        folder = os.path.normpath(folder)
        self.folder_label.setText(folder)
        self.image_paths = []
        self.result_list.clear()

        for root, dirs, files in os.walk(folder):
            for f in files:
                if os.path.splitext(f)[1].lower() in IMAGE_EXTENSIONS:
                    self.image_paths.append(os.path.join(root, f))

        self.image_paths.sort()
        self.status_label.setText(f"找到 {len(self.image_paths)} 张图片")

        for p in self.image_paths:
            size = os.path.getsize(p)
            item_text = f"{os.path.basename(p)}  ({size / 1024:.1f} KB)"
            self.result_list.addItem(item_text)

    def browse_output(self):
        folder = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if folder:
            self.output_dir.setText(folder)

    def clear_list(self):
        self.image_paths = []
        self.result_list.clear()
        self.folder_label.setText("未选择文件夹")
        self.status_label.setText("已清空")

    def start_resize(self):
        if not self.image_paths:
            QMessageBox.warning(self, "提示", "请先选择包含图片的文件夹")
            return

        unit = self.size_unit.currentText()
        val = self.size_value.value()
        max_bytes = int(val * 1024 * 1024) if unit == "MB" else int(val * 1024)

        output_dir = self.output_dir.text().strip() or None

        self.start_btn.setEnabled(False)
        self.select_btn.setEnabled(False)
        self.result_list.clear()
        self.progress_bar.setValue(0)

        self.worker = ImageResizeWorker(
            self.image_paths, max_bytes, output_dir=output_dir
        )
        self.worker.progress.connect(self.on_progress)
        self.worker.one_result.connect(self.on_one_result)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def on_progress(self, current, total, msg):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.status_label.setText(msg)

    def on_one_result(self, filename, original, new):
        icon = ""
        if new == "已跳过（未超限）":
            icon = "⏭"
        elif original == "错误":
            icon = "✗"
        else:
            icon = "✓"
        self.result_list.addItem(f"{icon} {filename}  |  原始: {original}  →  处理后: {new}")

    def on_finished(self, success, failed, skipped):
        self.start_btn.setEnabled(True)
        self.select_btn.setEnabled(True)
        self.progress_bar.setValue(self.progress_bar.maximum())
        self.status_label.setText(f"完成！成功: {success}  跳过: {skipped}  失败: {failed}")


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = ImageResizerApp()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
