import os
import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QListWidget, QLabel, QFileDialog, QMessageBox,
                             QSplitter, QFrame, QSizePolicy)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap, QFont
import cv2

class VideoLabelManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("视频标签管理器")
        self.setGeometry(100, 100, 1920, 1280)
        
        # 数据存储
        self.current_folder = ""
        self.media_files = []  # 存储相对路径（图片和视频）
        self.media_files_full_path = []  # 存储完整路径（图片和视频）
        self.current_index = 0
        
        # 视频播放相关
        self.video_capture = None
        self.playback_timer = QTimer()
        self.playback_timer.timeout.connect(self.update_frame)
        
        # 添加媒体类型标识
        self.current_media_type = None  # 'video', 'image', or None
        
        # 启用拖拽功能
        self.setAcceptDrops(True)
        
        # 添加双击删除相关的变量
        self.last_delete_click_time = 0
        self.delete_click_count = 0
        
        self.init_ui()
        
    def init_ui(self):
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # 左侧面板 - 文件列表和控制按钮
        left_panel = QFrame()
        left_panel.setFrameStyle(QFrame.StyledPanel)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(15, 15, 15, 15)
        left_layout.setSpacing(10)
        
        # 导入文件夹按钮
        self.import_btn = QPushButton("📁 导入文件夹")
        self.import_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        self.import_btn.clicked.connect(self.import_folder)
        left_layout.addWidget(self.import_btn)
        
        # 添加拖拽提示标签
        drag_drop_label = QLabel("或将文件夹拖拽至此")
        drag_drop_label.setAlignment(Qt.AlignCenter)
        drag_drop_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-style: italic;
                padding: 5px;
                border: 1px dashed #ccc;
                border-radius: 5px;
                margin: 5px 0;
            }
        """)
        left_layout.addWidget(drag_drop_label)
        
        # 文件列表标题
        file_label = QLabel("视频文件列表:")
        file_label.setFont(QFont("Arial", 10, QFont.Bold))
        left_layout.addWidget(file_label)
        
        # 文件列表
        self.file_list = QListWidget()
        self.file_list.currentRowChanged.connect(self.on_file_selected)
        self.file_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #ccc;
                border-radius: 5px;
                padding: 5px;
                background-color: #fff;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background-color: #4CAF50;
                color: white;
            }
        """)
        # 修改: 让文件列表占据剩余空间
        left_layout.addWidget(self.file_list, 1)
        
        # 删除按钮
        self.delete_btn = QPushButton("🗑️ 删除选中媒体及标签")
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
            QPushButton:hover:!disabled {
                background-color: #d32f2f;
            }
            QPushButton:pressed:!disabled {
                background-color: #b71c1c;
            }
        """)
        self.delete_btn.clicked.connect(self.delete_current_file)
        self.delete_btn.setEnabled(False)
        # 修改: 将删除按钮设置为固定高度
        self.delete_btn.setFixedHeight(200)
        left_layout.addWidget(self.delete_btn)
        

        # 右侧面板 - 预览区域
        right_panel = QSplitter(Qt.Vertical)
        right_panel.setStyleSheet("""
            QSplitter::handle {
                background-color: #ddd;
                height: 2px;
            }
        """)
        
        # 视频播放区域
        video_group = QFrame()
        video_group.setFrameStyle(QFrame.StyledPanel)
        video_layout = QVBoxLayout(video_group)
        video_layout.setContentsMargins(10, 10, 10, 10)
        video_layout.setSpacing(10)
        
        # 视频标题
        video_title = QLabel("视频预览:")
        video_title.setFont(QFont("Arial", 10, QFont.Bold))
        video_layout.addWidget(video_title)
        
        # 修改: 创建一个容器来放置媒体显示区域
        video_container = QWidget()
        video_container.setStyleSheet("background-color: black; border-radius: 5px;")
        video_container_layout = QVBoxLayout(video_container)
        video_container_layout.setContentsMargins(0, 0, 0, 0)
        
        # 使用QLabel显示媒体内容
        self.media_label = QLabel("媒体预览将在此显示")
        self.media_label.setAlignment(Qt.AlignCenter)
        # 修改: 设置媒体标签的尺寸策略，允许其扩展填充可用空间
        self.media_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.media_label.setMinimumSize(1, 1)  # 允许缩小到很小
        self.media_label.setStyleSheet("""
            QLabel {
                background-color: black;
                color: white;
                border-radius: 5px;
                font-size: 16px;
            }
        """)
        video_container_layout.addWidget(self.media_label)
        
        video_layout.addWidget(video_container)
        
        # 标签内容显示区域
        label_group = QFrame()
        label_group.setFrameStyle(QFrame.StyledPanel)
        label_layout = QVBoxLayout(label_group)
        label_layout.setContentsMargins(10, 10, 10, 10)
        label_layout.setSpacing(10)
        
        # 标签标题
        label_title = QLabel("标签内容:")
        label_title.setFont(QFont("Arial", 10, QFont.Bold))
        label_layout.addWidget(label_title)
        
        self.label_content = QLabel("标签内容将在此显示")
        self.label_content.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.label_content.setWordWrap(True)
        self.label_content.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.label_content.setStyleSheet("""
            QLabel {
                background-color: #f9f9f9;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 10px;
                font-family: Consolas, monospace;
                min-height: 100px;
            }
        """)
        label_layout.addWidget(self.label_content)
        
        # 添加导航按钮区域
        nav_group = QFrame()
        nav_group.setFrameStyle(QFrame.StyledPanel)
        nav_layout = QHBoxLayout(nav_group)
        nav_layout.setContentsMargins(10, 10, 10, 10)
        nav_layout.setSpacing(10)
        
        self.prev_btn = QPushButton("⏮️ 上一个媒体")
        self.prev_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px;
                font-size: 12px;
                border-radius: 5px;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
            QPushButton:hover:!disabled {
                background-color: #0b7dda;
            }
            QPushButton:pressed:!disabled {
                background-color: #095fa3;
            }
        """)
        self.prev_btn.setFixedHeight(200)
        self.prev_btn.clicked.connect(self.select_prev_video)
        self.prev_btn.setEnabled(False)
        nav_layout.addWidget(self.prev_btn)
        
        self.next_btn = QPushButton("下一个媒体 ⏭️")
        self.next_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px;
                font-size: 12px;
                border-radius: 5px;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
            QPushButton:hover:!disabled {
                background-color: #0b7dda;
            }
            QPushButton:pressed:!disabled {
                background-color: #095fa3;
            }
        """)
        self.next_btn.setFixedHeight(200)
        self.next_btn.clicked.connect(self.select_next_video)
        self.next_btn.setEnabled(False)
        nav_layout.addWidget(self.next_btn)
        
        # 添加到分割器
        right_panel.addWidget(video_group)
        right_panel.addWidget(label_group)
        right_panel.addWidget(nav_group)
        right_panel.setSizes([1100, 100, 60])
        
        # 设置左右面板的比例
        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(right_panel, 3)
        
    # 添加拖拽事件处理方法
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            # 检查是否是文件夹
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
            
    def get_image_info(self, image_path):
        """获取图片的分辨率信息"""
        try:
            img = cv2.imread(image_path)
            if img is not None:
                height, width, channels = img.shape
                return f"{width}x{height} ({channels} channels)"
            else:
                # 如果cv2无法读取，尝试使用PIL
                from PIL import Image
                pil_img = Image.open(image_path)
                width, height = pil_img.size
                return f"{width}x{height} ({pil_img.mode})"
        except Exception as e:
            return f"Error reading image: {str(e)}"

    def get_video_info(self, video_path):
        """获取视频的分辨率、帧率和总帧数信息"""
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return "无法打开视频文件"
                
            # 获取视频属性
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            cap.release()
            
            # 格式化信息字符串
            resolution = f"{width}x{height}"
            fps_str = f"{fps:.2f}fps" if fps > 0 else "unknown fps"
            frames_str = f"{total_frames} frames" if total_frames > 0 else "unknown frames"
            
            return f"{resolution}, {fps_str}, {frames_str}"
        except Exception as e:
            return f"Error reading video: {str(e)}"
    
    def load_files(self):
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
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.gif'}
        
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
        # 将完整路径和相对路径一起排序
        combined = list(zip(self.media_files, self.media_files_full_path))
        combined.sort(key=lambda x: x[0])  # 按相对路径排序
        if combined:
            self.media_files, self.media_files_full_path = zip(*combined)
            self.media_files = list(self.media_files)
            self.media_files_full_path = list(self.media_files_full_path)
        
        for i, media_file in enumerate(self.media_files):
            display_name = os.path.splitext(media_file)[0]  # 去掉扩展名
            # 添加所在目录信息 (如果不是根目录)
            dir_name = os.path.dirname(media_file)
            if dir_name:
                display_name = f"[{dir_name}] {os.path.basename(display_name)}"
            
            # 获取文件详细信息
            file_ext = os.path.splitext(media_file)[1].lower()
            full_path = self.media_files_full_path[i]
            info_str = ""
            
            if file_ext in image_extensions:
                # 图片文件
                info_str = self.get_image_info(full_path)
                display_name = f" {display_name} [图片] - {info_str}"  # 添加行号
            elif file_ext in video_extensions:
                # 视频文件
                info_str = self.get_video_info(full_path)
                display_name = f"{display_name} [视频] - {info_str}"  # 添加行号
            else:
                # 其他类型文件
                display_name = f"{display_name} [未知类型]"  # 添加行号
            
            self.file_list.addItem(display_name)
            
        # 如果有文件，默认选择第一个
        if self.media_files:
            self.file_list.setCurrentRow(0)
            
    def on_file_selected(self, index):
        if index < 0 or index >= len(self.media_files):
            return
            
        self.current_index = index
        
        # 更新按钮状态
        self.update_navigation_buttons()
        
        video_file = self.media_files[index]
        
        # 获取不带扩展名的文件名
        base_name = os.path.splitext(video_file)[0]
        
        # 更新媒体预览（图片或视频）
        self.update_media_preview(video_file)
        
        # 更新标签预览
        self.update_label_preview(base_name)
        
        # 启用删除按钮
        self.delete_btn.setEnabled(True)
        
        # 更新导航按钮状态
        self.update_navigation_buttons()
        
    def update_media_preview(self, media_file):
        if not self.current_folder:
            return
            
        # 使用完整路径获取媒体文件
        media_path = self.media_files_full_path[self.current_index]
        ext = os.path.splitext(media_path)[1].lower()
        
        # 判断是图片还是视频
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.gif'}
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv'}
        
        if ext in image_extensions:
            # 处理图片文件
            self.current_media_type = 'image'
            self.stop_video()  # 确保停止任何视频播放
            self.display_image(media_path)
        elif ext in video_extensions:
            # 处理视频文件
            self.current_media_type = 'video'
            self.update_video_preview(media_file)
        else:
            # 不支持的文件类型
            self.current_media_type = None
            self.media_label.setText("不支持的文件类型")
    
    def display_image(self, image_path):
        """显示图片"""
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            # 缩放以适应标签大小
            scaled_pixmap = pixmap.scaled(
                self.media_label.size(), 
                Qt.KeepAspectRatio, 
                Qt.SmoothTransformation
            )
            self.media_label.setPixmap(scaled_pixmap)
        else:
            self.media_label.setText("无法加载图片")
            
    def update_video_preview(self, video_file):
        if not self.current_folder:
            return
            
        # 使用完整路径打开视频文件
        video_path = self.media_files_full_path[self.current_index]
        
        # 停止当前播放
        self.stop_video()
        
        # 打开新的视频文件
        self.video_capture = cv2.VideoCapture(video_path)
        if not self.video_capture.isOpened():
            # 修改: 重置标签高度以便正确显示文本
            self.media_label.setFixedHeight(30)
            self.media_label.setText("无法打开视频文件")
            return
            
        # 获取视频的原始帧率
        fps = self.video_capture.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            # 如果无法获取帧率，使用默认值
            fps = 30
            
        # 开始播放
        self.playback_timer.start(int(1000 / fps))  # 使用原始帧率计算间隔时间
        
    def update_frame(self):
        if self.video_capture is None:
            return
            
        ret, frame = self.video_capture.read()
        if ret:
            # 转换颜色空间 (OpenCV使用BGR，Qt使用RGB)
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
            # 修改: 移除之前的固定高度设置，让标签自动适应
        else:
            # 视频播放结束，重新开始
            self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
            
    def stop_video(self):
        self.playback_timer.stop()
        if self.video_capture is not None:
            self.video_capture.release()
            self.video_capture = None
        # 修改: 重置媒体标签为初始状态，但保持其可扩展性
        self.media_label.setText("媒体预览将在此显示")
        self.media_label.setPixmap(QPixmap())  # 使用空的QPixmap对象清除现有的pixmap
        self.media_label.setStyleSheet("""
            QLabel {
                background-color: black;
                color: white;
                border-radius: 5px;
                font-size: 16px;
            }
        """)
        
    def update_label_preview(self, base_name):
        if not self.current_folder:
            return
            
        # 使用完整路径查找标签文件
        media_file = self.media_files[self.current_index]
        media_dir = os.path.dirname(self.media_files_full_path[self.current_index])
        
        # 查找匹配的标签文件
        label_extensions = ['.txt', '.xml', '.json', '.csv']
        label_file = None
        
        # 在媒体文件所在目录查找标签文件
        for ext in label_extensions:
            potential_file = os.path.splitext(os.path.basename(media_file))[0] + ext
            potential_path = os.path.join(media_dir, potential_file)
            if os.path.exists(potential_path):
                label_file = potential_path
                break
                
        if label_file:
            try:
                with open(label_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.label_content.setText(content)
            except Exception as e:
                self.label_content.setText(f"无法读取标签文件: {str(e)}")
        else:
            self.label_content.setText("未找到对应的标签文件")
            

    def delete_current_file(self):
        if self.current_index < 0 or self.current_index >= len(self.media_files):
            return

        import time
        current_time = time.time()

        # 检查是否在1秒内第二次点击
        if current_time - self.last_delete_click_time < 1.0:
            # 第二次点击，执行删除
            self.delete_click_count += 1
            # 在删除前先停止视频播放，释放资源
            self.stop_video()

            media_file = self.media_files[self.current_index]
            media_path = self.media_files_full_path[self.current_index]
            media_dir = os.path.dirname(media_path)
            base_name = os.path.splitext(os.path.basename(media_file))[0]

            # 删除媒体文件（图片或视频）
            try:
                os.remove(media_path)
            except Exception as e:
                QMessageBox.warning(self, "删除失败", f"无法删除媒体文件: {str(e)}")
                return

            # 删除对应的标签文件 (在媒体文件所在目录查找)
            label_extensions = ['.txt', '.xml', '.json', '.csv']
            for ext in label_extensions:
                label_file = base_name + ext
                label_path = os.path.join(media_dir, label_file)
                if os.path.exists(label_path):
                    try:
                        os.remove(label_path)
                    except Exception as e:
                        QMessageBox.warning(self, "删除警告", f"无法删除标签文件 {label_file}: {str(e)}")

            # 从列表中移除已删除的文件
            del self.media_files[self.current_index]
            del self.media_files_full_path[self.current_index]
            
            # 更新文件列表UI
            self.file_list.takeItem(self.current_index)
            
            # 调整当前索引
            if self.current_index >= len(self.media_files) and self.current_index > 0:
                self.current_index = self.current_index - 1
            
            # 如果还有文件，选择当前索引的文件，否则清空预览
            if len(self.media_files) > 0:
                self.file_list.setCurrentRow(self.current_index)
                self.on_file_selected(self.current_index)
            else:
                # 没有文件时，清空预览
                self.media_label.setText("媒体预览将在此显示")
                self.label_content.setText("标签内容将在此显示")
                self.delete_btn.setEnabled(False)
                self.update_navigation_buttons()
                
            #点击一次左箭头按键
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
        if self.current_index > 0:
            self.current_index -= 1
            self.file_list.setCurrentRow(self.current_index)
    
    def select_next_video(self):
        """选择下一个媒体"""
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
        
    def closeEvent(self, event):
        # 确保在关闭程序时释放资源
        self.stop_video()
        event.accept()

def main():
    app = QApplication(sys.argv)
    window = VideoLabelManager()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()