"""
媒体处理模块
处理媒体文件的加载、显示等功能
"""
import os
import cv2
import numpy as np
from PIL import Image
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QMessageBox

from utils import get_image_info, get_video_info


class MediaHandlerMixin:
    """媒体处理功能混入类"""

    def load_files(self):
        """加载媒体文件列表"""
        if not self.current_folder:
            return

        # 清空现有数据
        self.media_files = []
        self.media_files_full_path = []
        self.file_list.clear()
        self.stop_video()
        self.label_content.setText("标签内容将在此显示")
        self.current_index = -1
        self.delete_btn.setEnabled(False)

        # 支持的媒体格式
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv'}
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.gif', '.webp'}

        # 递归获取所有媒体文件
        for root, dirs, files in os.walk(self.current_folder):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in video_extensions or ext in image_extensions:
                    full_path = os.path.join(root, file)
                    relative_path = os.path.relpath(full_path, self.current_folder)
                    self.media_files.append(relative_path)
                    self.media_files_full_path.append(full_path)

        # 按名称排序
        combined = list(zip(self.media_files, self.media_files_full_path))
        combined.sort(key=lambda x: x[0])
        if combined:
            self.media_files, self.media_files_full_path = zip(*combined)
            self.media_files = list(self.media_files)
            self.media_files_full_path = list(self.media_files_full_path)

        for i, media_file in enumerate(self.media_files):
            display_name = os.path.splitext(media_file)[0]
            dir_name = os.path.dirname(media_file)
            if dir_name:
                display_name = f"[{dir_name}] {os.path.basename(display_name)}"

            file_ext = os.path.splitext(media_file)[1].lower()
            full_path = self.media_files_full_path[i]
            info_str = ""

            if file_ext in image_extensions:
                info_str = get_image_info(full_path)
                display_name = f" {display_name} [图片] - {info_str}"
            elif file_ext in video_extensions:
                info_str = get_video_info(full_path)
                display_name = f"{display_name} [视频] - {info_str}"
            else:
                display_name = f"{display_name} [未知类型]"

            self.file_list.addItem(display_name)

        # 如果有文件，默认选择第一个
        if self.media_files:
            self.file_list.setCurrentRow(0)

    def on_file_selected(self, index):
        """文件被选中时的处理"""
        # 在切换到新文件前，先保存当前标签内容
        if self.current_index >= 0 and self.label_modified:
            self.save_current_label()

        if index < 0 or index >= len(self.media_files):
            return

        self.current_index = index

        # 更新按钮状态
        self.update_navigation_buttons()

        video_file = self.media_files[index]
        base_name = os.path.splitext(video_file)[0]

        # 更新媒体预览
        self.update_media_preview(video_file)

        # 更新标签预览
        self.update_label_preview(base_name)

        # 启用删除按钮
        self.delete_btn.setEnabled(True)

        # 更新导航按钮状态
        self.update_navigation_buttons()

    def update_media_preview(self, media_file):
        """更新媒体预览"""
        if not self.current_folder:
            return

        media_path = self.media_files_full_path[self.current_index]
        ext = os.path.splitext(media_path)[1].lower()

        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.gif', '.webp'}
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv'}

        if ext in image_extensions:
            self.current_media_type = 'image'
            self.stop_video()
            self.display_image(media_path)
        elif ext in video_extensions:
            self.current_media_type = 'video'
            self.update_video_preview(media_file)
        else:
            self.current_media_type = None
            self.media_label.setText("不支持的文件类型")

    def display_image(self, image_path):
        """显示图片（包括静态和动画 WebP）"""
        # 检查是否为动画 WebP
        if os.path.splitext(image_path)[1].lower() == '.webp':
            try:
                pil_img = Image.open(image_path)
                if hasattr(pil_img, 'is_animated') and pil_img.is_animated:
                    self.play_animated_webp(image_path)
                    return
            except Exception as e:
                print(f"检查动画 WebP 失败：{e}")

        # 普通图片显示逻辑
        width, height = 0, 0
        try:
            img = cv2.imread(image_path)
            if img is not None:
                height, width, channels = img.shape
            else:
                pil_img = Image.open(image_path)
                width, height = pil_img.size
        except Exception as e:
            print(f"读取图片尺寸时出错：{e}")

        # 先检查并更新布局
        if width > 0 and height > 0:
            self.check_and_update_layout(width, height)

        # 使用 PIL 加载图片
        try:
            pil_img = Image.open(image_path)

            if pil_img.mode == 'RGBA':
                arr = np.array(pil_img.convert('RGB'))
                qt_image = QImage(arr.data, arr.shape[1], arr.shape[0],
                                  arr.shape[1] * 3, QImage.Format_RGB888)
            elif pil_img.mode == 'L':
                arr = np.array(pil_img.convert('RGB'))
                qt_image = QImage(arr.data, arr.shape[1], arr.shape[0],
                                  arr.shape[1] * 3, QImage.Format_RGB888)
            else:
                arr = np.array(pil_img.convert('RGB'))
                qt_image = QImage(arr.data, arr.shape[1], arr.shape[0],
                                  arr.shape[1] * 3, QImage.Format_RGB888)

            pixmap = QPixmap.fromImage(qt_image)

            if not pixmap.isNull():
                QTimer.singleShot(50, lambda p=pixmap: self._scale_and_display_image(p))
            else:
                self.media_label.setText("无法加载图片")
        except Exception as e:
            print(f"使用 PIL 加载图片失败：{e}")
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                QTimer.singleShot(50, lambda p=pixmap: self._scale_and_display_image(p))
            else:
                self.media_label.setText("无法加载图片")

    def _scale_and_display_image(self, pixmap):
        """缩放并显示图片"""
        if not pixmap.isNull() and hasattr(self, 'media_label'):
            scaled_pixmap = pixmap.scaled(
                self.media_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.media_label.setPixmap(scaled_pixmap)

    def delete_current_file(self):
        """删除当前选中的媒体文件及标签"""
        if self.current_index < 0 or self.current_index >= len(self.media_files):
            return

        import time
        current_time = time.time()

        # 检查是否在 1 秒内第二次点击
        if current_time - self.last_delete_click_time < 1.0:
            self.delete_click_count += 1
            self.stop_video()

            media_file = self.media_files[self.current_index]
            media_path = self.media_files_full_path[self.current_index]
            media_dir = os.path.dirname(media_path)
            base_name = os.path.splitext(os.path.basename(media_file))[0]

            # 删除媒体文件
            try:
                os.remove(media_path)
            except Exception as e:
                QMessageBox.warning(self, "删除失败", f"无法删除媒体文件：{str(e)}")
                return

            # 删除标签文件
            from utils import delete_label_file
            deleted_count, errors = delete_label_file(media_file, media_path)

            if errors:
                for error_msg in errors:
                    QMessageBox.warning(self, "删除警告", error_msg)

            # 从列表中移除已删除的文件
            del self.media_files[self.current_index]
            del self.media_files_full_path[self.current_index]

            # 更新文件列表 UI
            self.file_list.takeItem(self.current_index)

            # 调整当前索引
            if self.current_index >= len(self.media_files) and self.current_index > 0:
                self.current_index = self.current_index - 1

            # 如果还有文件，选择当前索引的文件，否则清空预览
            if len(self.media_files) > 0:
                self.file_list.setCurrentRow(self.current_index)
                self.on_file_selected(self.current_index)
            else:
                self.media_label.setText("媒体预览将在此显示")
                self.label_content.setText("标签内容将在此显示")
                self.delete_btn.setEnabled(False)
                self.update_navigation_buttons()

            # 点击一次左箭头按键
            self.select_prev_video()
            self.file_list.setFocus()

            # 重置计数器
            self.last_delete_click_time = 0
            self.delete_click_count = 0
        else:
            # 第一次点击，记录时间
            self.last_delete_click_time = current_time
            self.delete_click_count = 1

    def select_prev_video(self):
        """选择上一个媒体"""
        if self.current_index >= 0 and self.label_modified:
            if not self.save_current_label():
                return

        self.auto_create_label_if_needed()

        if self.current_index > 0:
            self.current_index -= 1
            self.file_list.setCurrentRow(self.current_index)

    def select_next_video(self):
        """选择下一个媒体"""
        if self.current_index >= 0 and self.label_modified:
            if not self.save_current_label():
                return

        self.auto_create_label_if_needed()

        if self.current_index < len(self.media_files) - 1:
            self.current_index += 1
            self.file_list.setCurrentRow(self.current_index)

    def update_navigation_buttons(self):
        """更新导航按钮状态"""
        has_media = len(self.media_files) > 0
        has_prev = self.current_index > 0 if has_media else False
        has_next = self.current_index < len(self.media_files) - 1 if has_media else False

        self.prev_btn.setEnabled(has_prev)
        self.next_btn.setEnabled(has_next)
