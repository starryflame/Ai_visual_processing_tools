import os
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QListWidget, QTextEdit, QLabel, 
                             QMessageBox, QLineEdit, QAbstractItemView,
                             QCheckBox, QScrollArea, QFrame, QListWidgetItem,
                             QGroupBox, QSplitter, QTreeWidget,
                             QGridLayout, QTabWidget)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QSize
from image_processor import ImageProcessor
from styles import *

# 页面尺寸配置类
class PageSizeConfig:
    # 窗口尺寸配置
    WINDOW_WIDTH = 2400
    WINDOW_HEIGHT = 1440
    WINDOW_X = 100
    WINDOW_Y = 100
    
    # 缩略图尺寸配置
    THUMBNAIL_WIDTH = 400
    THUMBNAIL_HEIGHT = 400
    
    # 网格尺寸配置
    GRID_WIDTH = 450
    GRID_HEIGHT = 450
    
    # 间距配置
    ITEM_SPACING = 10
    
    # 图片预览区域最小尺寸
    IMAGE_PREVIEW_MIN_WIDTH = 400
    IMAGE_PREVIEW_MIN_HEIGHT = 400
    
    # 分割器初始尺寸配置
    MIDDLE_SPLITTER_SIZES = [500, 300]  # 上下区域比例
    MAIN_SPLITTER_SIZES = [300, 1000, 600]  # 左中右区域比例
    
    # 右侧面板配置
    RIGHT_PANEL_MIN_WIDTH = 300
    
    # 预设标签区域配置
    PRESET_TAGS_MAX_HEIGHT = 600

# 全局字体设置
GLOBAL_FONT_FAMILY = "PingFang SC"  # 圆体字体
GLOBAL_FONT_SIZE = 14  # 增大字体大小
GLOBAL_FONT = QFont(GLOBAL_FONT_FAMILY, GLOBAL_FONT_SIZE)


class TaggerUI(QMainWindow):
    # 从core的各个模块导入所需函数
    from code.file_operations import import_folder
    from code.file_operations import append_folder
    from code.file_operations import update_file_list
    from code.file_operations import export_renamed_files
    from code.file_operations import delete_selected_images
    from code.file_operations import refresh_current_view
    from code.ui_event_handlers import on_thumbnail_loaded
    from code.ui_event_handlers import on_file_selected
    from code.ui_event_handlers import on_files_selected
    from code.tag_management import update_tag_checkboxes
    from code.tag_management import move_selected_tags_to_front
    from code.tag_management import add_tag_to_all_selected
    from code.tag_management import delete_selected_tag_from_all
    from code.tag_management import modify_selected_tag_for_all
    from code.batch_operations import select_all_images
    from code.batch_operations import deselect_all_images
    from code.preset_tags import save_preset_tags
    from code.preset_tags import update_preset_tags_display
    from code.preset_tags import delete_preset_tag
    from code.preset_tags import add_preset_tag_group_to_current
    from code.statistics import update_tag_statistics
    from code.statistics import update_statistics_display
    from code.statistics import update_statistics
    from code.ai_caption_generator import generate_caption_for_selected
    
    def __init__(self):
        super().__init__()
        self.image_processor = ImageProcessor()
        # 连接信号
        self.image_processor.thumbnail_loaded.connect(self.on_thumbnail_loaded)
        # 连接文件变化信号
        self.image_processor.file_changed.connect(self.on_file_changed)
        self.tag_checkboxes = []  # 存储标签复选框的引用
        self.current_image_name = None  # 记录当前选中的图片名称
        self.thumbnail_items = {}  # 存储文件列表项的引用
        # 添加标签统计相关属性
        self.selected_images = []  # 存储批量选中的图片
        self.tag_statistics = {}   # 存储标签统计信息
        # 添加预设标签列表
        self.preset_tags = []      # 存储预设标签
        # 添加主题相关属性
        self.current_theme = "light"  # 默认主题
        self.init_ui()
        # 启用拖拽功能
        self.setAcceptDrops(True)
        
    def init_ui(self):
        # 设置窗口标题和初始大小
        self.setWindowTitle('图片提示词打标器')
        self.setGeometry(
            PageSizeConfig.WINDOW_X, 
            PageSizeConfig.WINDOW_Y, 
            PageSizeConfig.WINDOW_WIDTH, 
            PageSizeConfig.WINDOW_HEIGHT
        )
        
        # 应用全局字体到主窗口
        self.setFont(GLOBAL_FONT)
        
        # 创建中央部件
        central_widget = QWidget()
        # 应用全局字体
        central_widget.setFont(GLOBAL_FONT)
        self.setCentralWidget(central_widget)
        
        # 使用标签页控件作为主界面容器
        self.tab_widget = QTabWidget()
        self.tab_widget.setFont(GLOBAL_FONT)
        
        # 创建主功能页面
        self.main_tab = QWidget()
        self.main_tab.setFont(GLOBAL_FONT)
        self.setup_main_tab()
        
        # 创建词频统计页面
        self.frequency_tab = QWidget()
        self.frequency_tab.setFont(GLOBAL_FONT)
        self.setup_frequency_tab()
        
        # 添加标签页
        self.tab_widget.addTab(self.main_tab, "主界面")
        self.tab_widget.addTab(self.frequency_tab, "词频统计")
        
        # 设置主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.addWidget(self.tab_widget)
        
        # 添加主题切换按钮
        self.theme_button = QPushButton('切换到深色主题')
        self.theme_button.clicked.connect(self.toggle_theme)
        self.theme_button.setFont(GLOBAL_FONT)
        self.theme_button.setMinimumHeight(50)
        main_layout.addWidget(self.theme_button)
        
        # 初始化时应用按钮样式
        self.apply_button_styles()
        
    def setup_main_tab(self):
        # 主布局使用分割器
        main_splitter = QSplitter(Qt.Horizontal)
        main_layout = QHBoxLayout(self.main_tab)
        main_layout.addWidget(main_splitter)
        
        # 左侧面板 - 文件列表区域
        left_panel = QFrame()
        # 应用全局字体
        left_panel.setFont(GLOBAL_FONT)
        left_layout = QVBoxLayout(left_panel)
        left_layout.addWidget(QLabel('图片文件列表'))
        
        # 文件列表控件配置
        self.file_list = QListWidget()
        # 缩略图大小设置
        self.file_list.setIconSize(QSize(
            PageSizeConfig.THUMBNAIL_WIDTH, 
            PageSizeConfig.THUMBNAIL_HEIGHT
        ))
        self.file_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.file_list.currentItemChanged.connect(self.on_file_selected)
        self.file_list.itemSelectionChanged.connect(self.on_files_selected)
        self.file_list.setViewMode(QListWidget.IconMode)
        self.file_list.setResizeMode(QListWidget.Adjust)
        # 添加拖拽功能和间距
        self.file_list.setDragDropMode(QAbstractItemView.InternalMove)
        # 文件项间距设置
        self.file_list.setSpacing(PageSizeConfig.ITEM_SPACING)
        self.file_list.setUniformItemSizes(False)  # 允许不同大小的项
        # 网格大小设置
        self.file_list.setGridSize(QSize(
            PageSizeConfig.GRID_WIDTH, 
            PageSizeConfig.GRID_HEIGHT
        ))
        self.file_list.setWordWrap(True)  # 允许文件名换行
        # 解决选中问题的关键设置
        self.file_list.setMouseTracking(False)  # 禁用鼠标跟踪以避免干扰点击事件
        self.file_list.setFocusPolicy(Qt.StrongFocus)  # 确保列表可以获取键盘焦点
        # 调整滚动步长，使鼠标滚轮滚动更平缓
        self.file_list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.file_list.verticalScrollBar().setSingleStep(30)
        # 启用按键事件
        self.file_list.keyPressEvent = self.file_list_key_press_event
        # 应用全局字体
        self.file_list.setFont(GLOBAL_FONT)
        left_layout.addWidget(self.file_list)
        
        # 添加统计信息显示区域
        self.stats_label = QLabel()
        self.stats_label.setWordWrap(True)
        self.stats_label.setStyleSheet("background-color: #f0f0f0; padding: 5px; border: 1px solid gray;")
        # 应用全局字体
        self.stats_label.setFont(GLOBAL_FONT)
        left_layout.addWidget(self.stats_label)
        
        # 导入按钮布局
        import_button_layout = QHBoxLayout()
        
        # 导入按钮
        self.import_button = QPushButton('新导入文件夹')
        self.import_button.setMinimumHeight(150)  # 设置最小高度
        self.import_button.clicked.connect(self.import_folder)
        # 应用全局字体
        self.import_button.setFont(GLOBAL_FONT)
        
        # 追加按钮
        self.append_button = QPushButton('追加文件夹')
        self.append_button.setMinimumHeight(150)
        self.append_button.clicked.connect(self.append_folder)
        # 应用全局字体
        self.append_button.setFont(GLOBAL_FONT)
        
        # 导出按钮
        self.export_button = QPushButton('导出重命名')
        self.export_button.setMinimumHeight(150)
        self.export_button.clicked.connect(self.export_renamed_files)
        # 应用全局字体
        self.export_button.setFont(GLOBAL_FONT)
        
        # 删除选中按钮
        self.delete_selected_button = QPushButton('删除选中')
        self.delete_selected_button.setMinimumHeight(150)
        self.delete_selected_button.clicked.connect(self.delete_selected_images)
        # 应用全局字体
        self.delete_selected_button.setFont(GLOBAL_FONT)
        
        import_button_layout.addWidget(self.import_button)
        import_button_layout.addWidget(self.append_button)
        import_button_layout.addWidget(self.export_button)
        import_button_layout.addWidget(self.delete_selected_button)
        
        left_layout.addLayout(import_button_layout)
        
        # 中间面板 - 图片预览和标签展示
        middle_panel = QFrame()
        # 应用全局字体
        middle_panel.setFont(GLOBAL_FONT)
        middle_layout = QVBoxLayout(middle_panel)
        
        # 使用垂直分割器来分离图片预览和标签展示区域
        middle_splitter = QSplitter(Qt.Vertical)
        
        # 图片预览标签
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        # 图片预览区域最小尺寸设置
        self.image_label.setMinimumSize(
            PageSizeConfig.IMAGE_PREVIEW_MIN_WIDTH,
            PageSizeConfig.IMAGE_PREVIEW_MIN_HEIGHT
        )
        self.image_label.setStyleSheet("border: 1px solid gray; background-color: #f0f0f0;")
        # 应用全局字体
        self.image_label.setFont(GLOBAL_FONT)
        # 将图片预览添加到分割器而不是直接添加到布局
        middle_splitter.addWidget(self.image_label)
        
        # 标签展示区域容器
        tag_display_panel = QWidget()
        # 应用全局字体
        tag_display_panel.setFont(GLOBAL_FONT)
        tag_display_layout = QVBoxLayout(tag_display_panel)
        
        # 标签显示区域
        label = QLabel('标签展示')
        label.setFont(GLOBAL_FONT)  # 应用全局字体
        tag_display_layout.addWidget(label)
        
        # 创建滚动区域用于标签展示
        self.tags_scroll_area = QScrollArea()
        self.tags_scroll_area.setWidgetResizable(True)
        self.tags_container = QWidget()
        # 应用全局字体
        self.tags_container.setFont(GLOBAL_FONT)
        self.tags_layout = QVBoxLayout(self.tags_container)
        self.tags_scroll_area.setWidget(self.tags_container)
        # 应用全局字体
        self.tags_scroll_area.setFont(GLOBAL_FONT)

        tag_display_layout.addWidget(self.tags_scroll_area)
        
        # 添加AI提示词编辑区域
        ai_prompt_label = QLabel('AI提示词设置:')
        ai_prompt_label.setFont(GLOBAL_FONT)
        tag_display_layout.addWidget(ai_prompt_label)
        
        self.ai_prompt_input = QTextEdit()
        self.ai_prompt_input.setFont(GLOBAL_FONT)
        self.ai_prompt_input.setMaximumHeight(120)
        self.ai_prompt_input.setPlaceholderText("在此输入给AI的指令提示词，例如：以提示词格式详细描述画面。请用中文回答，尽量详细、连贯。只输出提示词本身，不要输出其他内容。")
        # 从配置文件读取默认提示词
        default_prompt = '以提示词格式详细描述画面。请用中文回答，尽量详细、连贯。只输出提示词本身，不要输出其他内容。'
        config_path = os.path.join(os.path.dirname(__file__), 'code', 'config.ini')
        if os.path.exists(config_path):
            import configparser
            config = configparser.ConfigParser()
            config.read(config_path, encoding='utf-8')
            if 'PROMPTS' in config:
                default_prompt = config.get('PROMPTS', 'image_prompt', fallback=default_prompt)
        self.ai_prompt_input.setPlainText(default_prompt)
        tag_display_layout.addWidget(self.ai_prompt_input)
        
        # 添加生成提示词按钮
        self.generate_caption_button = QPushButton("生成提示词")
        self.generate_caption_button.clicked.connect(self.generate_caption_for_selected)
        self.generate_caption_button.setFont(GLOBAL_FONT)
        tag_display_layout.addWidget(self.generate_caption_button)
        
        # 将标签展示区域添加到分割器
        middle_splitter.addWidget(tag_display_panel)
        
        # 设置分割器的初始大小比例
        middle_splitter.setSizes(PageSizeConfig.MIDDLE_SPLITTER_SIZES)
        
        # 将分割器添加到中间面板布局
        middle_layout.addWidget(QLabel('图片预览'))
        middle_layout.addWidget(middle_splitter)
        
        # 添加前进后退按钮
        navigation_layout = QHBoxLayout()
        self.prev_button = QPushButton('后退 ←')
        self.prev_button.clicked.connect(self.select_prev_image)
        self.prev_button.setFont(GLOBAL_FONT)
        self.prev_button.setMinimumHeight(150)  # 设置最小高度
        self.next_button = QPushButton('前进 →')
        self.next_button.clicked.connect(self.select_next_image)
        self.next_button.setFont(GLOBAL_FONT)
        self.next_button.setMinimumHeight(150)  # 设置最小高度
        navigation_layout.addWidget(self.prev_button)
        navigation_layout.addWidget(self.next_button)
        
        # 设置按钮之间的间距
        navigation_layout.setSpacing(10)
        
        middle_layout.addLayout(navigation_layout)
        
        # 右侧面板 - 批量操作和统计
        right_panel = QFrame()
        # 最小宽度设置
        right_panel.setMinimumWidth(PageSizeConfig.RIGHT_PANEL_MIN_WIDTH)
        # 应用全局字体
        right_panel.setFont(GLOBAL_FONT)
        right_layout = QVBoxLayout(right_panel)
        
        # 批量操作区域
        batch_group = QGroupBox("批量操作")
        # 应用全局字体
        batch_group.setFont(GLOBAL_FONT)
        batch_layout = QVBoxLayout(batch_group)
        
        self.select_all_button = QPushButton("全选")
        self.select_all_button.clicked.connect(self.select_all_images)
        # 应用全局字体
        self.select_all_button.setFont(GLOBAL_FONT)
        self.deselect_all_button = QPushButton("取消全选")
        self.deselect_all_button.clicked.connect(self.deselect_all_images)
        # 应用全局字体
        self.deselect_all_button.setFont(GLOBAL_FONT)
        
        batch_actions_layout = QHBoxLayout()
        batch_actions_layout.addWidget(self.select_all_button)
        batch_actions_layout.addWidget(self.deselect_all_button)
        batch_layout.addLayout(batch_actions_layout)
        
        # 批量标签操作
        self.batch_tag_input2 = QLineEdit()
        self.batch_tag_input2.setPlaceholderText("输入要批量添加的标签...")
        # 应用全局字体
        self.batch_tag_input2.setFont(GLOBAL_FONT)
        
        # 添加"添加到开头"选项
        self.add_to_front_checkbox = QCheckBox("添加到标签列表开头")
        self.add_to_front_checkbox.setChecked(False)
        self.add_to_front_checkbox.setFont(GLOBAL_FONT)
        
        self.add_tag_to_all_btn = QPushButton("添加到所有选中图片")
        self.add_tag_to_all_btn.clicked.connect(self.add_tag_to_all_selected)
        # 应用全局字体
        self.add_tag_to_all_btn.setFont(GLOBAL_FONT)
        
        # 添加移动标签到开头的按钮
        self.move_tag_to_front_btn = QPushButton("将选中标签移到开头")
        self.move_tag_to_front_btn.clicked.connect(self.move_selected_tags_to_front)
        # 应用全局字体
        self.move_tag_to_front_btn.setFont(GLOBAL_FONT)
        
        batch_layout.addWidget(QLabel("批量添加标签:"))
        batch_layout.addWidget(self.batch_tag_input2)
        batch_layout.addWidget(self.add_to_front_checkbox)  # 添加选项
        batch_layout.addWidget(self.add_tag_to_all_btn)
        batch_layout.addWidget(self.move_tag_to_front_btn)
        
        # 预设标签区域
        preset_group = QGroupBox("预设标签")
        preset_group.setFont(GLOBAL_FONT)
        preset_layout = QVBoxLayout(preset_group)
        
        # 预设标签输入区域
        self.preset_tag_input = QLineEdit()
        self.preset_tag_input.setPlaceholderText("输入预设标签，用逗号分隔")
        self.preset_tag_input.setFont(GLOBAL_FONT)
        
        # 预设标签保存按钮
        save_preset_btn = QPushButton("保存预设标签")
        save_preset_btn.clicked.connect(self.save_preset_tags)
        save_preset_btn.setFont(GLOBAL_FONT)
        
        # 预设标签显示区域
        self.preset_tags_container = QWidget()
        self.preset_tags_layout = QGridLayout(self.preset_tags_container)  # 改为网格布局
        self.preset_tags_layout.setSpacing(5)
        self.preset_tags_layout.setAlignment(Qt.AlignLeft)
        
        preset_scroll = QScrollArea()
        preset_scroll.setWidgetResizable(True)
        preset_scroll.setWidget(self.preset_tags_container)
        # 预设标签区域高度设置
        preset_scroll.setMaximumHeight(PageSizeConfig.PRESET_TAGS_MAX_HEIGHT)
        preset_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # 禁用水平滚动
        preset_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)  # 启用垂直滚动
        
        # 设置预设标签容器的样式，确保标签文字为黑色
        self.preset_tags_container.setStyleSheet("color: black;")
        
        preset_layout.addWidget(self.preset_tag_input)
        preset_layout.addWidget(save_preset_btn)
        preset_layout.addWidget(QLabel("点击标签添加到当前图片:"))
        preset_layout.addWidget(preset_scroll)
        
        # 标签统计区域
        self.stats_tree = QTreeWidget()
        self.stats_tree.setHeaderLabels(["标签", "出现次数", "占比"])

        # 调整列宽以更好地显示内容
        self.stats_tree.setColumnWidth(0, 300)  # 标签列
        self.stats_tree.setColumnWidth(1, 200)  # 出现次数列
        self.stats_tree.setColumnWidth(2, 100)  # 占比列
        self.stats_tree.setSelectionMode(QAbstractItemView.SingleSelection)
        # 应用全局字体
        self.stats_tree.setFont(GLOBAL_FONT)
        
        # 设置表头样式，固定文字为黑色
        self.stats_tree.header().setStyleSheet("color: black;")
        
        stats_buttons_layout = QHBoxLayout()
        self.delete_selected_tag_btn = QPushButton("删除选中标签")
        self.modify_selected_tag_btn = QPushButton("修改选中标签")
        self.delete_selected_tag_btn.clicked.connect(self.delete_selected_tag_from_all)
        self.modify_selected_tag_btn.clicked.connect(self.modify_selected_tag_for_all)
        # 应用全局字体
        self.delete_selected_tag_btn.setFont(GLOBAL_FONT)
        self.modify_selected_tag_btn.setFont(GLOBAL_FONT)
        stats_buttons_layout.addWidget(self.delete_selected_tag_btn)
        stats_buttons_layout.addWidget(self.modify_selected_tag_btn)
        
        batch_layout.addWidget(preset_group)  # 添加预设标签组到批量操作区域
        batch_layout.addWidget(QLabel("标签统计:"))
        batch_layout.addWidget(self.stats_tree)
        batch_layout.addLayout(stats_buttons_layout)
        right_layout.addWidget(batch_group)
        
        # 添加面板到分割器
        main_splitter.addWidget(left_panel)
        main_splitter.addWidget(middle_panel)
        main_splitter.addWidget(right_panel)
        # 设置主分割器的初始大小比例
        main_splitter.setSizes(PageSizeConfig.MAIN_SPLITTER_SIZES)
        
    def setup_frequency_tab(self):
        # 在词频统计标签页中嵌入词频统计功能
        layout = QVBoxLayout(self.frequency_tab)
        
        # 创建一个容器来嵌入词频统计界面
        try:
            # 导入词频统计模块
            import sys
            sys.path.append(os.path.dirname(os.path.abspath(__file__)))
            from tool.词频统计.词频统计 import LabelAnalyzer
            import tkinter as tk
            from tkinter import ttk
            
            # 创建一个特殊的tkinter嵌入窗口
            # 由于Qt和Tkinter的GUI系统不兼容，我们采用另一种方式实现
            # 这里创建一个提示标签，指导用户如何使用词频统计功能
            info_label = QLabel("词频统计功能说明：\n\n"
                               "1. 请确保您的数据文件夹中包含图片文件及其对应的.txt标签文件\n"
                               "2. 图片文件和标签文件应具有相同的文件名（扩展名除外）\n"
                               "3. 点击下方按钮打开独立的词频统计工具窗口\n\n"
                               "注意：此功能将在新窗口中打开，不会影响当前界面的操作")
            info_label.setWordWrap(True)
            info_label.setAlignment(Qt.AlignCenter)
            info_label.setStyleSheet("font-size: 16px; padding: 20px;")
            layout.addWidget(info_label)
            
            # 添加打开词频统计工具的按钮
            open_freq_btn = QPushButton("打开词频统计工具")
            open_freq_btn.setFont(GLOBAL_FONT)
            open_freq_btn.clicked.connect(self.open_frequency_analyzer)
            layout.addWidget(open_freq_btn)
            
            # 添加占位符以填充布局
            layout.addStretch()
            
        except ImportError as e:
            error_label = QLabel(f"无法加载词频统计模块：{str(e)}\n\n"
                                "请确保词频统计.py文件位于正确位置")
            error_label.setWordWrap(True)
            error_label.setAlignment(Qt.AlignCenter)
            error_label.setStyleSheet("color: red; font-size: 16px; padding: 20px;")
            layout.addWidget(error_label)
            
    def open_frequency_analyzer(self):
        """打开词频统计分析工具"""
        try:
            import tkinter as tk
            from tool.词频统计.词频统计 import LabelAnalyzer
            
            # 创建一个新的tkinter根窗口
            freq_root = tk.Tk()
            freq_app = LabelAnalyzer(freq_root)
            freq_root.mainloop()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法打开词频统计工具：{str(e)}")

    # 添加文件变化处理方法
    def on_file_changed(self, action, image_name):
        """处理文件变化事件"""
        if action == 'created':
            # 新文件创建，添加到文件列表
            self.add_image_to_list(image_name)
            self.update_statistics()
        elif action == 'tag_updated':
            # 标签文件更新，刷新当前显示的图片（如果是当前选中的）
            if self.current_image_name == image_name:
                self.refresh_current_view()
            self.update_statistics()

    def add_image_to_list(self, image_name):
        """添加单个图片到文件列表"""
        if image_name not in self.thumbnail_items:
            # 创建新的列表项
            item = QListWidgetItem()
            item.setText(image_name)
            # 异步加载缩略图
            self.image_processor.load_thumbnail_async(image_name)
            self.file_list.addItem(item)
            self.thumbnail_items[image_name] = item

    def dragEnterEvent(self, event):
        """
        拖拽进入事件处理
        """
        if event.mimeData().hasUrls():
            # 检查是否是文件夹
            urls = event.mimeData().urls()
            if len(urls) == 1:
                url = urls[0]
                if url.isLocalFile():
                    path = url.toLocalFile()
                    if os.path.isdir(path):
                        event.acceptProposedAction()
                        return
        event.ignore()

    def dropEvent(self, event):
        """
        拖拽放下事件处理
        """
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if len(urls) == 1:
                url = urls[0]
                if url.isLocalFile():
                    path = url.toLocalFile()
                    if os.path.isdir(path):
                        # 处理文件夹拖拽
                        self.handle_folder_drop(path)
                        event.acceptProposedAction()
                        return
        event.ignore()

    def handle_folder_drop(self, folder_path):
        """
        处理文件夹拖拽事件
        """
        try:
            self.image_processor.load_folder(folder_path)
            self.update_file_list()
            self.update_statistics()  # 更新统计信息
            QMessageBox.information(self, "成功", f"成功导入 {len(self.image_processor.images)} 张图片")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导入失败: {str(e)}")

    def file_list_key_press_event(self, event):
        """处理文件列表的按键事件"""
        if event.key() == Qt.Key_Delete:
            # 如果按下的是Delete键，则触发删除选中图片的功能
            self.delete_selected_images()
        else:
            # 否则调用原始的按键处理方法
            QListWidget.keyPressEvent(self.file_list, event)

    def select_prev_image(self):
        """选中前一张图片"""
        current_row = self.file_list.currentRow()
        if current_row > 0:  # 确保不是第一张图片
            self.file_list.setCurrentRow(current_row - 1)

    def select_next_image(self):
        """选中下一张图片"""
        current_row = self.file_list.currentRow()
        if current_row < self.file_list.count() - 1:  # 确保不是最后一张图片
            self.file_list.setCurrentRow(current_row + 1)

    def toggle_theme(self):
        """切换主题"""
        if self.current_theme == "light":
            # 切换到深色主题
            self.setStyleSheet(DARK_THEME)
            self.theme_button.setText('切换到浅色主题')
            self.current_theme = "dark"
        else:
            # 切换到浅色主题
            self.setStyleSheet(LIGHT_THEME)
            self.theme_button.setText('切换到深色主题')
            self.current_theme = "light"
            
        # 重新应用按钮样式
        self.apply_button_styles()
        
        # 更新统计标签的样式以匹配当前主题
        if self.current_theme == "dark":
            self.stats_label.setStyleSheet(STATS_LABEL_STYLE_DARK)
            self.image_label.setStyleSheet(IMAGE_LABEL_STYLE_DARK)
            self.tags_scroll_area.setStyleSheet(STATS_LABEL_STYLE_DARK)
        else:
            self.stats_label.setStyleSheet(STATS_LABEL_STYLE_LIGHT)
            self.image_label.setStyleSheet(IMAGE_LABEL_STYLE_LIGHT)
            self.tags_scroll_area.setStyleSheet(STATS_LABEL_STYLE_LIGHT)
            
    def apply_button_styles(self):
        """应用按钮样式"""
        buttons = [
            self.import_button, self.append_button, self.export_button, 
            self.delete_selected_button, self.generate_caption_button,
            self.prev_button, self.next_button, self.select_all_button,
            self.deselect_all_button, self.add_tag_to_all_btn,
            self.move_tag_to_front_btn, self.delete_selected_tag_btn,
            self.modify_selected_tag_btn
        ]
        
        for button in buttons:
            button.setStyleSheet(BUTTON_STYLE_NORMAL + 
                                BUTTON_STYLE_HOVER + 
                                BUTTON_STYLE_PRESSED)
        
        # 为重要按钮应用特殊样式
        important_buttons = [self.delete_selected_button]
        for button in important_buttons:
            button.setStyleSheet(BUTTON_STYLE_IMPORTANT + 
                                BUTTON_STYLE_HOVER + 
                                BUTTON_STYLE_PRESSED)
        
        # 为导航按钮应用特殊样式
        nav_buttons = [self.prev_button, self.next_button]
        for button in nav_buttons:
            button.setStyleSheet(BUTTON_STYLE_NAVIGATION + 
                                BUTTON_STYLE_HOVER + 
                                BUTTON_STYLE_PRESSED)
