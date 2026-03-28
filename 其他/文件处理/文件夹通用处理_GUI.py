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

    def __init__(self, operation, source_folder=None, target_folder=None, max_files=1000):
        super().__init__()
        self.operation = operation
        self.source_folder = source_folder
        self.target_folder = target_folder
        self.max_files = max_files
        self.cancelled = False

    def run(self):
        if self.operation == "split":
            self.process_split()
        elif self.operation == "flatten":
            self.process_flatten()
        elif self.operation == "shuffle":
            self.process_shuffle()

    def cancel(self):
        self.cancelled = True

    def process_split(self):
        """拆分大文件夹"""
        source_path = Path(self.source_folder)
        
        if not source_path.exists():
            self.finished_signal.emit(f"错误：源文件夹 {self.source_folder} 不存在")
            return
        
        self.progress_signal.emit(5, "正在读取文件列表...")
        files = [f for f in source_path.iterdir() if f.is_file()]
        
        if not files:
            self.finished_signal.emit("错误：源文件夹中没有文件")
            return
        
        self.progress_signal.emit(10, f"找到 {len(files)} 个文件，开始拆分...")
        
        folder_count = 0
        file_count = 0
        current_subfolder = None
        
        for file_path in files:
            if self.cancelled:
                self.finished_signal.emit("操作已取消")
                return
            
            if file_count % self.max_files == 0:
                folder_count += 1
                subfolder_name = f"{source_path.name}_part_{folder_count}"
                current_subfolder = source_path / subfolder_name
                current_subfolder.mkdir(exist_ok=True)
                self.progress_signal.emit(
                    int(10 + (file_count / len(files)) * 20),
                    f"创建文件夹：{subfolder_name}"
                )
            
            destination = current_subfolder / file_path.name
            shutil.move(str(file_path), str(destination))
            file_count += 1
            
            if file_count % 100 == 0:
                progress = int(30 + (file_count / len(files)) * 40)
                self.progress_signal.emit(progress, f"已处理 {file_count} 个文件")
        
        total_progress = int(70 + (folder_count / max(folder_count, 1)) * 30)
        self.progress_signal.emit(total_progress, f"拆分完成，共创建 {folder_count} 个子文件夹，处理 {file_count} 个文件")
        self.finished_signal.emit(f"成功！已创建 {folder_count} 个子文件夹，处理了 {file_count} 个文件")

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
        """打乱图片文件名"""
        source_path = Path(self.source_folder)
        
        if not source_path.exists():
            self.finished_signal.emit(f"错误：源文件夹 {self.source_folder} 不存在")
            return
        
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.svg'}
        
        self.progress_signal.emit(5, "正在查找图片文件...")
        image_files = [f for f in source_path.iterdir() 
                       if f.is_file() and f.suffix.lower() in image_extensions]
        
        if not image_files:
            self.finished_signal.emit("错误：源文件夹中没有图片文件")
            return
        
        self.progress_signal.emit(10, f"找到 {len(image_files)} 个图片文件，开始打乱名称...")
        
        temp_names = []
        final_names = [f.name for f in image_files]
        
        # 生成临时名称并重命名
        for i, img_file in enumerate(image_files):
            if self.cancelled:
                self.finished_signal.emit("操作已取消")
                return
            
            temp_name = f"temp_{i:06d}{img_file.suffix}"
            temp_names.append(temp_name)
            
            temp_path = source_path / temp_name
            img_file.rename(temp_path)
        
        self.progress_signal.emit(50, "文件已重命名为临时名称，正在打乱...")
        
        # 打乱最终名称列表并重新命名
        random.shuffle(final_names)
        
        for temp_name, final_name in zip(temp_names, final_names):
            if self.cancelled:
                self.finished_signal.emit("操作已取消")
                return
            
            temp_path = source_path / temp_name
            final_path = source_path / final_name
            temp_path.rename(final_path)
        
        self.progress_signal.emit(100, f"已完成 {len(image_files)} 个图片文件的名称打乱")
        self.finished_signal.emit(f"成功！已打乱 {len(image_files)} 个图片文件的名称")


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
