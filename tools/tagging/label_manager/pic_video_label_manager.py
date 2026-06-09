"""
视频图片标签管理器 - 主文件
支持图片和视频的预览、标签管理、删除等功能
"""
import os
import sys
import cv2
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QTextOption

# 导入功能模块
from ui_components import UIComponentsMixin
from media_handler import MediaHandlerMixin
from video_controller import VideoControllerMixin
from label_manager import LabelManagerMixin
class VideoLabelManager(QMainWindow, UIComponentsMixin, MediaHandlerMixin,
                        VideoControllerMixin, LabelManagerMixin):
    """视频图片标签管理器主类"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("视频图片标签管理器")
        self.setGeometry(100, 100, 1920, 1280)

        # 数据存储
        self.current_folder = ""
        self.media_files = []
        self.media_files_full_path = []
        self.current_index = 0

        # 视频播放相关
        self.video_capture = None
        self.playback_timer = QTimer()
        self.playback_timer.timeout.connect(self.update_frame)

        # 媒体类型标识
        self.current_media_type = None

        # 启用拖拽功能
        self.setAcceptDrops(True)

        # 双击删除相关变量
        self.last_delete_click_time = 0
        self.delete_click_count = 0

        # 标签编辑相关变量
        self.current_label_file = None
        self.label_modified = False

        # 视频进度相关变量
        self.total_frames = 0
        self.current_frame = 0
        self.fps = 0

        # 视频播放控制相关变量
        self.is_paused = False

        # 动画 WebP 支持相关变量
        self.animated_webp_images = []
        self.webp_timer = QTimer()
        self.webp_timer.timeout.connect(self.update_webp_frame)
        self.current_webp_index = 0
        self.is_animated_webp = False

        # 布局模式变量
        self.is_vertical_layout = False

        # 窗口大小变化检测
        self.resize_timer = QTimer()
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self.on_window_resized)

        self.init_ui()

    # ========== 拖拽事件 ==========

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if len(urls) == 1:
                local_path = urls[0].toLocalFile()
                if os.path.isdir(local_path):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if len(urls) == 1:
                folder_path = urls[0].toLocalFile()
                if os.path.isdir(folder_path):
                    self.current_folder = folder_path
                    self.load_files()
                    event.acceptProposedAction()
                    return
        event.ignore()

    def import_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "选择包含视频和标签的文件夹")
        if folder_path:
            self.current_folder = folder_path
            self.load_files()

    # ========== 键盘事件 ==========

    def keyPressEvent(self, event):
        """键盘按键按下事件"""
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            if self.delete_btn.isEnabled():
                self.delete_current_file()
        else:
            super().keyPressEvent(event)

    # ========== 窗口事件 ==========

    def resizeEvent(self, event):
        """窗口大小改变事件"""
        super().resizeEvent(event)
        self.resize_timer.start(300)

    def on_window_resized(self):
        """窗口大小改变后的处理"""
        if self.current_index >= 0 and self.current_index < len(self.media_files):
            current_media_path = self.media_files_full_path[self.current_index]
            ext = os.path.splitext(current_media_path)[1].lower()
            image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.gif', '.webp'}
            video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv'}

            width, height = 0, 0
            try:
                if ext in image_extensions:
                    img = cv2.imread(current_media_path)
                    if img is not None:
                        height, width, channels = img.shape
                    else:
                        from PIL import Image
                        pil_img = Image.open(current_media_path)
                        width, height = pil_img.size
                elif ext in video_extensions:
                    if self.video_capture and self.video_capture.isOpened():
                        width = int(self.video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
                        height = int(self.video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            except Exception as e:
                print(f"获取媒体尺寸时出错：{e}")

            if width > 0 and height > 0:
                self.check_and_update_layout(width, height)

    def closeEvent(self, event):
        """关闭窗口事件"""
        if self.label_modified:
            self.save_current_label()
        self.stop_video()
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = VideoLabelManager()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
