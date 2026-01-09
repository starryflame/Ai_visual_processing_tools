# 预设标签功能
from PyQt5.QtWidgets import (QWidget, QHBoxLayout, 
                             QPushButton, QListWidget, QTextEdit, QLabel, 
                             QFileDialog, QMessageBox, QLineEdit, QAbstractItemView,
                             QCheckBox, QListWidgetItem,
                             QTreeWidgetItem,
                             QInputDialog)
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtCore import Qt, QSize
# 添加 QTimer 用于自动关闭消息框
from PyQt5.QtCore import QTimer
import re

# 全局字体设置
GLOBAL_FONT_FAMILY = "PingFang SC"  # 圆润字体
GLOBAL_FONT_SIZE = 14  # 增大字体大小
GLOBAL_FONT = QFont(GLOBAL_FONT_FAMILY, GLOBAL_FONT_SIZE)

# 保存预设标签
def save_preset_tags(self):
    tags_text = self.preset_tag_input.text()
    if tags_text:
        # 将新标签组添加到现有标签列表中
        new_tags = [tag.strip() for tag in re.split('[,，。.]', tags_text) if tag.strip()]
        self.preset_tags.append(new_tags)
        self.update_preset_tags_display()
        self.preset_tag_input.clear()
        
# 更新预设标签显示
def update_preset_tags_display(self):
    # 清除现有显示
    for i in reversed(range(self.preset_tags_layout.count())): 
        widget = self.preset_tags_layout.itemAt(i).widget()
        if widget:
            widget.setParent(None)
            
    # 添加新的标签按钮组
    row = 0
    col = 0
    for i, tag_group in enumerate(self.preset_tags):
        tag_container = QWidget()
        tag_layout = QHBoxLayout(tag_container)  # 标签内部仍然使用水平布局
        tag_layout.setContentsMargins(0, 0, 0, 0)
        tag_layout.setSpacing(2)
        
        # 显示标签组内容
        tags_text = ", ".join(tag_group[:3])  # 只显示前3个标签
        if len(tag_group) > 3:
            tags_text += "..."
            
        tag_button = QPushButton(tags_text)
        tag_button.setFont(GLOBAL_FONT)
        tag_button.setStyleSheet("""
            QPushButton {
                background-color: #E0E0E0;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                padding: 4px 8px;
                margin: 2px;
            }
            QPushButton:hover {
                background-color: #D0D0D0;
            }
        """)
        tag_button.clicked.connect(lambda checked, tg=tag_group: self.add_preset_tag_group_to_current(tg))
        
        delete_button = QPushButton("×")
        delete_button.setFont(GLOBAL_FONT)
        delete_button.setFixedSize(20, 20)
        delete_button.setStyleSheet("""
            QPushButton {
                background-color: #ff6666;
                color: white;
                border-radius: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ff3333;
            }
        """)
        delete_button.clicked.connect(lambda checked, index=i: self.delete_preset_tag(index))
        
        tag_layout.addWidget(tag_button)
        tag_layout.addWidget(delete_button)
        
        # 使用网格布局实现两列显示
        self.preset_tags_layout.addWidget(tag_container, row, col)
        
        # 更新行列索引
        if col == 0:
            col = 1
        else:
            col = 0
            row += 1
# 删除预设标签
def delete_preset_tag(self, index):
    if 0 <= index < len(self.preset_tags):
        del self.preset_tags[index]
        self.update_preset_tags_display()
# 将预设标签组添加到当前图片
def add_preset_tag_group_to_current(self, tag_group):
    # 修改为支持批量添加到所有选中图片
    target_images = self.selected_images if self.selected_images else ([self.current_image_name] if self.current_image_name else [])
    
    if not target_images:
        QMessageBox.warning(self, "警告", "请先选择至少一张图片")
        return
    
    added_info = []
    for image_name in target_images:
        tag_content = self.image_processor.get_tag_content(image_name)
        tags = [t.strip() for t in re.split('[,，。.]', tag_content) if t.strip()]
        
        # 添加标签组中的所有标签
        added_tags = []
        for tag in tag_group:
            if tag not in tags:
                # 根据选项决定添加位置
                if self.add_to_front_checkbox.isChecked():
                    tags.insert(0, tag)
                else:
                    tags.append(tag)
                added_tags.append(tag)
                
        # 保存更新后的标签
        self.image_processor.save_tags_to_image(image_name, tags)
        
        if added_tags:
            added_info.append((image_name, added_tags))
    
    # 刷新界面
    self.refresh_current_view()
    self.update_tag_statistics()
    
    # 创建自动关闭的消息框
    if added_info:
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle("成功")
        msg_box.setText(f"已将标签组添加到 {len(added_info)} 张图片")
        msg_box.setDetailedText("\n".join([f"{info[0]}: {', '.join(info[1])}" for info in added_info]))
        
        # 1秒后自动关闭
        timer = QTimer(msg_box)
        timer.timeout.connect(msg_box.close)
        timer.setSingleShot(True)
        timer.start(1000)  # 1秒
        
        msg_box.exec_()
    else:
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle("提示")
        msg_box.setText("标签组中的标签已全部存在于选中的图片中")
        
        # 1秒后自动关闭
        timer = QTimer(msg_box)
        timer.timeout.connect(msg_box.close)
        timer.setSingleShot(True)
        timer.start(1000)  # 1秒
        
        msg_box.exec_()
