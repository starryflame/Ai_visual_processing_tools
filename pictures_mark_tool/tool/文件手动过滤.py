import os
import sys
import shutil
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QListWidget, QListWidgetItem, QLabel, 
                             QPushButton, QFileDialog, QSplitter, QAbstractItemView,
                             QAction, QMenu)
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import Qt, QSize, QThread, pyqtSignal, QMutex, QMutexLocker
import threading
from functools import lru_cache
import time  # 添加time导入


class ThumbnailGenerator(QThread):
    thumbnail_ready = pyqtSignal(str, object)  # 发送文件路径和缩略图pixmap

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
            pixmap = QPixmap(img_path)
            if not pixmap.isNull():
                # 调整图片大小为缩略图
                thumbnail = pixmap.scaled(
                    self.icon_size.width(), 
                    self.icon_size.height(), 
                    Qt.KeepAspectRatio, 
                    Qt.SmoothTransformation
                )
                # 发送信号，传递文件名和缩略图
                self.thumbnail_ready.emit(img_file, thumbnail)

    def stop(self):
        with QMutexLocker(self.mutex):
            self._is_running = False

class ImageViewer(QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle("图片手动过滤工具")
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
        
        # 创建主窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # 左侧面板 - 源文件夹和缩略图
        self.left_panel = QWidget()  # 改为实例变量
        self.left_panel.setAcceptDrops(True)  # 启用拖放
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
        self.thumbnail_list.setIconSize(QSize(200, 200))  # 扩大一倍
        self.thumbnail_list.setResizeMode(QListWidget.Adjust)
        self.thumbnail_list.setMovement(QListWidget.Static)
        self.thumbnail_list.setDragDropMode(QListWidget.NoDragDrop)  # 禁止拖拽排序
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
        self.preview_label.setStyleSheet("border: 1px solid gray;")
        
        middle_layout.addWidget(self.preview_label)
        
        # 控制按钮
        controls_layout = QHBoxLayout()
        self.prev_btn = QPushButton("上一张")
        self.copy_btn = QPushButton("复制到目标文件夹")
        self.delete_btn = QPushButton("删除当前图片")  # 新增删除按钮
        self.next_btn = QPushButton("下一张")
        
        # 设置按钮高度更高
        button_height = 200
        self.prev_btn.setFixedHeight(button_height)
        self.copy_btn.setFixedHeight(button_height)
        self.delete_btn.setFixedHeight(button_height)  # 设置删除按钮高度
        self.next_btn.setFixedHeight(button_height)
        
        self.prev_btn.clicked.connect(self.show_prev_image)
        self.next_btn.clicked.connect(self.show_next_image)
        self.copy_btn.clicked.connect(self.copy_current_image)
        self.delete_btn.clicked.connect(self.delete_current_image)  # 连接删除功能

        controls_layout.addWidget(self.copy_btn)
        controls_layout.addWidget(self.prev_btn)
        controls_layout.addWidget(self.next_btn)
        controls_layout.addWidget(self.delete_btn)  # 添加删除按钮到布局

        middle_layout.addLayout(controls_layout)
        
        # 右侧面板 - 目标文件夹和预览
        self.right_panel = QWidget()  # 改为实例变量
        self.right_panel.setAcceptDrops(True)  # 启用拖放
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
        self.dest_preview_list.setIconSize(QSize(160, 160))  # 扩大一倍
        self.dest_preview_list.setResizeMode(QListWidget.Adjust)
        self.dest_preview_list.setDragDropMode(QListWidget.NoDragDrop)
        self.dest_preview_list.currentItemChanged.connect(self.on_dest_thumbnail_selected)  # 添加右侧缩略图选中事件
        
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
        self.delete_threshold = 1.0  # 1秒内双击才会删除

    def apply_theme(self):
        """应用深色主题"""
        # 设置深色主题样式
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

    def setup_menu(self):
        """设置菜单栏"""
        menubar = self.menuBar()
        
        # 其他菜单可以保留，但主题菜单被删除
        # 主题菜单相关代码已删除

    def select_source_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择源图片文件夹")
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
        self.thumbnail_list.clear()
        self.image_files = []
        
        # 支持的图片格式
        img_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp']
        
        for file in os.listdir(folder):
            if any(file.lower().endswith(ext) for ext in img_extensions):
                self.image_files.append(file)
        
        # 如果有图片文件，启动缩略图生成线程
        if self.image_files:
            # 停止之前的线程
            if self.thumbnail_thread and self.thumbnail_thread.isRunning():
                self.thumbnail_thread.stop()
                self.thumbnail_thread.wait()
            
            # 启动新线程生成缩略图
            self.thumbnail_thread = ThumbnailGenerator(folder, self.image_files)
            self.thumbnail_thread.thumbnail_ready.connect(self.add_thumbnail_to_list)
            self.thumbnail_thread.start()
        
        # 选中第一张图片
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
            item = QListWidgetItem(icon, img_file)
            item.setSizeHint(QSize(240, 240))  # 相应增加项目大小
            self.thumbnail_list.addItem(item)
    
    def load_dest_preview(self):
        if not self.dest_folder or not os.path.exists(self.dest_folder):
            return
            
        self.dest_preview_list.clear()
        
        # 支持的图片格式
        img_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp']
        
        files_in_dest = []
        for file in os.listdir(self.dest_folder):
            if any(file.lower().endswith(ext) for ext in img_extensions):
                files_in_dest.append(file)
                img_path = os.path.join(self.dest_folder, file)
                pixmap = QPixmap(img_path)
                if not pixmap.isNull():
                    # 调整图片大小为缩略图 - 扩大一倍
                    thumbnail = pixmap.scaled(160, 160, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    icon = QIcon(thumbnail)
                    item = QListWidgetItem(icon, file)
                    item.setSizeHint(QSize(200, 200))  # 相应增加项目大小
                    self.dest_preview_list.addItem(item)
        
        # 更新目标文件夹统计
        self.update_dest_stats()
    
    def on_thumbnail_selected(self, current, previous):
        if current:
            # 获取当前选中的图片索引
            row = self.thumbnail_list.row(current)
            if 0 <= row < len(self.image_files):
                self.current_image_index = row
                self.show_current_image()
                # 确保左侧列表有焦点
                self.thumbnail_list.setFocus()
    
    def show_current_image(self):
        if not self.image_files or self.current_image_index >= len(self.image_files):
            return
            
        img_file = self.image_files[self.current_image_index]
        img_path = os.path.join(self.source_folder, img_file)
        
        pixmap = QPixmap(img_path)
        if not pixmap.isNull():
            # 调整图片大小以适应预览区域
            preview_size = self.preview_label.size()
            scaled_pixmap = pixmap.scaled(
                preview_size.width() - 10, 
                preview_size.height() - 10, 
                Qt.KeepAspectRatio, 
                Qt.SmoothTransformation
            )
            self.preview_label.setPixmap(scaled_pixmap)
            self.current_image = img_path
    
    def show_prev_image(self):
        if self.image_files and self.current_image_index > 0:
            self.current_image_index -= 1
            self.thumbnail_list.setCurrentRow(self.current_image_index)
            self.show_current_image()
    
    def show_next_image(self):
        if self.image_files and self.current_image_index < len(self.image_files) - 1:
            self.current_image_index += 1
            self.thumbnail_list.setCurrentRow(self.current_image_index)
            self.show_current_image()
    
    def copy_current_image(self):
        if not self.image_files or not self.dest_folder:
            return
            
        if self.current_image_index >= len(self.image_files):
            return
            
        img_file = self.image_files[self.current_image_index]
        src_path = os.path.join(self.source_folder, img_file)
        
        # 检测目标文件夹中是否已存在同名文件，如有则添加后缀
        dest_path = self.get_unique_dest_path(img_file)
        
        # 复制文件
        try:
            shutil.copy2(src_path, dest_path)
            print(f"已复制: {src_path} -> {dest_path}")
            # 添加新复制的文件到右侧预览列表
            pixmap = QPixmap(dest_path)
            if not pixmap.isNull():
                # 调整图片大小为缩略图
                thumbnail = pixmap.scaled(160, 160, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                icon = QIcon(thumbnail)
                item = QListWidgetItem(icon, os.path.basename(dest_path))
                item.setSizeHint(QSize(200, 200))
                self.dest_preview_list.addItem(item)
        except Exception as e:
            print(f"复制失败: {e}")
        
        # 更新统计信息
        self.update_source_stats()
        self.update_dest_stats()
    
    def get_unique_dest_path(self, filename):
        """获取唯一的文件路径，避免重名"""
        name, ext = os.path.splitext(filename)
        dest_path = os.path.join(self.dest_folder, filename)
        counter = 1
        
        # 检查目标路径是否已存在，如果存在则添加数字后缀
        while os.path.exists(dest_path):
            new_name = f"{name}_{counter}{ext}"
            dest_path = os.path.join(self.dest_folder, new_name)
            counter += 1
            
        return dest_path
    
    def delete_current_image(self):
        """删除当前预览的图片，无论焦点在哪个列表"""
        current_time = time.time()
        
        # 检查是否在阈值时间内再次触发删除
        if current_time - self.last_delete_time < self.delete_threshold:
            # 执行删除操作
            self.perform_delete()
            self.last_delete_time = 0  # 重置时间
        else:
            # 更新删除时间，等待双击
            self.last_delete_time = current_time
            # 在1秒后重置删除时间
            from PyQt5.QtCore import QTimer
            timer = QTimer(self)
            timer.timeout.connect(lambda: setattr(self, 'last_delete_time', 
                                                0 if time.time() - self.last_delete_time >= self.delete_threshold else self.last_delete_time))
            timer.setSingleShot(True)
            timer.start(int(self.delete_threshold * 1000))

    def perform_delete(self):
        """执行实际的删除操作"""
        # 首先尝试删除中间预览的图片（如果有预览图片）
        if self.current_image and os.path.exists(self.current_image):
            # 确定当前预览的图片属于哪个文件夹
            if self.current_image.startswith(self.source_folder):
                # 这是源文件夹中的图片
                img_file = os.path.basename(self.current_image)
                
                try:
                    # 删除文件
                    os.remove(self.current_image)
                    print(f"已删除: {self.current_image}")
                    
                    # 从列表中移除文件
                    try:
                        img_index = self.image_files.index(img_file)
                        del self.image_files[img_index]
                        
                        # 更新缩略图列表
                        current_item = self.thumbnail_list.currentItem()
                        if current_item:
                            current_row = self.thumbnail_list.row(current_item)
                            self.thumbnail_list.takeItem(current_row)
                        
                        # 调整索引并显示下一张图片（如果存在）
                        if img_index < self.current_image_index:
                            self.current_image_index -= 1
                        elif img_index == self.current_image_index:
                            # 如果删除的是当前显示的图片，调整索引并显示新图片
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
                        # 文件不在列表中，重新加载列表
                        self.load_images_from_folder(self.source_folder)
                        
                except Exception as e:
                    print(f"删除失败: {e}")
                
                # 更新源文件夹统计
                self.update_source_stats()
            elif self.dest_folder and self.current_image.startswith(self.dest_folder):
                # 这是目标文件夹中的图片
                img_file = os.path.basename(self.current_image)
                
                try:
                    # 删除文件
                    os.remove(self.current_image)
                    print(f"已删除: {self.current_image}")
                    
                    # 从右侧列表中移除选中的项
                    current_item = self.dest_preview_list.currentItem()
                    if current_item:
                        row = self.dest_preview_list.row(current_item)
                        self.dest_preview_list.takeItem(row)
                    
                    # 清除预览
                    self.preview_label.clear()
                    self.current_image = None
                    
                    # 只更新统计信息，不重新加载整个列表
                    self.update_dest_stats()
                    
                except Exception as e:
                    print(f"删除失败: {e}")
                
                # 更新目标文件夹统计
                self.update_dest_stats()
        else:
            # 如果没有预览图片，按原来的焦点逻辑处理
            # 检查焦点在哪个列表
            focused_widget = QApplication.focusWidget()
            
            if focused_widget == self.dest_preview_list and self.dest_folder:
                # 如果焦点在右侧列表，删除右侧选中的图片
                current_item = self.dest_preview_list.currentItem()
                if not current_item:
                    return
                    
                img_file = current_item.text()
                img_path = os.path.join(self.dest_folder, img_file)
                
                try:
                    os.remove(img_path)
                    print(f"已删除: {img_path}")
                    
                    # 从右侧列表中移除选中的项
                    row = self.dest_preview_list.row(current_item)
                    self.dest_preview_list.takeItem(row)
                    
                    # 清除预览
                    self.preview_label.clear()
                    self.current_image = None
                    
                    # 只更新统计信息，不重新加载整个列表 - 这是关键修改
                    self.update_dest_stats()
                        
                except Exception as e:
                    print(f"删除失败: {e}")
                
                # 更新目标文件夹统计
                self.update_dest_stats()
            elif focused_widget == self.thumbnail_list and self.source_folder:
                # 如果焦点在左侧列表，删除左侧选中的图片
                current_item = self.thumbnail_list.currentItem()
                if not current_item:
                    return
                    
                img_file = current_item.text()
                
                # 找到对应索引
                try:
                    img_index = self.image_files.index(img_file)
                except ValueError:
                    return  # 文件不在列表中
                    
                img_path = os.path.join(self.source_folder, img_file)
                
                try:
                    os.remove(img_path)
                    print(f"已删除: {img_path}")
                    
                    # 从列表中移除文件
                    del self.image_files[img_index]
                    
                    # 更新缩略图列表
                    self.thumbnail_list.takeItem(self.thumbnail_list.row(current_item))
                    
                    # 调整索引并显示下一张图片（如果存在）
                    if img_index < self.current_image_index:
                        self.current_image_index -= 1
                    elif img_index == self.current_image_index:
                        # 如果删除的是当前显示的图片，调整索引并显示新图片
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
                    print(f"删除失败: {e}")
                
                # 更新源文件夹统计
                self.update_source_stats()
            elif self.image_files and 0 <= self.current_image_index < len(self.image_files):
                # 如果没有焦点在列表上，删除当前选中的源图片
                img_file = self.image_files[self.current_image_index]
                img_path = os.path.join(self.source_folder, img_file)
                
                try:
                    os.remove(img_path)
                    print(f"已删除: {img_path}")
                    
                    # 从列表中移除文件
                    del self.image_files[self.current_image_index]
                    
                    # 更新缩略图列表
                    current_row = self.thumbnail_list.currentRow()
                    if current_row != -1:
                        self.thumbnail_list.takeItem(current_row)
                    
                    # 调整索引并显示下一张图片（如果存在）
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
                    print(f"删除失败: {e}")
                
                # 更新源文件夹统计
                self.update_source_stats()

    def on_dest_thumbnail_selected(self, current, previous):
        """处理右侧缩略图选中事件"""
        if current:
            # 获取当前选中的图片文件名
            img_file = current.text()
            img_path = os.path.join(self.dest_folder, img_file)
            
            pixmap = QPixmap(img_path)
            if not pixmap.isNull():
                # 调整图片大小以适应预览区域
                preview_size = self.preview_label.size()
                scaled_pixmap = pixmap.scaled(
                    preview_size.width() - 10, 
                    preview_size.height() - 10, 
                    Qt.KeepAspectRatio, 
                    Qt.SmoothTransformation
                )
                self.preview_label.setPixmap(scaled_pixmap)
                self.current_image = img_path
                # 确保右侧列表有焦点以便能够删除
                self.dest_preview_list.setFocus()

    def keyPressEvent(self, event):
        """处理键盘快捷键事件"""
        key = event.key()
        
        if key == Qt.Key_Left:  # 左方向键（包括小键盘）
            self.show_prev_image()
        elif key == Qt.Key_Right:  # 右方向键（包括小键盘）
            self.show_next_image()
        elif key == Qt.Key_Delete:  # Delete键
            # 检查焦点在哪个列表，以决定删除哪个列表中的图片
            focused_widget = QApplication.focusWidget()
            if focused_widget == self.dest_preview_list:
                self.delete_current_image()
            elif focused_widget == self.thumbnail_list:
                self.delete_current_image()
            else:
                # 如果焦点不在任一列表，删除当前选中的图片（默认为左侧）
                self.delete_current_image()
        elif key == Qt.Key_Enter or key == Qt.Key_Return:  # Enter键（包括小键盘和主键盘）
            self.copy_current_image()
        else:
            # 调用父类的keyPressEvent处理其他按键
            super().keyPressEvent(event)

    def update_source_stats(self):
        """更新源文件夹统计信息"""
        total = len(self.image_files)
        if not hasattr(self, 'original_source_count') or self.original_source_count is None:
            self.original_source_count = total
        deleted = max(0, self.original_source_count - total)  # 确保删除数不为负
        self.source_stats_label.setText(f"总计: {total}, 已删除: {deleted}, 剩余: {total}")

    def update_dest_stats(self):
        """更新目标文件夹统计信息"""
        total = self.dest_preview_list.count()
        if not hasattr(self, 'original_dest_count') or self.original_dest_count is None:
            self.original_dest_count = 0  # 初始化为0
        added = total - self.original_dest_count
        self.dest_stats_label.setText(f"总计: {total}, 已添加: {max(0, added)}, 剩余: {total}")  # 确保添加数不为负

    def dragEnterEvent(self, event):
        """处理拖拽进入主窗口事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        """处理拖拽移动事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        """处理拖拽释放事件"""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            for url in urls:
                path = url.toLocalFile()
                if os.path.isdir(path):  # 检查是否为文件夹
                    # 判断拖拽到哪个面板
                    pos = event.pos()
                    # 获取左右面板在主窗口中的位置和大小
                    left_rect = self.left_panel.geometry()
                    right_rect = self.right_panel.geometry()
                    
                    # 转换坐标到全局坐标系进行比较
                    global_left_top = self.left_panel.mapToGlobal(self.left_panel.pos())
                    global_right_top = self.right_panel.mapToGlobal(self.right_panel.pos())
                    
                    # 检查鼠标位置在哪个面板上
                    if pos.x() < (global_left_top.x() + self.left_panel.width()):
                        # 拖到左侧面板，设置为源文件夹
                        self.source_folder = path
                        self.source_folder_label.setText(path)
                        self.load_images_from_folder(path)
                    elif pos.x() < (global_right_top.x() + self.right_panel.width()):
                        # 拖到右侧面板，设置为目标文件夹
                        self.dest_folder = path
                        self.dest_folder_label.setText(path)
                        self.load_dest_preview()
                    break  # 只处理第一个有效的文件夹
            event.acceptProposedAction()

    def dragEnterEvent(self, event):
        """处理拖拽进入事件"""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            for url in urls:
                path = url.toLocalFile()
                if os.path.isdir(path):  # 确保是文件夹
                    event.acceptProposedAction()
                    return

    def dropEvent(self, event):
        """处理拖拽释放事件"""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            for url in urls:
                path = url.toLocalFile()
                if os.path.isdir(path):  # 检查是否为文件夹
                    # 判断拖拽到哪个面板
                    pos = event.pos()
                    # 获取左右面板相对于主窗口的位置
                    left_pos = self.left_panel.pos().x()
                    left_width = self.left_panel.width()
                    right_pos = self.right_panel.pos().x()
                    
                    # 简单的位置判断，根据面板的相对位置确定拖放目标
                    if pos.x() < right_pos:
                        # 拖到左侧面板，设置为源文件夹
                        self.source_folder = path
                        self.source_folder_label.setText(path)
                        self.load_images_from_folder(path)
                    else:
                        # 拖到右侧面板，设置为目标文件夹
                        self.dest_folder = path
                        self.dest_folder_label.setText(path)
                        self.load_dest_preview()
                    break  # 只处理第一个有效的文件夹
            event.acceptProposedAction()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = ImageViewer()
    viewer.show()
    sys.exit(app.exec_())






