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
        self.video_files = []  # 存储相对路径
        self.video_files_full_path = []  # 存储完整路径
        self.current_index = 0
        
        # 视频播放相关
        self.video_capture = None
        self.playback_timer = QTimer()
        self.playback_timer.timeout.connect(self.update_frame)
        
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
        self.delete_btn = QPushButton("🗑️ 删除选中视频及标签")
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
        self.delete_btn.setFixedHeight(80)
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
        
        # 修改: 创建一个容器来放置视频显示区域
        video_container = QWidget()
        video_container.setStyleSheet("background-color: black; border-radius: 5px;")
        video_container_layout = QVBoxLayout(video_container)
        video_container_layout.setContentsMargins(0, 0, 0, 0)
        
        # 使用QLabel显示视频帧
        self.video_label = QLabel("视频预览将在此显示")
        self.video_label.setAlignment(Qt.AlignCenter)
        # 修改: 设置视频标签的尺寸策略，允许其扩展填充可用空间
        self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_label.setMinimumSize(1, 1)  # 允许缩小到很小
        self.video_label.setStyleSheet("""
            QLabel {
                background-color: black;
                color: white;
                border-radius: 5px;
                font-size: 16px;
            }
        """)
        video_container_layout.addWidget(self.video_label)
        
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
        
        self.prev_btn = QPushButton("⏮️ 上一个视频")
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
        
        self.next_btn = QPushButton("下一个视频 ⏭️")
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
            
    def load_files(self):
        if not self.current_folder:
            return
            
        # 清空现有数据
        self.video_files = []
        self.video_files_full_path = []
        self.file_list.clear()
        self.stop_video()
        self.label_content.setText("标签内容将在此显示")
        self.current_index = -1
        self.delete_btn.setEnabled(False)
        
        # 支持的视频格式
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv'}
        
        # 递归获取所有视频文件
        for root, dirs, files in os.walk(self.current_folder):
            for file in files:
                if os.path.splitext(file)[1].lower() in video_extensions:
                    full_path = os.path.join(root, file)
                    relative_path = os.path.relpath(full_path, self.current_folder)
                    self.video_files.append(relative_path)
                    self.video_files_full_path.append(full_path)
        
        # 按名称排序
        # 将完整路径和相对路径一起排序
        combined = list(zip(self.video_files, self.video_files_full_path))
        combined.sort(key=lambda x: x[0])  # 按相对路径排序
        if combined:
            self.video_files, self.video_files_full_path = zip(*combined)
            self.video_files = list(self.video_files)
            self.video_files_full_path = list(self.video_files_full_path)
        
        # 添加到列表 (只显示相对路径)
        for video_file in self.video_files:
            display_name = os.path.splitext(video_file)[0]  # 去掉扩展名
            # 添加所在目录信息 (如果不是根目录)
            dir_name = os.path.dirname(video_file)
            if dir_name:
                display_name = f"[{dir_name}] {os.path.basename(display_name)}"
            self.file_list.addItem(display_name)
            
        # 如果有文件，默认选择第一个
        if self.video_files:
            self.file_list.setCurrentRow(0)
            
    def on_file_selected(self, index):
        if index < 0 or index >= len(self.video_files):
            return
            
        self.current_index = index
        
        # 更新按钮状态
        self.update_navigation_buttons()
        
        video_file = self.video_files[index]
        
        # 获取不带扩展名的文件名
        base_name = os.path.splitext(video_file)[0]
        
        # 更新视频预览
        self.update_video_preview(video_file)
        
        # 更新标签预览
        self.update_label_preview(base_name)
        
        # 启用删除按钮
        self.delete_btn.setEnabled(True)
        
        # 更新导航按钮状态
        self.update_navigation_buttons()
        
    def update_video_preview(self, video_file):
        if not self.current_folder:
            return
            
        # 使用完整路径打开视频文件
        video_path = self.video_files_full_path[self.current_index]
        
        # 停止当前播放
        self.stop_video()
        
        # 打开新的视频文件
        self.video_capture = cv2.VideoCapture(video_path)
        if not self.video_capture.isOpened():
            # 修改: 重置标签高度以便正确显示文本
            self.video_label.setFixedHeight(30)
            self.video_label.setText("无法打开视频文件")
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
                self.video_label.size(), 
                Qt.KeepAspectRatio, 
                Qt.SmoothTransformation
            )
            self.video_label.setPixmap(scaled_pixmap)
            # 修改: 移除之前的固定高度设置，让标签自动适应
        else:
            # 视频播放结束，重新开始
            self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
            
    def stop_video(self):
        self.playback_timer.stop()
        if self.video_capture is not None:
            self.video_capture.release()
            self.video_capture = None
        # 修改: 重置视频标签为初始状态，但保持其可扩展性
        self.video_label.setText("视频预览将在此显示")
        self.video_label.setPixmap(QPixmap())  # 使用空的QPixmap对象清除现有的pixmap
        self.video_label.setStyleSheet("""
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
        video_file = self.video_files[self.current_index]
        video_dir = os.path.dirname(self.video_files_full_path[self.current_index])
        
        # 查找匹配的标签文件
        label_extensions = ['.txt', '.xml', '.json', '.csv']
        label_file = None
        
        # 在视频文件所在目录查找标签文件
        for ext in label_extensions:
            potential_file = os.path.splitext(os.path.basename(video_file))[0] + ext
            potential_path = os.path.join(video_dir, potential_file)
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
        if self.current_index < 0 or self.current_index >= len(self.video_files):
            return

        import time
        current_time = time.time()

        # 检查是否在1秒内第二次点击
        if current_time - self.last_delete_click_time < 1.0:
            # 第二次点击，执行删除
            self.delete_click_count += 1
            
            # 在删除前先停止视频播放，释放资源
            self.stop_video()

            video_file = self.video_files[self.current_index]
            video_path = self.video_files_full_path[self.current_index]
            video_dir = os.path.dirname(video_path)
            base_name = os.path.splitext(os.path.basename(video_file))[0]

            # 删除视频文件
            try:
                os.remove(video_path)
            except Exception as e:
                QMessageBox.warning(self, "删除失败", f"无法删除视频文件: {str(e)}")
                return

            # 删除对应的标签文件 (在视频文件所在目录查找)
            label_extensions = ['.txt', '.xml', '.json', '.csv']
            for ext in label_extensions:
                label_file = base_name + ext
                label_path = os.path.join(video_dir, label_file)
                if os.path.exists(label_path):
                    try:
                        os.remove(label_path)
                    except Exception as e:
                        QMessageBox.warning(self, "删除警告", f"无法删除标签文件 {label_file}: {str(e)}")

            # 保存当前要删除的行号
            deleted_row = self.current_index

            # 从列表中移除
            self.video_files.pop(self.current_index)
            self.video_files_full_path.pop(self.current_index)
            self.file_list.takeItem(self.current_index)

            # 自动选择下一个项目，如果没有下一个则选择上一个
            if self.video_files:
                # 如果删除的是最后一个项目，则选择新的最后一个项目
                if deleted_row >= len(self.video_files):
                    self.current_index = len(self.video_files) - 1
                else:
                    # 否则保持相同的索引
                    self.current_index = deleted_row-1

                # 设置当前行为当前索引，触发on_file_selected方法
                self.file_list.setCurrentRow(self.current_index)
                # 确保文件列表获得焦点，使键盘操作恢复正常
                self.file_list.setFocus()
                
                # 更新导航按钮状态
                self.update_navigation_buttons()
            else:
                # 没有剩余文件，重置界面
                self.current_index = -1
                self.label_content.setText("标签内容将在此显示")
                self.delete_btn.setEnabled(False)
                self.prev_btn.setEnabled(False)
                self.next_btn.setEnabled(False)
                self.update_navigation_buttons()
                
            # 显示删除完成弹窗
            msg = QMessageBox()
            msg.setWindowTitle("删除完成")
            msg.setText("文件已成功删除")
            msg.setStandardButtons(QMessageBox.NoButton)  # 不显示按钮，自动关闭
            msg.show()
            # 使用QTimer在1秒后自动关闭弹窗
            from PyQt5.QtCore import QTimer
            timer = QTimer()
            timer.singleShot(1000, msg.close)
            
            # 重置计数器
            self.last_delete_click_time = 0
            self.delete_click_count = 0
        else:
            # 第一次点击，记录时间
            self.last_delete_click_time = current_time
            self.delete_click_count = 1
            
            # 显示提示信息
            msg = QMessageBox()
            msg.setWindowTitle("删除提示")
            msg.setText("再次点击删除按钮将删除当前文件")
            msg.setStandardButtons(QMessageBox.NoButton)  # 不显示按钮，自动关闭
            msg.show()
            # 使用QTimer在1秒后自动关闭弹窗
            from PyQt5.QtCore import QTimer
            timer = QTimer()
            timer.singleShot(1000, msg.close)
            
    def select_prev_video(self):
        """选择上一个视频"""
        if self.current_index > 0:
            self.current_index -= 1
            self.file_list.setCurrentRow(self.current_index)
    
    def select_next_video(self):
        """选择下一个视频"""
        if self.current_index < len(self.video_files) - 1:
            self.current_index += 1
            self.file_list.setCurrentRow(self.current_index)
            
    def update_navigation_buttons(self):
        """更新导航按钮状态"""
        has_videos = len(self.video_files) > 0
        has_prev = self.current_index > 0 if has_videos else False
        has_next = self.current_index < len(self.video_files) - 1 if has_videos else False
        
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