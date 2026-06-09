# UI事件处理函数
import os
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QListWidget, QTextEdit, QLabel, 
                             QFileDialog, QMessageBox, QLineEdit, QAbstractItemView,
                             QCheckBox, QListWidgetItem,
                             QTreeWidgetItem,
                             QInputDialog)
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtCore import Qt, QSize

def on_thumbnail_loaded(self, image_name, thumbnail):
    # 在主线程中更新UI
    if image_name in self.thumbnail_items:
        item = self.thumbnail_items[image_name]
        if thumbnail:
            item.setIcon(QIcon(thumbnail))
            
def on_file_selected(self, current, previous):
    if current:
        self.current_image_name = current.text()
        # 显示图片
        pixmap = self.image_processor.get_pixmap(self.current_image_name)
        if pixmap:
            self.image_label.setPixmap(pixmap.scaled(
                self.image_label.width(), 
                self.image_label.height(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            ))
        
        # 显示标签复选框
        self.update_tag_checkboxes()
        
# 添加批量选中处理函数
def on_files_selected(self):
    selected_items = self.file_list.selectedItems()
    self.selected_images = [item.text() for item in selected_items]
    
    # 更新标签统计
    self.update_tag_statistics()