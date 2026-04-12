"""
UI 组件模块
处理界面布局、组件初始化等功能
"""
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QTextOption
from PyQt5.QtWidgets import (QHBoxLayout, QVBoxLayout, QFrame, QListWidget,
                             QPushButton, QLabel, QSplitter, QTextEdit,
                             QWidget, QSizePolicy, QSlider)


class UIComponentsMixin:
    """UI 组件功能混入类"""

    def init_ui(self):
        """初始化 UI 界面"""
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 创建主布局
        self.main_layout = QHBoxLayout(central_widget)
        self.main_layout.setSpacing(15)
        self.main_layout.setContentsMargins(15, 15, 15, 15)

        # 左侧面板 - 文件列表和控制按钮
        left_panel = QFrame()
        left_panel.setFrameStyle(QFrame.StyledPanel)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(15, 15, 15, 15)
        left_layout.setSpacing(10)

        # 导入文件夹按钮
        self.import_btn = QPushButton("📁 导入文件夹")
        self.import_btn.setStyleSheet(self._get_import_button_style())
        self.import_btn.clicked.connect(self.import_folder)
        left_layout.addWidget(self.import_btn)

        # 添加拖拽提示标签
        drag_drop_label = QLabel("或将文件夹拖拽至此")
        drag_drop_label.setAlignment(Qt.AlignCenter)
        drag_drop_label.setStyleSheet(self._get_drag_drop_label_style())
        left_layout.addWidget(drag_drop_label)

        # 文件列表标题
        file_label = QLabel("视频文件列表:")
        file_label.setFont(QFont("Arial", 10, QFont.Bold))
        left_layout.addWidget(file_label)

        # 文件列表
        self.file_list = QListWidget()
        self.file_list.currentRowChanged.connect(self.on_file_selected)
        self.file_list.setStyleSheet(self._get_file_list_style())
        left_layout.addWidget(self.file_list, 1)

        # 删除按钮
        self.delete_btn = QPushButton("🗑️ 删除选中媒体及标签")
        self.delete_btn.setStyleSheet(self._get_delete_button_style())
        self.delete_btn.clicked.connect(self.delete_current_file)
        self.delete_btn.setEnabled(False)
        self.delete_btn.setFixedHeight(200)
        left_layout.addWidget(self.delete_btn)

        # 右侧面板 - 预览区域（初始化为默认两列布局）
        self.setup_default_layout(left_panel)

    def _get_import_button_style(self):
        """获取导入按钮样式"""
        return """
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
        """

    def _get_drag_drop_label_style(self):
        """获取拖拽提示标签样式"""
        return """
            QLabel {
                color: #666;
                font-style: italic;
                padding: 5px;
                border: 1px dashed #ccc;
                border-radius: 5px;
                margin: 5px 0;
            }
        """

    def _get_file_list_style(self):
        """获取文件列表样式"""
        return """
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
        """

    def _get_delete_button_style(self):
        """获取删除按钮样式"""
        return """
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
        """

    def setup_default_layout(self, left_panel):
        """设置默认的两列布局"""
        # 清除现有的右侧布局
        while self.main_layout.count() > 1:
            item = self.main_layout.takeAt(1)
            widget = item.widget()
            if widget:
                widget.setParent(None)

        # 右侧面板 - 预览区域
        right_panel = QSplitter(Qt.Vertical)
        right_panel.setStyleSheet("""
            QSplitter::handle {
                background-color: #ddd;
                height: 2px;
            }
        """)

        # 视频播放区域
        video_group = self._create_video_group()

        # 标签内容显示区域
        label_group = self._create_label_group()

        # 导航按钮区域
        nav_group = self._create_nav_group()

        # 添加到分割器
        right_panel.addWidget(video_group)
        right_panel.addWidget(label_group)
        right_panel.addWidget(nav_group)
        right_panel.setSizes([1100, 100, 60])

        # 设置左右面板的比例
        self.main_layout.addWidget(left_panel, 1)
        self.main_layout.addWidget(right_panel, 3)

        # 更新布局模式标志
        self.is_vertical_layout = False

    def _create_video_group(self):
        """创建视频播放区域"""
        video_group = QFrame()
        video_group.setFrameStyle(QFrame.StyledPanel)
        video_layout = QVBoxLayout(video_group)
        video_layout.setContentsMargins(10, 10, 10, 10)
        video_layout.setSpacing(10)

        # 视频标题
        video_title = QLabel("视频预览:")
        video_title.setFont(QFont("Arial", 10, QFont.Bold))
        video_layout.addWidget(video_title)

        # 媒体显示区域容器
        video_container = QWidget()
        video_container.setStyleSheet("background-color: black; border-radius: 5px;")
        video_container_layout = QVBoxLayout(video_container)
        video_container_layout.setContentsMargins(0, 0, 0, 0)

        self.media_label = QLabel("媒体预览将在此显示")
        self.media_label.setAlignment(Qt.AlignCenter)
        self.media_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.media_label.setMinimumSize(1, 1)
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

        # 视频进度控制区域
        progress_group = self._create_progress_group()
        video_layout.addWidget(progress_group)

        return video_group

    def _create_progress_group(self):
        """创建视频进度控制区域"""
        from PyQt5.QtWidgets import QSlider
        progress_group = QFrame()
        progress_layout = QHBoxLayout(progress_group)
        progress_layout.setContentsMargins(5, 5, 5, 5)
        progress_layout.setSpacing(10)

        # 暂停/播放按钮
        self.pause_btn = QPushButton("⏸️")
        self.pause_btn.setStyleSheet(self._get_pause_button_style())
        self.pause_btn.clicked.connect(self.toggle_pause)
        self.pause_btn.setEnabled(False)
        progress_layout.addWidget(self.pause_btn)

        # 当前时间标签
        self.current_time_label = QLabel("00:00")
        self.current_time_label.setStyleSheet("color: white; font-size: 12px;")
        progress_layout.addWidget(self.current_time_label)

        # 进度滑块
        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setStyleSheet(self._get_slider_style())
        self.progress_slider.sliderPressed.connect(self.on_slider_pressed)
        self.progress_slider.sliderReleased.connect(self.on_slider_released)
        self.progress_slider.sliderMoved.connect(self.on_slider_moved)
        progress_layout.addWidget(self.progress_slider)

        # 总时长标签
        self.total_time_label = QLabel("00:00")
        self.total_time_label.setStyleSheet("color: white; font-size: 12px;")
        progress_layout.addWidget(self.total_time_label)

        return progress_group

    def _get_pause_button_style(self):
        """获取暂停按钮样式"""
        return """
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
            QPushButton:hover:!disabled {
                background-color: #F57C00;
            }
            QPushButton:pressed:!disabled {
                background-color: #E65100;
            }
        """

    def _get_slider_style(self):
        """获取进度滑块样式"""
        return """
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
        """

    def _create_label_group(self):
        """创建标签内容显示区域"""
        label_group = QFrame()
        label_group.setFrameStyle(QFrame.StyledPanel)
        label_layout = QVBoxLayout(label_group)
        label_layout.setContentsMargins(10, 10, 10, 10)
        label_layout.setSpacing(10)

        # 标签标题
        label_title = QLabel("标签内容:")
        label_title.setFont(QFont("Arial", 10, QFont.Bold))
        label_layout.addWidget(label_title)

        # 标签内容编辑框
        self.label_content = QTextEdit()
        self.label_content.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        self.label_content.textChanged.connect(self.on_label_text_changed)
        self.label_content.setStyleSheet(self._get_label_content_style())
        label_layout.addWidget(self.label_content)

        # 保存状态标签
        self.save_status_label = QLabel("")
        self.save_status_label.setStyleSheet(self._get_save_status_style())
        label_layout.addWidget(self.save_status_label)

        return label_group

    def _get_label_content_style(self):
        """获取标签内容编辑框样式"""
        return """
            QTextEdit {
                background-color: #f9f9f9;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 10px;
                font-family: Consolas, monospace;
                font-size: 32px;
                min-height: 100px;
            }
        """

    def _get_save_status_style(self):
        """获取保存状态标签样式"""
        return """
            QLabel {
                color: #666;
                font-style: italic;
                font-size: 12px;
                padding: 2px;
            }
        """

    def _create_nav_group(self):
        """创建导航按钮区域"""
        nav_group = QFrame()
        nav_group.setFrameStyle(QFrame.StyledPanel)
        nav_layout = QHBoxLayout(nav_group)
        nav_layout.setContentsMargins(10, 10, 10, 10)
        nav_layout.setSpacing(10)

        self.prev_btn = QPushButton("⏮️ 上一个媒体")
        self.prev_btn.setStyleSheet(self._get_nav_button_style())
        self.prev_btn.setFixedHeight(200)
        self.prev_btn.clicked.connect(self.select_prev_video)
        self.prev_btn.setEnabled(False)
        nav_layout.addWidget(self.prev_btn)

        self.next_btn = QPushButton("下一个媒体 ⏭️")
        self.next_btn.setStyleSheet(self._get_nav_button_style())
        self.next_btn.setFixedHeight(200)
        self.next_btn.clicked.connect(self.select_next_video)
        self.next_btn.setEnabled(False)
        nav_layout.addWidget(self.next_btn)

        return nav_group

    def _get_nav_button_style(self):
        """获取导航按钮样式"""
        return """
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
        """

    def setup_vertical_layout(self, left_panel):
        """设置竖屏的三列布局"""
        # 清除现有的右侧布局
        while self.main_layout.count() > 1:
            item = self.main_layout.takeAt(1)
            widget = item.widget()
            if widget:
                widget.setParent(None)

        # 创建三列布局
        middle_panel = QFrame()
        middle_panel.setFrameStyle(QFrame.StyledPanel)
        middle_layout = QVBoxLayout(middle_panel)
        middle_layout.setContentsMargins(10, 10, 10, 10)
        middle_layout.setSpacing(10)

        # 视频播放区域（简化版）
        video_group = self._create_compact_video_group()
        middle_layout.addWidget(video_group)

        # 右侧面板 - 标签区域
        right_panel = self._create_vertical_label_group()

        # 设置三列比例
        self.main_layout.addWidget(left_panel, 1)
        self.main_layout.addWidget(middle_panel, 2)
        self.main_layout.addWidget(right_panel, 2)

        # 更新布局模式标志
        self.is_vertical_layout = True

    def _create_compact_video_group(self):
        """创建紧凑版视频播放区域"""
        from PyQt5.QtWidgets import QSlider
        video_group = QFrame()
        video_group.setFrameStyle(QFrame.StyledPanel)
        video_layout = QVBoxLayout(video_group)
        video_layout.setContentsMargins(5, 5, 5, 5)
        video_layout.setSpacing(5)

        video_title = QLabel("媒体预览:")
        video_title.setFont(QFont("Arial", 10, QFont.Bold))
        video_layout.addWidget(video_title)

        video_container = QWidget()
        video_container.setStyleSheet("background-color: black; border-radius: 5px;")
        video_container_layout = QVBoxLayout(video_container)
        video_container_layout.setContentsMargins(0, 0, 0, 0)

        self.media_label = QLabel("媒体预览将在此显示")
        self.media_label.setAlignment(Qt.AlignCenter)
        self.media_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.media_label.setMinimumSize(1, 1)
        self.media_label.setStyleSheet("""
            QLabel {
                background-color: black;
                color: white;
                border-radius: 5px;
                font-size: 12px;
            }
        """)
        video_container_layout.addWidget(self.media_label)
        video_layout.addWidget(video_container)

        # 紧凑版进度控制
        progress_group = QFrame()
        progress_layout = QHBoxLayout(progress_group)
        progress_layout.setContentsMargins(2, 2, 2, 2)
        progress_layout.setSpacing(5)

        self.pause_btn = QPushButton("⏸️")
        self.pause_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                padding: 3px;
                font-size: 12px;
                border-radius: 3px;
                min-width: 30px;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.pause_btn.clicked.connect(self.toggle_pause)
        self.pause_btn.setEnabled(False)
        progress_layout.addWidget(self.pause_btn)

        self.current_time_label = QLabel("00:00")
        self.current_time_label.setStyleSheet("color: white; font-size: 10px;")
        progress_layout.addWidget(self.current_time_label)

        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #999999;
                height: 6px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #B1B1B1, stop:1 #c4c4c4);
                margin: 1px 0;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #b4b4b4, stop:1 #8f8f8f);
                border: 1px solid #5c5c5c;
                width: 12px;
                margin: -1px 0;
                border-radius: 2px;
            }
        """)
        self.progress_slider.sliderPressed.connect(self.on_slider_pressed)
        self.progress_slider.sliderReleased.connect(self.on_slider_released)
        self.progress_slider.sliderMoved.connect(self.on_slider_moved)
        progress_layout.addWidget(self.progress_slider)

        self.total_time_label = QLabel("00:00")
        self.total_time_label.setStyleSheet("color: white; font-size: 10px;")
        progress_layout.addWidget(self.total_time_label)

        video_layout.addWidget(progress_group)

        return video_group

    def _create_vertical_label_group(self):
        """创建竖屏布局的标签区域"""
        right_panel = QFrame()
        right_panel.setFrameStyle(QFrame.StyledPanel)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)
        right_layout.setSpacing(10)

        label_title = QLabel("标签内容:")
        label_title.setFont(QFont("Arial", 10, QFont.Bold))
        right_layout.addWidget(label_title)

        self.label_content = QTextEdit()
        self.label_content.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        self.label_content.textChanged.connect(self.on_label_text_changed)
        self.label_content.setStyleSheet("""
            QTextEdit {
                background-color: #f9f9f9;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 8px;
                font-family: Consolas, monospace;
                font-size: 32px;
                min-height: 200px;
            }
        """)
        right_layout.addWidget(self.label_content)

        self.save_status_label = QLabel("")
        self.save_status_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-style: italic;
                font-size: 10px;
                padding: 2px;
            }
        """)
        right_layout.addWidget(self.save_status_label)

        # 导航按钮
        nav_group = QFrame()
        nav_group.setFrameStyle(QFrame.StyledPanel)
        nav_layout = QVBoxLayout(nav_group)
        nav_layout.setContentsMargins(5, 5, 5, 5)
        nav_layout.setSpacing(5)

        self.prev_btn = QPushButton("⏮️ 上一个")
        self.prev_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 5px;
                font-size: 10px;
                border-radius: 3px;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.prev_btn.setFixedHeight(200)
        self.prev_btn.clicked.connect(self.select_prev_video)
        self.prev_btn.setEnabled(False)
        nav_layout.addWidget(self.prev_btn)

        self.next_btn = QPushButton("下一个 ⏭️")
        self.next_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 5px;
                font-size: 10px;
                border-radius: 3px;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.next_btn.setFixedHeight(200)
        self.next_btn.clicked.connect(self.select_next_video)
        self.next_btn.setEnabled(False)
        nav_layout.addWidget(self.next_btn)

        right_layout.addWidget(nav_group)

        return right_panel

    def check_and_update_layout(self, width, height):
        """根据媒体宽高比检查并更新布局"""
        if width > 0 and height > 0:
            aspect_ratio = width / height
            should_be_vertical = aspect_ratio < 0.8

            if should_be_vertical != self.is_vertical_layout:
                current_content = self.label_content.toPlainText()
                current_modified = self.label_modified
                current_label_file = self.current_label_file

                left_panel = self.main_layout.itemAt(0).widget()
                if should_be_vertical:
                    self.setup_vertical_layout(left_panel)
                else:
                    self.setup_default_layout(left_panel)

                self.label_content.setPlainText(current_content)
                self.label_modified = current_modified
                self.current_label_file = current_label_file
                self.update_save_status()
