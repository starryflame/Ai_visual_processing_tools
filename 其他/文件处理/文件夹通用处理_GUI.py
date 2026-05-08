#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件夹通用处理工具 - PyQt5 图形化界面版本
功能：拆分大文件夹、扁平化结构、打乱图片名称
"""

import os
import shutil
from pathlib import Path
import random
import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTabWidget, QTextEdit,
    QFileDialog, QMessageBox, QProgressBar, QGroupBox, QSpinBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal


class ProcessingWorker(QThread):
    """后台处理线程，避免界面卡死"""
    progress_signal = pyqtSignal(int, str)  # 进度百分比，日志信息
    finished_signal = pyqtSignal(str)       # 完成信号

    def __init__(self, operation, source_folder=None, target_folder=None, max_files=1000, folder_name=None):
        super().__init__()
        self.operation = operation
        self.source_folder = source_folder
        self.target_folder = target_folder
        self.max_files = max_files
        self.folder_name = folder_name
        self.cancelled = False

    def run(self):
        if self.operation == "split":
            self.process_split()
        elif self.operation == "flatten":
            self.process_flatten()
        elif self.operation == "shuffle":
            self.process_shuffle()
        elif self.operation == "extract":
            self.process_extract()

    def cancel(self):
        self.cancelled = True

    def process_split(self):
        """拆分大文件夹 - 尽量保持同名文件的配对关系"""
        source_path = Path(self.source_folder)
        
        if not source_path.exists():
            self.finished_signal.emit(f"错误：源文件夹 {self.source_folder} 不存在")
            return
        
        self.progress_signal.emit(5, "正在扫描所有文件...")
        
        # 支持的媒体和标签文件扩展名
        media_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.svg', 
                            '.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv', '.webm', '.m4v'}
        label_extensions = {'.txt'}
        
        # 收集所有需要处理的文件
        all_files = [f for f in source_path.iterdir() 
                     if f.is_file() and (f.suffix.lower() in media_extensions or f.suffix.lower() in label_extensions)]
        
        if not all_files:
            self.finished_signal.emit("错误：源文件夹中没有媒体或标签文件")
            return
        
        # 按文件名分组（同名不同格式的文件归为一组）
        file_groups = {}
        for file_path in all_files:
            base_name = file_path.stem
            if base_name not in file_groups:
                file_groups[base_name] = []
            file_groups[base_name].append(file_path)
        
        self.progress_signal.emit(10, f"找到 {len(file_groups)} 组文件，共 {len(all_files)} 个文件")
        
        # 将每组文件视为一个整体进行拆分
        group_list = list(file_groups.keys())
        random.shuffle(group_list)  # 打乱分组顺序
        
        folder_count = 0
        processed_count = 0
        current_subfolder = None
        subfolder_file_count = 0
        
        for base_name in group_list:
            if self.cancelled:
                self.finished_signal.emit("操作已取消")
                return
            
            files_in_group = file_groups[base_name]
            
            # 检查如果添加当前组是否会超过最大文件数，如果是则先创建新文件夹
            needs_new_folder = False
            if current_subfolder is None:
                needs_new_folder = True
            elif subfolder_file_count + len(files_in_group) > self.max_files:
                needs_new_folder = True
            
            # 创建第一个子文件夹或当达到最大文件数时创建新文件夹
            if needs_new_folder:
                folder_count += 1
                subfolder_name = f"{source_path.name}_part_{folder_count}"
                current_subfolder = source_path / subfolder_name
                current_subfolder.mkdir(exist_ok=True)
                self.progress_signal.emit(
                    int(10 + (processed_count / len(all_files)) * 20),
                    f"创建文件夹：{subfolder_name}"
                )
                subfolder_file_count = 0
            
            for file_path in files_in_group:
                destination = current_subfolder / file_path.name
                shutil.move(str(file_path), str(destination))
            
            subfolder_file_count += len(files_in_group)
            processed_count += len(files_in_group)
            
            if processed_count % 100 == 0:
                progress = int(30 + (processed_count / len(all_files)) * 40)
                self.progress_signal.emit(progress, f"已处理 {processed_count} 个文件（{subfolder_file_count}/{self.max_files}）")
        
        total_progress = int(70 + (folder_count / max(folder_count, 1)) * 30)
        self.progress_signal.emit(total_progress, f"拆分完成，共创建 {folder_count} 个子文件夹，处理 {processed_count} 个文件")
        self.finished_signal.emit(f"成功！已创建 {folder_count} 个子文件夹，处理了 {processed_count} 个文件。同名不同格式的文件已尽量保持配对关系。")

    def process_flatten(self):
        """扁平化文件夹结构"""
        source_path = Path(self.source_folder)
        
        if not source_path.exists():
            self.finished_signal.emit(f"错误：源文件夹 {self.source_folder} 不存在")
            return
        
        self.progress_signal.emit(5, "正在扫描所有文件...")
        
        all_files = []
        for root, dirs, files in os.walk(source_path):
            if self.cancelled:
                self.finished_signal.emit("操作已取消")
                return
            
            for file in files:
                file_path = Path(root) / file
                if file_path.parent != source_path:
                    all_files.append(file_path)
        
        if not all_files:
            self.finished_signal.emit("成功：没有需要移动的文件")
            return
        
        self.progress_signal.emit(10, f"找到 {len(all_files)} 个文件，开始扁平化...")
        
        moved_count = 0
        for file_path in all_files:
            if self.cancelled:
                self.finished_signal.emit("操作已取消")
                return
            
            # 目标路径：直接放到源文件夹根目录
            target_name = file_path.name
            destination = source_path / target_name
            
            counter = 1
            while destination.exists():
                name_without_ext = Path(target_name).stem
                ext = Path(target_name).suffix
                new_name = f"{name_without_ext}_{counter}{ext}"
                destination = source_path / new_name
                counter += 1
            
            shutil.move(str(file_path), str(destination))
            moved_count += 1
            
            if moved_count % 100 == 0:
                progress = int(20 + (moved_count / len(all_files)) * 50)
                self.progress_signal.emit(progress, f"已移动 {moved_count} 个文件")
        
        # 删除空文件夹（不显示进度，避免干扰）
        for item in source_path.iterdir():
            if item.is_dir():
                try:
                    item.rmdir()
                except OSError:
                    pass
        
        # 确保进度达到 100%
        self.progress_signal.emit(100, f"扁平化完成，共移动 {moved_count} 个文件")
        self.finished_signal.emit(f"成功！已移动 {moved_count} 个文件并清理空文件夹")

    def process_shuffle(self):
        """打乱图片/视频文件名，保持同名不同格式文件的配对关系"""
        source_path = Path(self.source_folder)
        
        if not source_path.exists():
            self.finished_signal.emit(f"错误：源文件夹 {self.source_folder} 不存在")
            return
        
        # 支持的媒体文件扩展名
        media_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.svg', 
                            '.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv', '.webm', '.m4v'}
        # 标签文件扩展名
        label_extensions = {'.txt'}
        
        self.progress_signal.emit(5, "正在扫描所有文件...")
        
        # 收集所有需要处理的文件（媒体 + 标签）
        all_files = [f for f in source_path.iterdir() 
                     if f.is_file() and (f.suffix.lower() in media_extensions or f.suffix.lower() in label_extensions)]
        
        if not all_files:
            self.finished_signal.emit("错误：源文件夹中没有媒体或标签文件")
            return
        
        # 按文件名分组（同名不同格式的文件归为一组）
        file_groups = {}
        for file_path in all_files:
            base_name = file_path.stem  # 不带扩展名的文件名
            if base_name not in file_groups:
                file_groups[base_name] = []
            file_groups[base_name].append(file_path)
        
        self.progress_signal.emit(10, f"找到 {len(file_groups)} 组文件，共 {len(all_files)} 个文件")
        
        # 生成临时名称 - 每组文件分别处理
        group_temp_names = {}
        for base_name, files in file_groups.items():
            if self.cancelled:
                self.finished_signal.emit("操作已取消")
                return
            
            temp_names_for_group = []
            for i, file_path in enumerate(files):
                temp_name = f"temp_{base_name}_{i:04d}{file_path.suffix}"
                temp_names_for_group.append((file_path, temp_name))
                
                temp_path = source_path / temp_name
                file_path.rename(temp_path)
            
            group_temp_names[base_name] = temp_names_for_group
        
        self.progress_signal.emit(50, "文件已重命名为临时名称，正在打乱...")
        
        # 生成新的文件名列表并打乱
        new_base_names = list(file_groups.keys())
        random.shuffle(new_base_names)
        
        # 将新名称分配给各组的临时文件
        for old_base_name, files in file_groups.items():
            if self.cancelled:
                self.finished_signal.emit("操作已取消")
                return
            
            new_base = new_base_names.pop(0)
            
            # 按后缀排序，确保相同位置的文件使用相同的扩展名
            sorted_files = sorted(files, key=lambda x: x.suffix.lower())
            
            for i, file_path in enumerate(sorted_files):
                if self.cancelled:
                    self.finished_signal.emit("操作已取消")
                    return
                
                temp_name = group_temp_names[old_base_name][i][1]
                new_name = f"{new_base}{file_path.suffix}"
                
                temp_path = source_path / temp_name
                final_path = source_path / new_name
                temp_path.rename(final_path)
        
        self.progress_signal.emit(95, "文件重命名完成")
        self.finished_signal.emit(f"成功！已打乱 {len(file_groups)} 组文件的名称，共处理 {len(all_files)} 个文件。同名不同格式的文件已保持配对关系。")

    def process_extract(self):
        """按名称提取所有同名文件夹并复制到目标目录"""
        source_path = Path(self.source_folder)
        target_path = Path(self.target_folder)
        folder_name = self.folder_name

        if not source_path.exists():
            self.finished_signal.emit(f"错误：源文件夹 {self.source_folder} 不存在")
            return

        if not target_path.exists():
            target_path.mkdir(parents=True, exist_ok=True)

        self.progress_signal.emit(5, f"正在扫描所有名为「{folder_name}」的文件夹...")

        # 查找所有匹配的文件夹
        matched_folders = []
        for root, dirs, _files in os.walk(source_path):
            if self.cancelled:
                self.finished_signal.emit("操作已取消")
                return
            for d in dirs:
                if d == folder_name:
                    matched_folders.append(Path(root) / d)

        if not matched_folders:
            self.finished_signal.emit(f"没有找到名为「{folder_name}」的文件夹")
            return

        self.progress_signal.emit(10, f"找到 {len(matched_folders)} 个匹配的文件夹，开始复制...")

        copied_count = 0
        for i, src_folder in enumerate(matched_folders):
            if self.cancelled:
                self.finished_signal.emit("操作已取消")
                return

            # 目标文件夹名带序号
            dest_folder = target_path / f"{folder_name}_{i + 1}"

            # 如果目标已存在，递增序号
            counter = i + 1
            while dest_folder.exists():
                counter += 1
                dest_folder = target_path / f"{folder_name}_{counter}"

            shutil.copytree(str(src_folder), str(dest_folder))
            copied_count += 1

            if copied_count % 10 == 0:
                progress = int(20 + (copied_count / len(matched_folders)) * 70)
                self.progress_signal.emit(progress, f"已复制 {copied_count}/{len(matched_folders)} 个文件夹")

        self.progress_signal.emit(100, f"提取完成，共复制 {copied_count} 个文件夹")
        self.finished_signal.emit(f"成功！已将 {copied_count} 个名为「{folder_name}」的文件夹复制到目标目录，已自动添加序号。")


class FolderProcessorGUI(QMainWindow):
    """主窗口类"""
    
    def __init__(self):
        super().__init__()
        self.worker = None
        self.init_ui()

    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("文件夹通用处理工具")
        self.setMinimumSize(1640, 1600)
        
        # 设置应用程序全局字体 - 超大字号
        app_font = QApplication.font()
        app_font.setPointSize(20)  # 全局字体 20pt
        QApplication.setFont(app_font)
        
        # 主容器和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 标题 - 超大字号
        from PyQt5.QtGui import QFont
        title_label = QLabel("📁 文件夹通用处理工具")
        font = QFont()
        font.setPointSize(36)  # 标题 36pt
        font.setBold(True)
        title_label.setFont(font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""font-size: 40px; font-weight: bold; padding: 20px; background-color: #f0f0f0; border-radius: 15px;""")
        main_layout.addWidget(title_label)
        
        # 选项卡控件
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 3px solid #ccc; border-radius: 10px; }
            QTabBar::tab { 
                background-color: #e0e0e0; 
                padding: 20px 40px; 
                margin-right: 6px;
                font-size: 22px;
                font-weight: bold;
            }
            QTabBar::tab:selected { 
                background-color: #fff; 
                border-bottom: 5px solid #2196F3;
            }
        """)
        main_layout.addWidget(self.tabs)
        
        # 创建各个功能标签页
        self.create_split_tab()
        self.create_flatten_tab()
        self.create_extract_tab()
        self.create_shuffle_tab()
        
        # 进度条和日志区域
        progress_group = QGroupBox("📊 进度 & 日志")
        progress_group.setStyleSheet("""
            QGroupBox { 
                font-weight: bold; 
                font-size: 22px;
                margin-top: 15px;
                padding-top: 20px;
                border: 4px solid #ccc;
                border-radius: 12px;
            }
        """)
        progress_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 4px solid #666;
                border-radius: 15px;
                text-align: center;
                font-size: 22px;
                background-color: #e0e0e0;
                height: 50px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 12px;
            }
        """)
        progress_layout.addWidget(self.progress_bar)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(300)
        self.log_text.setStyleSheet("""
            QTextEdit {
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 18px;
                background-color: #1e1e1e;
                color: #d4d4d4;
                border-radius: 10px;
                padding: 12px;
            }
        """)
        progress_layout.addWidget(self.log_text)
        
        progress_group.setLayout(progress_layout)
        main_layout.addWidget(progress_group)
        
        # 按钮区域 - 超大按钮
        button_layout = QHBoxLayout()
        
        self.clear_log_btn = QPushButton("🗑️ 清空日志")
        self.clear_log_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-weight: bold;
                padding: 20px 40px;
                border-radius: 15px;
                font-size: 22px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        self.clear_log_btn.clicked.connect(self.clear_log)
        button_layout.addWidget(self.clear_log_btn)
        
        self.cancel_btn = QPushButton("❌ 取消操作")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff9800;
                color: white;
                font-weight: bold;
                padding: 20px 40px;
                border-radius: 15px;
                font-size: 22px;
            }
            QPushButton:hover {
                background-color: #f57c00;
            }
        """)
        self.cancel_btn.clicked.connect(self.cancel_operation)
        self.cancel_btn.setEnabled(False)
        button_layout.addWidget(self.cancel_btn)
        
        main_layout.addLayout(button_layout)

    def create_split_tab(self):
        """创建拆分大文件夹标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 源文件夹选择 - GroupBox 标题 22px
        source_group = QGroupBox("📁 源文件夹")
        source_group.setStyleSheet("""
            QGroupBox { 
                font-weight: bold; 
                font-size: 22px;
                margin-top: 15px;
                padding-top: 20px;
                border: 4px solid #ccc;
                border-radius: 12px;
            }
        """)
        source_layout = QHBoxLayout()
        
        self.split_source_path = QLineEdit()
        self.split_source_path.setPlaceholderText("选择或输入源文件夹路径...")
        self.split_source_path.setStyleSheet("""
            QLineEdit {
                padding: 18px;
                font-size: 20px;
                border: 4px solid #ccc;
                border-radius: 10px;
            }
        """)
        browse_btn = QPushButton("浏览...")
        browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                padding: 18px 25px;
                border-radius: 10px;
                font-size: 20px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        browse_btn.clicked.connect(lambda: self.browse_folder(self.split_source_path))
        
        source_layout.addWidget(QLabel("源文件夹："))
        source_layout.addWidget(self.split_source_path)
        source_layout.addWidget(browse_btn)
        source_group.setLayout(source_layout)
        layout.addWidget(source_group)
        
        # 参数设置 - GroupBox 标题 22px
        params_group = QGroupBox("⚙️ 拆分参数")
        params_group.setStyleSheet("""
            QGroupBox { 
                font-weight: bold; 
                font-size: 22px;
                margin-top: 15px;
                padding-top: 20px;
                border: 4px solid #ccc;
                border-radius: 12px;
            }
        """)
        params_layout = QHBoxLayout()
        
        self.max_files_spin = QSpinBox()
        self.max_files_spin.setRange(10, 100000)
        self.max_files_spin.setValue(1000)
        self.max_files_spin.setSuffix(" 个文件/子文件夹")
        self.max_files_spin.setStyleSheet("""
            QSpinBox {
                padding: 15px;
                font-size: 20px;
                border: 4px solid #ccc;
                border-radius: 10px;
            }
        """)
        
        params_layout.addWidget(QLabel("每子文件夹最大文件数："))
        params_layout.addWidget(self.max_files_spin)
        params_group.setLayout(params_layout)
        layout.addWidget(params_group)
        
        # 执行按钮 - 超大按钮
        exec_btn = QPushButton("▶️ 开始拆分")
        exec_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 25px;
                border-radius: 15px;
                font-size: 28px;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
        """)
        exec_btn.clicked.connect(self.start_split)
        layout.addWidget(exec_btn)
        
        self.tabs.addTab(tab, "1. 拆分大文件夹")

    def create_flatten_tab(self):
        """创建扁平化标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 源文件夹选择 - GroupBox 标题 22px
        source_group = QGroupBox("📁 源文件夹")
        source_group.setStyleSheet("""
            QGroupBox { 
                font-weight: bold; 
                font-size: 22px;
                margin-top: 15px;
                padding-top: 20px;
                border: 4px solid #ccc;
                border-radius: 12px;
            }
        """)
        source_layout = QHBoxLayout()
        
        self.flatten_source_path = QLineEdit()
        self.flatten_source_path.setPlaceholderText("选择或输入要扁平化的文件夹路径...")
        self.flatten_source_path.setStyleSheet("""
            QLineEdit {
                padding: 18px;
                font-size: 20px;
                border: 4px solid #ccc;
                border-radius: 10px;
            }
        """)
        browse_btn = QPushButton("浏览...")
        browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                padding: 18px 25px;
                border-radius: 10px;
                font-size: 20px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        browse_btn.clicked.connect(lambda: self.browse_folder(self.flatten_source_path))
        
        source_layout.addWidget(QLabel("源文件夹："))
        source_layout.addWidget(self.flatten_source_path)
        source_layout.addWidget(browse_btn)
        source_group.setLayout(source_layout)
        layout.addWidget(source_group)
        
        # 执行按钮 - 超大按钮
        exec_btn = QPushButton("▶️ 开始扁平化")
        exec_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                padding: 25px;
                border-radius: 15px;
                font-size: 28px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        exec_btn.clicked.connect(self.start_flatten)
        layout.addWidget(exec_btn)
        
        self.tabs.addTab(tab, "2. 扁平化文件夹结构")

    def create_extract_tab(self):
        """创建按名称提取文件夹标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 源文件夹选择
        source_group = QGroupBox("📁 源文件夹")
        source_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 22px;
                margin-top: 15px;
                padding-top: 20px;
                border: 4px solid #ccc;
                border-radius: 12px;
            }
        """)
        source_layout = QHBoxLayout()

        self.extract_source_path = QLineEdit()
        self.extract_source_path.setPlaceholderText("选择或输入要扫描的大文件夹路径...")
        self.extract_source_path.setStyleSheet("""
            QLineEdit {
                padding: 18px;
                font-size: 20px;
                border: 4px solid #ccc;
                border-radius: 10px;
            }
        """)
        browse_btn = QPushButton("浏览...")
        browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                padding: 18px 25px;
                border-radius: 10px;
                font-size: 20px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        browse_btn.clicked.connect(lambda: self.browse_folder(self.extract_source_path))

        source_layout.addWidget(QLabel("源文件夹："))
        source_layout.addWidget(self.extract_source_path)
        source_layout.addWidget(browse_btn)
        source_group.setLayout(source_layout)
        layout.addWidget(source_group)

        # 文件夹名称
        name_group = QGroupBox("🏷️ 要提取的文件夹名称")
        name_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 22px;
                margin-top: 15px;
                padding-top: 20px;
                border: 4px solid #ccc;
                border-radius: 12px;
            }
        """)
        name_layout = QHBoxLayout()

        self.extract_folder_name = QLineEdit()
        self.extract_folder_name.setPlaceholderText("输入要提取的文件夹名称，例如：labels")
        self.extract_folder_name.setStyleSheet("""
            QLineEdit {
                padding: 18px;
                font-size: 20px;
                border: 4px solid #ccc;
                border-radius: 10px;
            }
        """)
        name_layout.addWidget(QLabel("文件夹名："))
        name_layout.addWidget(self.extract_folder_name)
        name_group.setLayout(name_layout)
        layout.addWidget(name_group)

        # 目标文件夹选择
        target_group = QGroupBox("📂 目标文件夹")
        target_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 22px;
                margin-top: 15px;
                padding-top: 20px;
                border: 4px solid #ccc;
                border-radius: 12px;
            }
        """)
        target_layout = QHBoxLayout()

        self.extract_target_path = QLineEdit()
        self.extract_target_path.setPlaceholderText("选择或输入复制目标文件夹路径（不存在将自动创建）...")
        self.extract_target_path.setStyleSheet("""
            QLineEdit {
                padding: 18px;
                font-size: 20px;
                border: 4px solid #ccc;
                border-radius: 10px;
            }
        """)
        browse_btn2 = QPushButton("浏览...")
        browse_btn2.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                padding: 18px 25px;
                border-radius: 10px;
                font-size: 20px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        browse_btn2.clicked.connect(lambda: self.browse_folder(self.extract_target_path))

        target_layout.addWidget(QLabel("目标文件夹："))
        target_layout.addWidget(self.extract_target_path)
        target_layout.addWidget(browse_btn2)
        target_group.setLayout(target_layout)
        layout.addWidget(target_group)

        # 执行按钮
        exec_btn = QPushButton("▶️ 开始提取")
        exec_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                font-weight: bold;
                padding: 25px;
                border-radius: 15px;
                font-size: 28px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        exec_btn.clicked.connect(self.start_extract)
        layout.addWidget(exec_btn)

        self.tabs.addTab(tab, "4. 按名称提取文件夹")

    def create_shuffle_tab(self):
        """创建打乱图片名称标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 源文件夹选择 - GroupBox 标题 22px
        source_group = QGroupBox("📁 源文件夹")
        source_group.setStyleSheet("""
            QGroupBox { 
                font-weight: bold; 
                font-size: 22px;
                margin-top: 15px;
                padding-top: 20px;
                border: 4px solid #ccc;
                border-radius: 12px;
            }
        """)
        source_layout = QHBoxLayout()
        
        self.shuffle_source_path = QLineEdit()
        self.shuffle_source_path.setPlaceholderText("选择或输入包含图片的文件夹路径...")
        self.shuffle_source_path.setStyleSheet("""
            QLineEdit {
                padding: 18px;
                font-size: 20px;
                border: 4px solid #ccc;
                border-radius: 10px;
            }
        """)
        browse_btn = QPushButton("浏览...")
        browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                padding: 18px 25px;
                border-radius: 10px;
                font-size: 20px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        browse_btn.clicked.connect(lambda: self.browse_folder(self.shuffle_source_path))
        
        source_layout.addWidget(QLabel("源文件夹："))
        source_layout.addWidget(self.shuffle_source_path)
        source_layout.addWidget(browse_btn)
        source_group.setLayout(source_layout)
        layout.addWidget(source_group)
        
        # 执行按钮 - 超大按钮
        exec_btn = QPushButton("▶️ 开始打乱图片名称")
        exec_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                font-weight: bold;
                padding: 25px;
                border-radius: 15px;
                font-size: 28px;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
        """)
        exec_btn.clicked.connect(self.start_shuffle)
        layout.addWidget(exec_btn)
        
        self.tabs.addTab(tab, "3. 打乱图片文件名称顺序")

    def browse_folder(self, line_edit):
        """打开文件夹选择对话框"""
        folder = QFileDialog.getExistingDirectory(
            self, "选择文件夹", 
            line_edit.text() if line_edit.text() else os.path.expanduser("~")
        )
        if folder:
            line_edit.setText(folder)

    def start_split(self):
        """开始拆分操作"""
        source = self.split_source_path.text().strip()
        if not source or not os.path.exists(source):
            QMessageBox.warning(self, "警告", "请选择有效的源文件夹！")
            return
        
        max_files = self.max_files_spin.value()
        
        self.worker = ProcessingWorker("split", source_folder=source, max_files=max_files)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.finished_signal.connect(self.on_operation_finished)
        self.worker.start()
        self.set_processing_state(True)

    def start_flatten(self):
        """开始扁平化操作"""
        source = self.flatten_source_path.text().strip()
        if not source or not os.path.exists(source):
            QMessageBox.warning(self, "警告", "请选择有效的源文件夹！")
            return
        
        self.worker = ProcessingWorker("flatten", source_folder=source)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.finished_signal.connect(self.on_operation_finished)
        self.worker.start()
        self.set_processing_state(True)

    def start_extract(self):
        """开始按名称提取文件夹操作"""
        source = self.extract_source_path.text().strip()
        target = self.extract_target_path.text().strip()
        name = self.extract_folder_name.text().strip()

        if not source or not os.path.exists(source):
            QMessageBox.warning(self, "警告", "请选择有效的源文件夹！")
            return
        if not target or not os.path.exists(target):
            os.makedirs(target, exist_ok=True)
        if not name:
            QMessageBox.warning(self, "警告", "请输入要提取的文件夹名称！")
            return

        self.worker = ProcessingWorker("extract", source_folder=source, target_folder=target, folder_name=name)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.finished_signal.connect(self.on_operation_finished)
        self.worker.start()
        self.set_processing_state(True)

    def start_shuffle(self):
        """开始打乱图片名称操作"""
        source = self.shuffle_source_path.text().strip()
        if not source or not os.path.exists(source):
            QMessageBox.warning(self, "警告", "请选择有效的源文件夹！")
            return
        
        self.worker = ProcessingWorker("shuffle", source_folder=source)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.finished_signal.connect(self.on_operation_finished)
        self.worker.start()
        self.set_processing_state(True)

    def update_progress(self, value, message):
        """更新进度和日志"""
        self.progress_bar.setValue(value)
        self.log_text.append(f"[{value}%] {message}")
        QApplication.processEvents()

    def on_operation_finished(self, result):
        """操作完成回调"""
        self.log_text.append(f"\n{'='*50}\n结果：{result}\n{'='*50}")
        
        if "成功" in result or "已完成" in result:
            QMessageBox.information(self, "完成", result)
        else:
            QMessageBox.warning(self, "警告", result)
        
        self.set_processing_state(False)

    def cancel_operation(self):
        """取消操作"""
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.log_text.append("\n用户取消了操作...")

    def clear_log(self):
        """清空日志"""
        self.log_text.clear()

    def set_processing_state(self, is_processing):
        """设置处理状态"""
        self.cancel_btn.setEnabled(is_processing)
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            for widget in tab.findChildren(QLineEdit):
                widget.setEnabled(not is_processing)
            for widget in tab.findChildren(QSpinBox):
                widget.setEnabled(not is_processing)

    def closeEvent(self, event):
        """关闭窗口时的处理"""
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self, "确认退出",
                "正在执行操作，确定要退出吗？\n当前操作将被取消。",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.worker.cancel()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


def main():
    app = QApplication(sys.argv)
    window = FolderProcessorGUI()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
