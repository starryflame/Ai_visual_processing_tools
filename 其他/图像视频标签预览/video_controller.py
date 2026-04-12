"""
视频播放控制模块
处理视频播放、暂停、进度控制等功能
"""
import cv2
import numpy as np
from PIL import Image
from PyQt5.QtCore import QTimer, QTime, Qt
from PyQt5.QtGui import QImage, QPixmap


class VideoControllerMixin:
    """视频播放控制功能混入类"""

    def update_video_preview(self, video_file):
        """更新视频预览"""
        if not self.current_folder:
            return

        video_path = self.media_files_full_path[self.current_index]

        # 停止当前播放
        self.stop_video()

        # 打开新的视频文件
        self.video_capture = cv2.VideoCapture(video_path)
        if not self.video_capture.isOpened():
            self.media_label.setFixedHeight(30)
            self.media_label.setText("无法打开视频文件")
            return

        # 获取视频信息
        self.total_frames = int(self.video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.video_capture.get(cv2.CAP_PROP_FPS)
        width = int(self.video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # 检查并更新布局
        self.check_and_update_layout(width, height)

        # 延迟执行，确保布局更新完成后再继续
        QTimer.singleShot(100, lambda: self._continue_video_setup())

    def _continue_video_setup(self):
        """继续视频设置过程"""
        if self.video_capture is None or not self.video_capture.isOpened():
            return

        if self.fps <= 0:
            self.fps = 30  # 默认帧率

        # 设置进度条范围
        self.progress_slider.setRange(0, self.total_frames)
        self.progress_slider.setValue(0)

        # 更新时间显示
        self.update_time_display()

        # 启用暂停按钮
        self.pause_btn.setEnabled(True)
        self.is_paused = False
        self.pause_btn.setText("⏸️")

        # 开始播放
        self.playback_timer.start(int(1000 / self.fps))

    def update_frame(self):
        """更新视频帧"""
        if self.video_capture is None:
            return

        ret, frame = self.video_capture.read()
        if ret:
            # 更新当前帧位置
            self.current_frame = int(self.video_capture.get(cv2.CAP_PROP_POS_FRAMES))

            # 更新进度条（如果用户没有正在拖动）
            if not hasattr(self, 'slider_pressed') or not self.slider_pressed:
                self.progress_slider.setValue(self.current_frame)
                self.update_time_display()

            # 转换颜色空间 (OpenCV 使用 BGR，Qt 使用 RGB)
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)

            # 缩放以适应标签大小
            scaled_pixmap = pixmap.scaled(
                self.media_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.media_label.setPixmap(scaled_pixmap)
        else:
            # 视频播放结束，重新开始
            self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self.current_frame = 0
            self.progress_slider.setValue(0)
            self.update_time_display()

    def stop_video(self):
        """停止视频播放"""
        # 停止视频播放
        self.playback_timer.stop()
        if self.video_capture is not None:
            self.video_capture.release()
            self.video_capture = None

        # 停止动画 WebP 播放
        self.stop_animated_webp()

        # 重置进度相关变量
        self.current_frame = 0
        self.total_frames = 0
        self.fps = 0
        self.progress_slider.setValue(0)
        self.current_time_label.setText("00:00")
        self.total_time_label.setText("00:00")
        # 禁用暂停按钮
        self.pause_btn.setEnabled(False)
        self.is_paused = False
        # 重置媒体标签为初始状态
        self.media_label.setText("媒体预览将在此显示")
        self.media_label.setPixmap(QPixmap())
        self.media_label.setStyleSheet("""
            QLabel {
                background-color: black;
                color: white;
                border-radius: 5px;
                font-size: 16px;
            }
        """)

    def update_time_display(self):
        """更新时间显示"""
        if self.fps > 0 and self.total_frames > 0:
            current_seconds = int(self.current_frame / self.fps)
            total_seconds = int(self.total_frames / self.fps)

            current_time = QTime(0, 0).addSecs(current_seconds).toString("mm:ss")
            total_time = QTime(0, 0).addSecs(total_seconds).toString("mm:ss")

            self.current_time_label.setText(current_time)
            self.total_time_label.setText(total_time)
        else:
            self.current_time_label.setText("00:00")
            self.total_time_label.setText("00:00")

    def on_slider_pressed(self):
        """进度条被按下"""
        self.slider_pressed = True

    def on_slider_released(self):
        """进度条释放"""
        self.slider_pressed = False
        # 跳转到指定位置
        target_frame = self.progress_slider.value()
        if self.video_capture is not None:
            self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
            self.current_frame = target_frame

    def on_slider_moved(self, value):
        """进度条移动时更新时间显示"""
        if self.fps > 0 and self.total_frames > 0:
            seconds = int(value / self.fps)
            time_str = QTime(0, 0).addSecs(seconds).toString("mm:ss")
            self.current_time_label.setText(time_str)

    def toggle_pause(self):
        """切换视频/动画 WebP 播放/暂停状态"""
        # 检查是否为动画 WebP
        if self.is_animated_webp:
            if self.is_paused:
                self.webp_timer.start(int(1000 / (self.total_frames / max(self.fps, 1))))
                self.is_paused = False
                self.pause_btn.setText("⏸️")
            else:
                self.webp_timer.stop()
                self.is_paused = True
                self.pause_btn.setText("▶️")
            return

        # 普通视频播放控制
        if self.video_capture is None:
            return

        if self.is_paused:
            self.playback_timer.start(int(1000 / self.fps))
            self.is_paused = False
            self.pause_btn.setText("⏸️")
        else:
            self.playback_timer.stop()
            self.is_paused = True
            self.pause_btn.setText("▶️")

    # ========== 动画 WebP 相关方法 ==========

    def is_animated_webp(self, image_path):
        """检查是否为动画 WebP"""
        try:
            img = Image.open(image_path)

            if hasattr(img, 'is_animated'):
                return img.is_animated

            frame_count = 0
            try:
                while True:
                    img.seek(frame_count)
                    frame_count += 1
                    if frame_count > 100:
                        break
            except EOFError:
                pass

            return frame_count > 1
        except Exception as e:
            print(f"检查动画 WebP 失败：{e}")
            return False

    def play_animated_webp(self, image_path):
        """播放动画 WebP"""
        try:
            self.animated_webp_images = []
            pil_img = Image.open(image_path)

            # 获取第一帧的尺寸信息用于布局判断
            width, height = pil_img.size

            # 先检查并更新布局
            if width > 0 and height > 0:
                self.check_and_update_layout(width, height)

            # 读取所有帧
            frame_count = 0
            total_duration = 0

            while True:
                try:
                    duration = pil_img.info.get('duration', 100)
                    total_duration += duration

                    # 将 PIL 图像转换为 QImage
                    arr = np.array(pil_img.convert('RGB'))
                    qt_image = QImage(arr.data, arr.shape[1], arr.shape[0],
                                      arr.shape[1] * 3, QImage.Format_RGB888)

                    pixmap = QPixmap.fromImage(qt_image)
                    self.animated_webp_images.append(pixmap)

                except (EOFError, IndexError):
                    break

                frame_count += 1

                try:
                    pil_img.seek(frame_count)
                except (EOFError, IndexError):
                    break

            if not self.animated_webp_images:
                self.media_label.setText("无法加载动画 WebP")
                return

            # 设置动画 WebP 相关变量
            self.is_animated_webp = True
            self.total_frames = len(self.animated_webp_images)
            self.current_frame = 0

            # 计算平均帧率
            if total_duration > 0:
                avg_fps = len(self.animated_webp_images) * 1000 / total_duration
                display_fps = int(avg_fps)
            else:
                display_fps = 10

            # 显示第一帧
            self._scale_and_display_image(self.animated_webp_images[0])

            # 设置进度条
            self.progress_slider.setRange(0, self.total_frames - 1)
            self.progress_slider.setValue(0)

            # 更新时间显示
            total_seconds = total_duration / 1000.0
            current_time_str = QTime(0, 0).addSecs(0).toString("mm:ss")
            total_time_str = QTime(0, 0).addSecs(int(total_seconds)).toString("mm:ss")
            self.current_time_label.setText(current_time_str)
            self.total_time_label.setText(total_time_str)

            # 启动定时器播放动画
            self.webp_timer.start(int(1000 / display_fps))
            self.pause_btn.setEnabled(True)
            self.is_paused = False

            print(f"动画 WebP: {len(self.animated_webp_images)} 帧，平均{display_fps}fps")

        except Exception as e:
            print(f"播放动画 WebP 失败：{e}")
            # 回退到显示第一帧静态图像
            pil_img = Image.open(image_path)
            arr = np.array(pil_img.convert('RGB'))
            qt_image = QImage(arr.data, arr.shape[1], arr.shape[0],
                              arr.shape[1] * 3, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)
            QTimer.singleShot(50, lambda p=pixmap: self._scale_and_display_image(p))

    def update_webp_frame(self):
        """更新动画 WebP 帧"""
        if not self.is_animated_webp or not self.animated_webp_images:
            return

        if self.is_paused:
            return

        # 显示下一帧
        self.current_frame = (self.current_frame + 1) % len(self.animated_webp_images)
        pixmap = self.animated_webp_images[self.current_frame]

        # 缩放并显示
        scaled_pixmap = pixmap.scaled(
            self.media_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.media_label.setPixmap(scaled_pixmap)

        # 更新进度条
        if not hasattr(self, 'slider_pressed') or not self.slider_pressed:
            self.progress_slider.setValue(self.current_frame)

        # 更新时间显示
        total_seconds = int(self.total_frames / (self.fps if self.fps > 0 else 10))
        current_time_str = QTime(0, 0).addSecs(int(self.current_frame * total_seconds / max(len(self.animated_webp_images), 1))).toString("mm:ss")
        self.current_time_label.setText(current_time_str)

    def stop_animated_webp(self):
        """停止动画 WebP 播放"""
        self.webp_timer.stop()
        self.is_animated_webp = False
        self.animated_webp_images = []
        self.current_frame = 0
        self.pause_btn.setEnabled(False)
        self.is_paused = False
