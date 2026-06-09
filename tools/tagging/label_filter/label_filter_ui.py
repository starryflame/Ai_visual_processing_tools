import os
import sys
import shutil
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QListWidget, QListWidgetItem, QLabel, 
                             QPushButton, QFileDialog, QSplitter, QAbstractItemView,
                             QAction, QMenu, QSlider, QFrame)
from PyQt5.QtGui import QPixmap, QIcon, QImage
from PyQt5.QtCore import Qt, QSize, QThread, pyqtSignal, QMutex, QMutexLocker, QTimer, QTime
import threading
from functools import lru_cache
import time
import cv2  # 添加：用于视频处理


class ThumbnailGenerator(QThread):
    thumbnail_ready = pyqtSignal(str, object)  # 发送文件路径和缩略图 pixmap

    def __init__(self, folder_path, image_files, icon_size=QSize(200, 200)):
        super().__init__()
        self.folder_path = folder_path
        self.image_files = image_files
        self.icon_size = icon_size
        self._is_running = True
        self.mutex = QMutex()

    def run(self):
        for img_file in self.image_files:
            if not self._is_running:
                break
            img_path = os.path.join(self.folder_path, img_file)
            ext = os.path.splitext(img_file)[1].lower()
            
            # 视频文件生成封面缩略图
            if ext in {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv'}:
                try:
                    cap = cv2.VideoCapture(img_path)
                    if cap.isOpened():
                        # 读取第一帧作为封面
                        ret, frame = cap.read()
                        if ret:
                            # 转换颜色空间 (OpenCV 使用 BGR，Qt 使用 RGB)
                            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                            h, w, ch = rgb_image.shape
                            bytes_per_line = ch * w
                            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
                            thumbnail = QPixmap.fromImage(qt_image).scaled(
                                self.icon_size.width(), 
                                self.icon_size.height(), 
                                Qt.KeepAspectRatio, 
                                Qt.SmoothTransformation
                            )
                            self.thumbnail_ready.emit(img_file, thumbnail)
                        cap.release()
                except Exception as e:
                    print(f"生成视频封面失败：{e}")
            else:
                # 图片文件正常处理
                pixmap = QPixmap(img_path)
                if not pixmap.isNull():
                    thumbnail = pixmap.scaled(
                        self.icon_size.width(), 
                        self.icon_size.height(), 
                        Qt.KeepAspectRatio, 
                        Qt.SmoothTransformation
                    )
                    self.thumbnail_ready.emit(img_file, thumbnail)

    def stop(self):
        with QMutexLocker(self.mutex):
            self._is_running = False


class ImageViewer(QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle("图片视频手动过滤工具")  # 修改：标题更新
        self.setGeometry(100, 100, 2160, 1280)
        
        # 设置接受拖放
        self.setAcceptDrops(True)
        
        # 初始化变量
        self.source_folder = ""
        self.dest_folder = ""
        self.current_image_index = 0
        self.image_files = []
        self.current_image = None
        
        # 缩略图缓存
        self.thumbnail_cache = {}
        
        # 视频播放相关
        self.video_capture = None
        self.playback_timer = QTimer()
        self.playback_timer.timeout.connect(self.update_frame)
        self.current_media_type = None  # 'video', 'image', or None
        self.total_frames = 0
        self.current_frame = 0
        self.fps = 0
        self.is_paused = False
        
        # 创建主窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # 左侧面板 - 源文件夹和缩略图
        self.left_panel = QWidget()
        self.left_panel.setAcceptDrops(True)
        left_layout = QVBoxLayout(self.left_panel)
        
        # 源文件夹选择
        source_label = QLabel("源文件夹:")
        self.source_folder_label = QLabel("未选择")
        self.select_source_btn = QPushButton("选择源文件夹")
        self.select_source_btn.setFixedHeight(100)
        self.select_source_btn.clicked.connect(self.select_source_folder)
        
        left_layout.addWidget(source_label)
        left_layout.addWidget(self.source_folder_label)
        left_layout.addWidget(self.select_source_btn)
        
        # 缩略图列表
        self.thumbnail_list = QListWidget()
        self.thumbnail_list.setViewMode(QListWidget.IconMode)
        self.thumbnail_list.setIconSize(QSize(200, 200))
        self.thumbnail_list.setResizeMode(QListWidget.Adjust)
        self.thumbnail_list.setMovement(QListWidget.Static)
        self.thumbnail_list.setDragDropMode(QListWidget.NoDragDrop)
        self.thumbnail_list.setSelectionMode(QListWidget.SingleSelection)
        self.thumbnail_list.currentItemChanged.connect(self.on_thumbnail_selected)
        
        left_layout.addWidget(self.thumbnail_list)
        
        # 添加源文件夹统计标签
        self.source_stats_label = QLabel()
        self.source_stats_label.setAlignment(Qt.AlignCenter)
        self.source_stats_label.setStyleSheet("color: #cccccc; font-size: 12px;")
        left_layout.addWidget(self.source_stats_label)
        
        # 更新源文件夹统计
        self.update_source_stats()
        
        # 中间面板 - 大图预览和控制按钮
        middle_panel = QWidget()
        middle_layout = QVBoxLayout(middle_panel)
        
        # 大图预览
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(400, 400)
        self.preview_label.setStyleSheet("border: 1px solid gray; background-color: black;")
        
        middle_layout.addWidget(self.preview_label, 1)  # 修改：设置 stretch 因子为 1，让预览区域占据更多空间
        
        # 添加视频进度控制区域
        self.video_control_frame = QFrame()
        self.video_control_frame.setFrameStyle(QFrame.StyledPanel)
        self.video_control_frame.setMaximumHeight(60)  # 添加：限制控制框最大高度
        video_control_layout = QHBoxLayout(self.video_control_frame)
        video_control_layout.setContentsMargins(5, 5, 5, 5)
        video_control_layout.setSpacing(10)
        
        # 播放/暂停按钮
        self.pause_btn = QPushButton("⏸️")
        self.pause_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                padding: 5px;
                font-size: 16px;
                border-radius: 5px;
                min-width: 40px;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.pause_btn.clicked.connect(self.toggle_pause)
        self.pause_btn.setEnabled(False)
        video_control_layout.addWidget(self.pause_btn)
        
        # 当前时间标签
        self.current_time_label = QLabel("00:00")
        self.current_time_label.setStyleSheet("color: white; font-size: 12px;")
        video_control_layout.addWidget(self.current_time_label)
        
        # 进度滑块
        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #999999;
                height: 8px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #B1B1B1, stop:1 #c4c4c4);
                margin: 2px 0;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #b4b4b4, stop:1 #8f8f8f);
                border: 1px solid #5c5c5c;
                width: 18px;
                margin: -2px 0;
                border-radius: 3px;
            }
        """)
        self.progress_slider.sliderPressed.connect(self.on_slider_pressed)
        self.progress_slider.sliderReleased.connect(self.on_slider_released)
        self.progress_slider.sliderMoved.connect(self.on_slider_moved)
        self.progress_slider.setEnabled(False)
        video_control_layout.addWidget(self.progress_slider)
        
        # 总时长标签
        self.total_time_label = QLabel("00:00")
        self.total_time_label.setStyleSheet("color: white; font-size: 12px;")
        video_control_layout.addWidget(self.total_time_label)
        
        middle_layout.addWidget(self.video_control_frame, 0)  # 修改：设置 stretch 因子为 0，控制框保持紧凑
        
        # 控制按钮
        controls_layout = QHBoxLayout()
        self.prev_btn = QPushButton("上一张")
        self.copy_btn = QPushButton("复制到目标文件夹")
        self.delete_btn = QPushButton("删除当前媒体")  # 修改：支持视频删除
        self.next_btn = QPushButton("下一张")
        
        # 设置按钮高度更高
        button_height = 200
        self.prev_btn.setFixedHeight(button_height)
        self.copy_btn.setFixedHeight(button_height)
        self.delete_btn.setFixedHeight(button_height)
        self.next_btn.setFixedHeight(button_height)
        
        self.prev_btn.clicked.connect(self.show_prev_image)
        self.next_btn.clicked.connect(self.show_next_image)
        self.copy_btn.clicked.connect(self.copy_current_image)
        self.delete_btn.clicked.connect(self.delete_current_image)

        controls_layout.addWidget(self.copy_btn)
        controls_layout.addWidget(self.prev_btn)
        controls_layout.addWidget(self.next_btn)
        controls_layout.addWidget(self.delete_btn)

        middle_layout.addLayout(controls_layout)
        
        # 右侧面板 - 目标文件夹和预览
        self.right_panel = QWidget()
        self.right_panel.setAcceptDrops(True)
        right_layout = QVBoxLayout(self.right_panel)
        
        # 目标文件夹选择
        dest_label = QLabel("目标文件夹:")
        self.dest_folder_label = QLabel("未选择")
        self.select_dest_btn = QPushButton("选择目标文件夹")
        self.select_dest_btn.setFixedHeight(100)
        self.select_dest_btn.clicked.connect(self.select_dest_folder)
        
        right_layout.addWidget(dest_label)
        right_layout.addWidget(self.dest_folder_label)
        right_layout.addWidget(self.select_dest_btn)
        
        # 目标文件夹内容预览
        self.dest_preview_list = QListWidget()
        self.dest_preview_list.setViewMode(QListWidget.IconMode)
        self.dest_preview_list.setIconSize(QSize(160, 160))
        self.dest_preview_list.setResizeMode(QListWidget.Adjust)
        self.dest_preview_list.setDragDropMode(QListWidget.NoDragDrop)
        self.dest_preview_list.currentItemChanged.connect(self.on_dest_thumbnail_selected)
        
        right_layout.addWidget(self.dest_preview_list)
        
        # 添加目标文件夹统计标签
        self.dest_stats_label = QLabel()
        self.dest_stats_label.setAlignment(Qt.AlignCenter)
        self.dest_stats_label.setStyleSheet("color: #cccccc; font-size: 12px;")
        right_layout.addWidget(self.dest_stats_label)
        
        # 更新目标文件夹统计
        self.update_dest_stats()
        
        # 添加面板到分割器
        splitter.addWidget(self.left_panel)
        splitter.addWidget(middle_panel)
        splitter.addWidget(self.right_panel)
        
        # 设置分割器比例
        splitter.setSizes([300, 800, 300])
        
        # 应用默认主题
        self.apply_theme()
        
        # 缩略图生成线程
        self.thumbnail_thread = None

        # 添加双击删除相关变量
        self.last_delete_time = 0
        self.delete_threshold = 1.0


    def apply_theme(self):
        """应用深色主题"""
        dark_theme = """
        QMainWindow {
            background-color: #2b2b2b;
            color: white;
        }
        QWidget {
            background-color: #2b2b2b;
            color: white;
        }
        QLabel {
            background-color: #2b2b2b;
            color: white;
        }
        QPushButton {
            background-color: #3c3c3c;
            color: white;
            border: 1px solid #5c5c5c;
            padding: 5px;
            border-radius: 3px;
        }
        QPushButton:hover {
            background-color: #4c4c4c;
        }
        QPushButton:pressed {
            background-color: #5c5c5c;
        }
        QListWidget {
            background-color: #1e1e1e;
            color: white;
            border: 1px solid #5c5c5c;
        }
        QListWidget::item:selected {
            background-color: #3a3a3a;
            color: white;
        }
        QScrollBar:vertical {
            background: #2b2b2b;
            width: 15px;
            border-radius: 4px;
        }
        QScrollBar::handle:vertical {
            background: #4c4c4c;
            border-radius: 4px;
            min-height: 20px;
        }
        QScrollBar::handle:vertical:hover {
            background: #5c5c5c;
        }
        """
        self.setStyleSheet(dark_theme)

    def dragEnterEvent(self, event):
        """接受拖拽事件"""
        if event.mimeData().hasUrls():
            # 检查是否为文件夹
            for url in event.mimeData().urls():
                if url.isLocalFile() and os.path.isdir(url.toLocalFile()):
                    event.acceptProposedAction()
                    return
        event.ignore()
    
    def dropEvent(self, event):
        """处理文件夹拖拽放置"""
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    folder_path = url.toLocalFile()
                    if os.path.isdir(folder_path):
                        # 根据鼠标位置判断拖拽到哪个面板
                        pos = event.pos()
                        widget = self.childAt(pos)
                        
                        # 获取鼠标位置对应的全局坐标
                        global_pos = self.mapToGlobal(pos)
                        left_panel_global = self.left_panel.mapToGlobal(self.left_panel.rect().topLeft())
                        right_panel_global = self.right_panel.mapToGlobal(self.right_panel.rect().topLeft())
                        
                        # 判断拖拽到左侧还是右侧
                        if global_pos.x() < left_panel_global.x() + self.left_panel.width():
                            # 拖拽到左侧，设置为源文件夹
                            self.source_folder = folder_path
                            self.source_folder_label.setText(folder_path)
                            self.load_images_from_folder(folder_path)
                        elif global_pos.x() > right_panel_global.x():
                            # 拖拽到右侧，设置为目标文件夹
                            self.dest_folder = folder_path
                            self.dest_folder_label.setText(folder_path)
                            self.load_dest_preview()
                        else:
                            # 拖拽到中间区域，根据更靠近哪侧来判断
                            middle_x = left_panel_global.x() + self.left_panel.width()
                            if global_pos.x() < middle_x + (right_panel_global.x() - middle_x) / 2:
                                self.source_folder = folder_path
                                self.source_folder_label.setText(folder_path)
                                self.load_images_from_folder(folder_path)
                            else:
                                self.dest_folder = folder_path
                                self.dest_folder_label.setText(folder_path)
                                self.load_dest_preview()
                        return
        event.ignore()

    def select_source_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择源图片/视频文件夹")  # 修改：支持视频
        if folder:
            self.source_folder = folder
            self.source_folder_label.setText(folder)
            self.load_images_from_folder(folder)
    
    def select_dest_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择目标文件夹")
        if folder:
            self.dest_folder = folder
            self.dest_folder_label.setText(folder)
            self.load_dest_preview()
    
    def load_images_from_folder(self, folder):
        # 修改：停止当前视频播放
        self.stop_video()
        
        self.thumbnail_list.clear()
        self.image_files = []
        
        # 修改：支持的图片和视频格式
        img_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp']
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv']
        
        for file in os.listdir(folder):
            ext = file.lower()
            if any(ext.endswith(e) for e in img_extensions) or any(ext.endswith(e) for e in video_extensions):
                self.image_files.append(file)
        
        # 如果有文件，启动缩略图生成线程
        if self.image_files:
            # 停止之前的线程
            if self.thumbnail_thread and self.thumbnail_thread.isRunning():
                self.thumbnail_thread.stop()
                self.thumbnail_thread.wait()
            
            # 启动新线程生成缩略图
            self.thumbnail_thread = ThumbnailGenerator(folder, self.image_files)
            self.thumbnail_thread.thumbnail_ready.connect(self.add_thumbnail_to_list)
            self.thumbnail_thread.start()
        
        # 选中第一张图片/视频
        if self.image_files:
            self.current_image_index = 0
            self.thumbnail_list.setCurrentRow(0)
            self.show_current_image()
        
        # 更新源文件夹统计
        self.update_source_stats()


    def add_thumbnail_to_list(self, img_file, thumbnail):
        """将生成的缩略图添加到列表中"""
        if thumbnail:
            icon = QIcon(thumbnail)
            # 添加文件类型标识
            ext = os.path.splitext(img_file)[1].lower()
            video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv'}
            type_label = "[视频]" if ext in video_extensions else "[图片]"
            item = QListWidgetItem(icon, f"{type_label} {img_file}")
            item.setSizeHint(QSize(240, 240))
            self.thumbnail_list.addItem(item)
    

    def load_dest_preview(self):
        if not self.dest_folder or not os.path.exists(self.dest_folder):
            return
            
        self.dest_preview_list.clear()
        
        # 修改：支持的图片和视频格式
        img_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp']
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv']
        
        files_in_dest = []
        for file in os.listdir(self.dest_folder):
            ext = file.lower()
            if any(ext.endswith(e) for e in img_extensions) or any(ext.endswith(e) for e in video_extensions):
                files_in_dest.append(file)
                file_path = os.path.join(self.dest_folder, file)
                
                # 生成缩略图（图片或视频封面）
                if any(ext.endswith(e) for e in video_extensions):
                    try:
                        cap = cv2.VideoCapture(file_path)
                        if cap.isOpened():
                            ret, frame = cap.read()
                            if ret:
                                rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                                h, w, ch = rgb_image.shape
                                bytes_per_line = ch * w
                                qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
                                thumbnail = QPixmap.fromImage(qt_image).scaled(160, 160, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                                icon = QIcon(thumbnail)
                                item = QListWidgetItem(icon, f"[视频] {file}")
                                item.setSizeHint(QSize(200, 200))
                                self.dest_preview_list.addItem(item)
                            cap.release()
                    except Exception as e:
                        print(f"生成视频封面失败：{e}")
                else:
                    pixmap = QPixmap(file_path)
                    if not pixmap.isNull():
                        thumbnail = pixmap.scaled(160, 160, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        icon = QIcon(thumbnail)
                        item = QListWidgetItem(icon, f"[图片] {file}")
                        item.setSizeHint(QSize(200, 200))
                        self.dest_preview_list.addItem(item)
        
        # 更新目标文件夹统计
        self.update_dest_stats()
    

    def on_thumbnail_selected(self, current, previous):
        if current:
            row = self.thumbnail_list.row(current)
            if 0 <= row < len(self.image_files):
                self.current_image_index = row
                self.show_current_image()
                self.thumbnail_list.setFocus()
    
    def show_prev_image(self):
        """选择上一个媒体文件"""
        # 保存当前状态并停止视频
        self.stop_video()
        
        if self.image_files and self.current_image_index > 0:
            self.current_image_index -= 1
            self.thumbnail_list.setCurrentRow(self.current_image_index)
            self.show_current_image()
    
    def show_next_image(self):
        """选择下一个媒体文件"""
        # 保存当前状态并停止视频
        self.stop_video()
        
        if self.image_files and self.current_image_index < len(self.image_files) - 1:
            self.current_image_index += 1
            self.thumbnail_list.setCurrentRow(self.current_image_index)
            self.show_current_image()
    
    def show_current_image(self):
        # 修改：停止之前的视频播放
        self.stop_video()
        
        if not self.image_files or self.current_image_index >= len(self.image_files):
            return
            
        img_file = self.image_files[self.current_image_index]
        img_path = os.path.join(self.source_folder, img_file)
        ext = os.path.splitext(img_file)[1].lower()
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv'}
        
        if ext in video_extensions:
            # 处理视频文件
            self.current_media_type = 'video'
            self.play_video(img_path)
        else:
            # 处理图片文件
            self.current_media_type = 'image'
            pixmap = QPixmap(img_path)
            if not pixmap.isNull():
                preview_size = self.preview_label.size()
                scaled_pixmap = pixmap.scaled(
                    preview_size.width() - 10, 
                    preview_size.height() - 10, 
                    Qt.KeepAspectRatio, 
                    Qt.SmoothTransformation
                )
                self.preview_label.setPixmap(scaled_pixmap)
                self.current_image = img_path
        
        # 更新视频控制按钮状态
        self.pause_btn.setEnabled(self.current_media_type == 'video')
        self.progress_slider.setEnabled(self.current_media_type == 'video')
    
    def play_video(self, video_path):
        """播放视频"""
        self.video_capture = cv2.VideoCapture(video_path)
        if not self.video_capture.isOpened():
            self.preview_label.setText("无法打开视频文件")
            return
        
        # 获取视频信息
        self.total_frames = int(self.video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.video_capture.get(cv2.CAP_PROP_FPS)
        
        if self.fps <= 0:
            self.fps = 30
        
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
            self.current_frame = int(self.video_capture.get(cv2.CAP_PROP_POS_FRAMES))
            
            if not hasattr(self, 'slider_pressed') or not self.slider_pressed:
                self.progress_slider.setValue(self.current_frame)
                self.update_time_display()
            
            # 转换颜色空间
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)
            
            # 缩放以适应标签大小
            preview_size = self.preview_label.size()
            scaled_pixmap = pixmap.scaled(
                preview_size.width() - 10,
                preview_size.height() - 10,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.preview_label.setPixmap(scaled_pixmap)
        else:
            # 视频播放结束，重新开始
            self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self.current_frame = 0
            self.progress_slider.setValue(0)
            self.update_time_display()
    
    def stop_video(self):
        """停止视频播放"""
        self.playback_timer.stop()
        if self.video_capture is not None:
            self.video_capture.release()
            self.video_capture = None
        self.current_frame = 0
        self.total_frames = 0
        self.fps = 0
        self.progress_slider.setValue(0)
        self.current_time_label.setText("00:00")
        self.total_time_label.setText("00:00")
        self.pause_btn.setEnabled(False)
        self.is_paused = False
    
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
        """切换视频播放/暂停状态"""
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
    

    def copy_current_image(self):
        if not self.image_files or not self.dest_folder:
            return
            
        if self.current_image_index >= len(self.image_files):
            return
            
        img_file = self.image_files[self.current_image_index]
        src_path = os.path.join(self.source_folder, img_file)
        
        # 检测目标文件夹中是否已存在同名文件
        dest_path = self.get_unique_dest_path(img_file)
        
        # 复制文件
        try:
            shutil.copy2(src_path, dest_path)
            print(f"已复制：{src_path} -> {dest_path}")
            
            # 检查并复制同名的 txt 文件
            base_name, ext = os.path.splitext(img_file)
            txt_src_path = os.path.join(self.source_folder, f"{base_name}.txt")
            if os.path.exists(txt_src_path):
                txt_dest_path = os.path.join(self.dest_folder, f"{base_name}.txt")
                shutil.copy2(txt_src_path, txt_dest_path)
                print(f"已复制关联 txt 文件：{txt_src_path} -> {txt_dest_path}")
            
            # 添加新复制的文件到右侧预览列表
            ext = os.path.splitext(img_file)[1].lower()
            video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv'}
            
            if ext in video_extensions:
                # 视频文件生成封面
                try:
                    cap = cv2.VideoCapture(dest_path)
                    if cap.isOpened():
                        ret, frame = cap.read()
                        if ret:
                            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                            h, w, ch = rgb_image.shape
                            bytes_per_line = ch * w
                            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
                            thumbnail = QPixmap.fromImage(qt_image).scaled(160, 160, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                            icon = QIcon(thumbnail)
                            item = QListWidgetItem(icon, f"[视频] {os.path.basename(dest_path)}")
                            item.setSizeHint(QSize(200, 200))
                            self.dest_preview_list.addItem(item)
                        cap.release()
                except Exception as e:
                    print(f"生成视频封面失败：{e}")
            else:
                # 图片文件
                pixmap = QPixmap(dest_path)
                if not pixmap.isNull():
                    thumbnail = pixmap.scaled(160, 160, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    icon = QIcon(thumbnail)
                    item = QListWidgetItem(icon, f"[图片] {os.path.basename(dest_path)}")
                    item.setSizeHint(QSize(200, 200))
                    self.dest_preview_list.addItem(item)
        except Exception as e:
            print(f"复制失败：{e}")
        
        # 更新统计信息
        self.update_source_stats()
        self.update_dest_stats()
    

    def delete_current_image(self):
        """删除当前预览的媒体文件（图片或视频）"""
        current_time = time.time()
        
        if current_time - self.last_delete_time < self.delete_threshold:
            self.perform_delete()
            self.last_delete_time = 0
        else:
            self.last_delete_time = current_time
            from PyQt5.QtCore import QTimer
            timer = QTimer(self)
            timer.timeout.connect(lambda: setattr(self, 'last_delete_time', 
                                                0 if time.time() - self.last_delete_time >= self.delete_threshold else self.last_delete_time))
            timer.setSingleShot(True)
            timer.start(int(self.delete_threshold * 1000))

    def perform_delete(self):
        """执行实际的删除操作"""
        # 停止视频播放
        self.stop_video()
        
        if self.current_image and os.path.exists(self.current_image):
            if self.current_image.startswith(self.source_folder):
                img_file = os.path.basename(self.current_image)
                
                try:
                    os.remove(self.current_image)
                    print(f"已删除：{self.current_image}")
                    
                    try:
                        img_index = self.image_files.index(img_file)
                        del self.image_files[img_index]
                        
                        current_item = self.thumbnail_list.currentItem()
                        if current_item:
                            current_row = self.thumbnail_list.row(current_item)
                            self.thumbnail_list.takeItem(current_row)
                        
                        if img_index < self.current_image_index:
                            self.current_image_index -= 1
                        elif img_index == self.current_image_index:
                            if img_index >= len(self.image_files):
                                self.current_image_index = max(0, len(self.image_files) - 1)
                            
                        if self.image_files and 0 <= self.current_image_index < len(self.image_files):
                            if self.thumbnail_list.count() > self.current_image_index:
                                self.thumbnail_list.setCurrentRow(self.current_image_index)
                            self.show_current_image()
                        else:
                            self.preview_label.clear()
                            self.current_image = None
                            
                    except ValueError:
                        self.load_images_from_folder(self.source_folder)
                        
                except Exception as e:
                    print(f"删除失败：{e}")
                
                self.update_source_stats()
            elif self.dest_folder and self.current_image.startswith(self.dest_folder):
                img_file = os.path.basename(self.current_image)
                
                try:
                    os.remove(self.current_image)
                    print(f"已删除：{self.current_image}")
                    
                    current_item = self.dest_preview_list.currentItem()
                    if current_item:
                        row = self.dest_preview_list.row(current_item)
                        self.dest_preview_list.takeItem(row)
                    
                    self.preview_label.clear()
                    self.current_image = None
                    
                    self.update_dest_stats()
                    
                except Exception as e:
                    print(f"删除失败：{e}")
                
                self.update_dest_stats()
        else:
            focused_widget = QApplication.focusWidget()
            
            if focused_widget == self.dest_preview_list and self.dest_folder:
                current_item = self.dest_preview_list.currentItem()
                if not current_item:
                    return
                    
                img_file = current_item.text()
                # 移除类型标识
                if img_file.startswith("[视频] ") or img_file.startswith("[图片] "):
                    img_file = img_file.split(" ", 1)[1]
                img_path = os.path.join(self.dest_folder, img_file)
                
                try:
                    os.remove(img_path)
                    print(f"已删除：{img_path}")
                    
                    row = self.dest_preview_list.row(current_item)
                    self.dest_preview_list.takeItem(row)
                    
                    self.preview_label.clear()
                    self.current_image = None
                    
                    self.update_dest_stats()
                        
                except Exception as e:
                    print(f"删除失败：{e}")
                
                self.update_dest_stats()
            elif focused_widget == self.thumbnail_list and self.source_folder:
                current_item = self.thumbnail_list.currentItem()
                if not current_item:
                    return
                    
                img_file = current_item.text()
                # 移除类型标识
                if img_file.startswith("[视频] ") or img_file.startswith("[图片] "):
                    img_file = img_file.split(" ", 1)[1]
                
                try:
                    img_index = self.image_files.index(img_file)
                except ValueError:
                    return
                    
                img_path = os.path.join(self.source_folder, img_file)
                
                try:
                    os.remove(img_path)
                    print(f"已删除：{img_path}")
                    
                    del self.image_files[img_index]
                    
                    self.thumbnail_list.takeItem(self.thumbnail_list.row(current_item))
                    
                    if img_index < self.current_image_index:
                        self.current_image_index -= 1
                    elif img_index == self.current_image_index:
                        if img_index >= len(self.image_files):
                            self.current_image_index = max(0, len(self.image_files) - 1)
                        
                    if self.image_files and 0 <= self.current_image_index < len(self.image_files):
                        if self.thumbnail_list.count() > self.current_image_index:
                            self.thumbnail_list.setCurrentRow(self.current_image_index)
                        self.show_current_image()
                    else:
                        self.preview_label.clear()
                        self.current_image = None
                        
                except Exception as e:
                    print(f"删除失败：{e}")
                
                self.update_source_stats()
            elif self.image_files and 0 <= self.current_image_index < len(self.image_files):
                img_file = self.image_files[self.current_image_index]
                img_path = os.path.join(self.source_folder, img_file)
                
                try:
                    os.remove(img_path)
                    print(f"已删除：{img_path}")
                    
                    del self.image_files[self.current_image_index]
                    
                    current_row = self.thumbnail_list.currentRow()
                    if current_row != -1:
                        self.thumbnail_list.takeItem(current_row)
                    
                    if self.current_image_index >= len(self.image_files) and self.current_image_index > 0:
                        self.current_image_index = len(self.image_files) - 1
                    
                    if self.image_files and 0 <= self.current_image_index < len(self.image_files):
                        if self.thumbnail_list.count() > self.current_image_index:
                            self.thumbnail_list.setCurrentRow(self.current_image_index)
                        self.show_current_image()
                    else:
                        self.preview_label.clear()
                        self.current_image = None
                        
                except Exception as e:
                    print(f"删除失败：{e}")
                
                self.update_source_stats()


    def on_dest_thumbnail_selected(self, current, previous):
        """处理右侧缩略图选中事件"""
        # 修改：停止视频播放
        self.stop_video()
        
        if current:
            img_file = current.text()
            # 移除类型标识
            if img_file.startswith("[视频] ") or img_file.startswith("[图片] "):
                img_file = img_file.split(" ", 1)[1]
            img_path = os.path.join(self.dest_folder, img_file)
            ext = os.path.splitext(img_file)[1].lower()
            video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv'}
            
            if ext in video_extensions:
                # 播放视频
                self.current_media_type = 'video'
                self.play_video(img_path)
            else:
                # 显示图片
                self.current_media_type = 'image'
                pixmap = QPixmap(img_path)
                if not pixmap.isNull():
                    preview_size = self.preview_label.size()
                    scaled_pixmap = pixmap.scaled(
                        preview_size.width() - 10, 
                        preview_size.height() - 10, 
                        Qt.KeepAspectRatio, 
                        Qt.SmoothTransformation
                    )
                    self.preview_label.setPixmap(scaled_pixmap)
                    self.current_image = img_path
            
            self.dest_preview_list.setFocus()
            self.pause_btn.setEnabled(self.current_media_type == 'video')
            self.progress_slider.setEnabled(self.current_media_type == 'video')


    def update_source_stats(self):
        """更新源文件夹统计信息"""
        total = len(self.image_files)
        # 统计图片和视频数量
        img_count = 0
        video_count = 0
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv'}
        for f in self.image_files:
            ext = os.path.splitext(f)[1].lower()
            if ext in video_extensions:
                video_count += 1
            else:
                img_count += 1
        
        if not hasattr(self, 'original_source_count') or self.original_source_count is None:
            self.original_source_count = total
        deleted = max(0, self.original_source_count - total)
        self.source_stats_label.setText(f"总计:{total} (图片:{img_count}, 视频:{video_count}), 已删除:{deleted}, 剩余:{total}")

    def update_dest_stats(self):
        """更新目标文件夹统计信息"""
        total = self.dest_preview_list.count()
        # 统计图片和视频数量
        img_count = 0
        video_count = 0
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv'}
        for i in range(self.dest_preview_list.count()):
            item = self.dest_preview_list.item(i)
            if item:
                text = item.text()
                if text.startswith("[视频]"):
                    video_count += 1
                elif text.startswith("[图片]"):
                    img_count += 1
        
        if not hasattr(self, 'original_dest_count') or self.original_dest_count is None:
            self.original_dest_count = 0
        added = total - self.original_dest_count
        self.dest_stats_label.setText(f"总计:{total} (图片:{img_count}, 视频:{video_count}), 已添加:{max(0, added)}, 剩余:{total}")

    def get_unique_dest_path(self, filename):
        """生成唯一的目标文件路径，避免覆盖已存在的文件"""
        base_name, ext = os.path.splitext(filename)
        dest_path = os.path.join(self.dest_folder, filename)
        
        counter = 1
        while os.path.exists(dest_path):
            new_filename = f"{base_name}_{counter}{ext}"
            dest_path = os.path.join(self.dest_folder, new_filename)
            counter += 1
        
        return dest_path

    def closeEvent(self, event):
        # 确保在关闭程序时释放视频资源
        self.stop_video()
        if self.thumbnail_thread and self.thumbnail_thread.isRunning():
            self.thumbnail_thread.stop()
            self.thumbnail_thread.wait()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = ImageViewer()
    viewer.show()
    sys.exit(app.exec_())













