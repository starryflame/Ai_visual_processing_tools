# 标签管理功能
import os
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QListWidget, QTextEdit, QLabel, 
                             QFileDialog, QMessageBox, QLineEdit, QAbstractItemView,
                             QCheckBox, QListWidgetItem,
                             QTreeWidgetItem,
                             QInputDialog)
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtCore import Qt, QSize
import re

# 全局字体设置
GLOBAL_FONT_FAMILY = "PingFang SC"  # 圆润字体
GLOBAL_FONT_SIZE = 14  # 增大字体大小
GLOBAL_FONT = QFont(GLOBAL_FONT_FAMILY, GLOBAL_FONT_SIZE)

def update_tag_checkboxes(self):
    # 清除现有的标签展示
    for label in self.tag_checkboxes:
        self.tags_layout.removeWidget(label)
        label.deleteLater()
    self.tag_checkboxes = []
    
    # 获取当前图片的标签内容
    if self.current_image_name:
        tag_content = self.image_processor.get_tag_content(self.current_image_name)
        # 修改: 支持中英文逗号分割标签
        tags = [tag.strip() for tag in re.split('[,，。.]', tag_content) if tag.strip()]
        
        # 为每个标签创建美化展示标签
        for tag in tags:
            label = QLabel(tag)
            # 根据当前主题应用不同的样式
            if hasattr(self, 'current_theme') and self.current_theme == "dark":
                label.setStyleSheet("""
                    QLabel {
                        background-color: #555555;
                        border: 1px solid #777777;
                        border-radius: 4px;
                        padding: 4px;
                        margin: 2px;
                    }
                """)
            else:
                label.setStyleSheet("""
                    QLabel {
                        background-color: #E0E0E0;
                        border: 1px solid #CCCCCC;
                        border-radius: 4px;
                        padding: 4px;
                        margin: 2px;
                    }
                """)
            # 应用全局字体到标签
            label.setFont(GLOBAL_FONT)
            label.setWordWrap(True)  # 允许标签文本换行
            label.setMinimumSize(100, 30)  # 设置最小尺寸
            self.tags_layout.addWidget(label)
            self.tag_checkboxes.append(label)
            
    # 添加一个弹性空间，确保标签能正确换行显示
    self.tags_layout.addStretch()
def move_selected_tags_to_front(self):
    """
    将统计列表中选中的标签移动到所有选中图片的标签列表开头
    """
    selected_items = self.stats_tree.selectedItems()
    if not selected_items:
        QMessageBox.warning(self, "警告", "请先从统计列表中选择一个标签")
        return
        
    tag_name = selected_items[0].text(0)
    reply = QMessageBox.question(self, "确认", 
                               f"确定要将标签 '{tag_name}' 移动到所有选中 {len(self.selected_images)} 张图片的标签列表开头吗？",
                               QMessageBox.Yes | QMessageBox.No)
    
    if reply == QMessageBox.Yes:
        moved_count = 0
        for image_name in self.selected_images:
            tag_content = self.image_processor.get_tag_content(image_name)
            # 修改: 支持中英文逗号分割标签
            tags = [tag.strip() for tag in re.split('[,，。.]', tag_content) if tag.strip()]
            
            # 如果包含要移动的标签
            if tag_name in tags:
                # 移除标签并将其添加到开头
                tags.remove(tag_name)
                tags.insert(0, tag_name)
                # 保存更新后的标签
                self.image_processor.save_tags_to_image(image_name, tags)
                moved_count += 1
                
        QMessageBox.information(self, "完成", f"已将标签 '{tag_name}' 移动到 {moved_count} 张图片的标签列表开头")
        # 重新统计
        self.update_tag_statistics()
        # 刷新界面
        self.refresh_current_view()

# 添加标签到所有选中图片
def add_tag_to_all_selected(self):
    if len(self.selected_images) == 0:
        QMessageBox.warning(self, "警告", "请先选择至少一张图片")
        return
        
    tag_to_add = self.batch_tag_input2.text().strip()
    if not tag_to_add:
        QMessageBox.warning(self, "警告", "请输入要添加的标签")
        return
        
    added_count = 0
    for image_name in self.selected_images:
        tag_content = self.image_processor.get_tag_content(image_name)
        # 修改: 支持中英文逗号分割标签
        tags = [tag.strip() for tag in re.split('[,，。.]', tag_content) if tag.strip()]
        
        # 如果标签不存在，则添加
        if tag_to_add not in tags:
            # 根据选项决定添加位置
            if self.add_to_front_checkbox.isChecked():
                tags.insert(0, tag_to_add)
            else:
                tags.append(tag_to_add)
            # 保存更新后的标签
            self.image_processor.save_tags_to_image(image_name, tags)
            added_count += 1
            
    QMessageBox.information(self, "完成", f"已将标签 '{tag_to_add}' 添加到 {added_count} 张图片中")
    # 重新统计
    self.update_tag_statistics()
    # 刷新界面
    self.refresh_current_view()

# 从所有选中图片中删除标签
def delete_selected_tag_from_all(self):
    selected_items = self.stats_tree.selectedItems()
    if not selected_items:
        QMessageBox.warning(self, "警告", "请先从统计列表中选择一个标签")
        return
        
    tag_name = selected_items[0].text(0)
    reply = QMessageBox.question(self, "确认", 
                               f"确定要从所有选中的 {len(self.selected_images)} 张图片中删除标签 '{tag_name}' 吗？",
                               QMessageBox.Yes | QMessageBox.No)
    
    if reply == QMessageBox.Yes:
        deleted_count = 0
        for image_name in self.selected_images:
            tag_content = self.image_processor.get_tag_content(image_name)
            # 修改: 支持中英文逗号分割标签
            tags = [tag.strip() for tag in re.split('[,，。.]', tag_content) if tag.strip()]
            
            # 如果包含要删除的标签
            if tag_name in tags:
                tags.remove(tag_name)
                # 保存更新后的标签
                self.image_processor.save_tags_to_image(image_name, tags)
                deleted_count += 1
                
        QMessageBox.information(self, "完成", f"已从 {deleted_count} 张图片中删除标签 '{tag_name}'")
        # 重新统计
        self.update_tag_statistics()
        # 刷新界面
        self.refresh_current_view()
# 修改所有选中图片中的标签
def modify_selected_tag_for_all(self):
    selected_items = self.stats_tree.selectedItems()
    if not selected_items:
        QMessageBox.warning(self, "警告", "请先从统计列表中选择一个标签")
        return
        
    old_tag = selected_items[0].text(0)
    dialog = QInputDialog(self)
    dialog.setInputMode(QInputDialog.TextInput)
    dialog.setWindowTitle("修改标签")
    dialog.setLabelText(f"将 '{old_tag}' 修改为:")
    dialog.setTextValue(old_tag)
    # 增大弹窗尺寸
    dialog.resize(400, 350)
    # 应用全局字体设置
    dialog.setFont(GLOBAL_FONT)
    ok = dialog.exec_()
    new_tag = dialog.textValue()
    
    if ok and new_tag:
        modified_count = 0
        for image_name in self.selected_images:
            tag_content = self.image_processor.get_tag_content(image_name)
            # 修改: 支持中英文逗号分割标签
            tags = [tag.strip() for tag in re.split('[,，。.]', tag_content) if tag.strip()]
            
            # 如果包含要修改的标签
            if old_tag in tags:
                # 替换标签
                tags = [new_tag if tag == old_tag else tag for tag in tags]
                # 保存更新后的标签
                self.image_processor.save_tags_to_image(image_name, tags)
                modified_count += 1
                
        QMessageBox.information(self, "完成", f"已在 {modified_count} 张图片中将标签 '{old_tag}' 修改为 '{new_tag}'")
        # 重新统计
        self.update_tag_statistics()
        # 刷新界面
        self.refresh_current_view()
# 添加标签到所有选中图片
def add_tag_to_all_selected(self):
    if len(self.selected_images) == 0:
        QMessageBox.warning(self, "警告", "请先选择至少一张图片")
        return
        
    tag_to_add = self.batch_tag_input2.text().strip()
    if not tag_to_add:
        QMessageBox.warning(self, "警告", "请输入要添加的标签")
        return
        
    added_count = 0
    for image_name in self.selected_images:
        tag_content = self.image_processor.get_tag_content(image_name)
        # 修改: 支持中英文逗号分割标签
        tags = [tag.strip() for tag in re.split('[,，。.]', tag_content) if tag.strip()]
        
        # 如果标签不存在，则添加
        if tag_to_add not in tags:
            # 根据选项决定添加位置
            if self.add_to_front_checkbox.isChecked():
                tags.insert(0, tag_to_add)
            else:
                tags.append(tag_to_add)
            # 保存更新后的标签
            self.image_processor.save_tags_to_image(image_name, tags)
            added_count += 1
            
    QMessageBox.information(self, "完成", f"已将标签 '{tag_to_add}' 添加到 {added_count} 张图片中")
    # 重新统计
    self.update_tag_statistics()
    # 刷新界面
    self.refresh_current_view()