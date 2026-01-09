import os
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QListWidget, QTextEdit, QLabel, 
                             QFileDialog, QMessageBox, QLineEdit, QAbstractItemView,
                             QCheckBox, QListWidgetItem,
                             QTreeWidgetItem,
                             QInputDialog)
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtCore import Qt, QSize

# 全局字体设置
GLOBAL_FONT_FAMILY = "PingFang SC"  # 圆润字体
GLOBAL_FONT_SIZE = 14  # 增大字体大小
GLOBAL_FONT = QFont(GLOBAL_FONT_FAMILY, GLOBAL_FONT_SIZE)
def import_folder(self):
    folder_path = QFileDialog.getExistingDirectory(self, "选择图片文件夹")
    if folder_path:
        try:
            self.image_processor.load_folder(folder_path)
            self.update_file_list()
            self.update_statistics()  # 更新统计信息
            QMessageBox.information(self, "成功", f"成功导入 {len(self.image_processor.images)} 张图片")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导入失败: {str(e)}")
            
def append_folder(self):
    """
    追加文件夹功能，将新文件夹中的图片添加到现有列表中
    注意：这只是将新文件夹中的图片信息加入到当前会话中，并不会物理复制文件到原文件夹
    """
    folder_path = QFileDialog.getExistingDirectory(self, "选择要追加的图片文件夹")
    if folder_path:
        try:
            # 保存当前图片数量
            old_count = len(self.image_processor.images)
            
            # 支持的图片格式
            image_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.gif')
            
            # 遍历新文件夹中的图片并添加到现有集合中
            for filename in os.listdir(folder_path):
                if filename.lower().endswith(image_extensions):
                    image_name = os.path.splitext(filename)[0]
                    image_path = os.path.join(folder_path, filename)
                    tag_path = os.path.join(folder_path, image_name + '.txt')
                    
                    # 处理重名情况：如果名称已存在，则添加序号
                    original_image_name = image_name
                    counter = 1
                    while image_name in self.image_processor.images:
                        image_name = f"{original_image_name}_({counter})"
                        counter += 1
                    
                    # 更新正确的标签路径
                    tag_path = os.path.join(folder_path, original_image_name + '.txt')
                    
                    # 即使标签文件不存在也记录图片信息
                    self.image_processor.images[image_name] = {
                        'image_path': image_path,
                        'tag_path': tag_path
                    }
            
            self.update_file_list()
            self.update_statistics()  # 更新统计信息
            new_count = len(self.image_processor.images) - old_count
            QMessageBox.information(self, "成功", f"成功追加 {new_count} 张新图片")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"追加失败: {str(e)}")
            
def update_file_list(self):
    self.file_list.clear()
    self.thumbnail_items.clear()
    
    # 添加所有文件项（无缩略图）
    for image_name in self.image_processor.images.keys():
        item = QListWidgetItem(image_name)
        item.setIcon(QIcon())  # 先设置空图标
        # 设置合适的图标大小和文本位置，解决部分区域无法点击的问题
        item.setSizeHint(QSize(400, 420))  # 调整项目大小
        self.file_list.addItem(item)
        self.thumbnail_items[image_name] = item
        
    # 开始异步加载缩略图
    for image_name in self.image_processor.images.keys():
        self.image_processor.load_thumbnail_async(image_name)
        
    # 更新统计信息
    self.update_statistics()
    
    # 重要：清除当前选中图片名称，避免引用已删除的图片
    self.current_image_name = None
    # 清除标签显示
    self.update_tag_checkboxes()
        
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
        
# 更新标签统计信息
def update_tag_statistics(self):
    self.tag_statistics = {}
    
    # 统计每个标签出现的频率
    for image_name in self.selected_images:
        tag_content = self.image_processor.get_tag_content(image_name)
        tags = [tag.strip() for tag in tag_content.split(',') if tag.strip()]
        
        for tag in tags:
            if tag in self.tag_statistics:
                self.tag_statistics[tag] += 1
            else:
                self.tag_statistics[tag] = 1
                
    # 更新统计显示
    self.update_statistics_display()
    
# 更新统计显示
def update_statistics_display(self):
    # 清空现有统计显示
    self.stats_tree.clear()
    
    # 添加统计信息为树形结构
    for tag, count in sorted(self.tag_statistics.items(), key=lambda x: x[1], reverse=True):
        percentage = count / len(self.selected_images) * 100 if self.selected_images else 0
        item = QTreeWidgetItem([tag, str(count), f"{percentage:.1f}%"])
        self.stats_tree.addTopLevelItem(item)
         
# 
# 全选图片
def select_all_images(self):
    self.file_list.selectAll()
    
# 取消全选
def deselect_all_images(self):
    self.file_list.clearSelection()
    
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
            tags = [tag.strip() for tag in tag_content.split(',') if tag.strip()]
            
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
    new_tag, ok = QInputDialog.getText(self, "修改标签", 
                                      f"将 '{old_tag}' 修改为:",
                                      text=old_tag)
    
    if ok and new_tag:
        modified_count = 0
        for image_name in self.selected_images:
            tag_content = self.image_processor.get_tag_content(image_name)
            tags = [tag.strip() for tag in tag_content.split(',') if tag.strip()]
            
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
        tags = [tag.strip() for tag in tag_content.split(',') if tag.strip()]
        
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
    self.batch_tag_input2.clear()
    # 刷新界面
    self.refresh_current_view()
def update_tag_checkboxes(self):
    # 清除现有的标签展示
    for label in self.tag_checkboxes:
        self.tags_layout.removeWidget(label)
        label.deleteLater()
    self.tag_checkboxes = []
    
    # 获取当前图片的标签内容
    if self.current_image_name:
        tag_content = self.image_processor.get_tag_content(self.current_image_name)
        tags = [tag.strip() for tag in tag_content.split(',') if tag.strip()]
        
        # 为每个标签创建美化展示标签
        for tag in tags:
            label = QLabel(tag)
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
            tags = [tag.strip() for tag in tag_content.split(',') if tag.strip()]
            
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
def closeEvent(self, event):
    # 关闭时清理线程资源
    self.image_processor.shutdown()
    event.accept()
def update_statistics(self):
    """
    更新文件列表统计信息
    """
    total_images = len(self.image_processor.images)
    
    # 统计已打标和未打标的图片数量
    tagged_count = 0
    untagged_count = 0
    
    for image_name in self.image_processor.images:
        tag_path = self.image_processor.images[image_name]['tag_path']
        if os.path.exists(tag_path):
            # 检查标签文件是否为空
            try:
                with open(tag_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        tagged_count += 1
                    else:
                        untagged_count += 1
            except Exception:
                untagged_count += 1
        else:
            untagged_count += 1
            
    # 更新统计标签显示
    stats_text = f"总图片数: {total_images} | 已打标: {tagged_count} | 未打标: {untagged_count}"
    self.stats_label.setText(stats_text)
    
def export_renamed_files(self):
    """
    导出重命名功能，将当前图片文件列表里的图片和标签重新命名并保存到指定文件夹里
    注意：此功能不会修改原始文件夹中的文件，仅将文件复制到新位置并重命名
    """
    if not self.image_processor.images:
        QMessageBox.warning(self, "警告", "当前没有图片可以导出")
        return
        
    # 选择目标文件夹
    target_folder = QFileDialog.getExistingDirectory(self, "选择导出目标文件夹")
    if not target_folder:
        return
        
    # 获取重命名前缀
    prefix, ok = QInputDialog.getText(self, "重命名设置", "请输入文件名前缀:", text="image")
    if not ok:
        return
        
    # 获取起始编号
    start_num, ok = QInputDialog.getInt(self, "重命名设置", "请输入起始编号:", value=1, min=0)
    if not ok:
        return
        
    try:
        exported_count = 0
        # 按照图片名称排序进行重命名
        sorted_images = sorted(self.image_processor.images.items())
        
        for index, (image_name, image_info) in enumerate(sorted_images):
            # 生成新的文件名
            new_number = start_num + index
            new_image_name = f"{prefix}_{new_number:04d}"  # 使用4位数字格式，如0001, 0002...
            
            # 原始文件路径
            original_image_path = image_info['image_path']
            original_tag_path = image_info['tag_path']
            
            # 新文件路径
            _, image_ext = os.path.splitext(original_image_path)
            new_image_path = os.path.join(target_folder, new_image_name + image_ext)
            new_tag_path = os.path.join(target_folder, new_image_name + '.txt')
            
            # 复制图片文件（注意：这里使用复制，不会修改原始文件）
            if os.path.exists(original_image_path):
                from shutil import copy2
                copy2(original_image_path, new_image_path)
                
                # 如果标签文件存在，也一并复制
                if os.path.exists(original_tag_path):
                    copy2(original_tag_path, new_tag_path)
                else:
                    # 如果标签文件不存在，创建一个空的标签文件
                    with open(new_tag_path, 'w', encoding='utf-8') as f:
                        pass  # 创建空文件
                
                exported_count += 1
                
        QMessageBox.information(self, "导出完成", f"成功导出 {exported_count} 个文件对到:\n{target_folder}\n\n注意：原始文件未被修改")
        
    except Exception as e:
        QMessageBox.critical(self, "导出失败", f"导出过程中发生错误:\n{str(e)}")
def refresh_current_view(self):
    """
    刷新当前视图，重新加载当前选中图片的标签显示和缩略图
    """
    # 重新加载当前选中图片的标签显示
    if self.current_image_name:
        self.update_tag_checkboxes()
        
    # 重新生成选中图片的缩略图
    for image_name in self.selected_images:
        # 从缓存中移除旧的缩略图
        if image_name in self.image_processor.thumbnail_cache:
            del self.image_processor.thumbnail_cache[image_name]
        # 重新加载缩略图
        self.image_processor.load_thumbnail_async(image_name)
        
    # 如果当前图片在选中列表中，也需要刷新其缩略图
    if self.current_image_name and self.current_image_name not in self.selected_images:
        # 从缓存中移除旧的缩略图
        if self.current_image_name in self.image_processor.thumbnail_cache:
            del self.image_processor.thumbnail_cache[self.current_image_name]
        # 重新加载缩略图
        self.image_processor.load_thumbnail_async(self.current_image_name)
        
    # 更新统计信息
    self.update_statistics()
# 保存预设标签
def save_preset_tags(self):
    tags_text = self.preset_tag_input.text()
    if tags_text:
        # 将新标签组添加到现有标签列表中
        new_tags = [tag.strip() for tag in tags_text.split(",") if tag.strip()]
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
    if not self.current_image_name:
        QMessageBox.warning(self, "警告", "请先选择一张图片")
        return
        
    tag_content = self.image_processor.get_tag_content(self.current_image_name)
    tags = [t.strip() for t in tag_content.split(',') if t.strip()]
    
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
    self.image_processor.save_tags_to_image(self.current_image_name, tags)
    
    # 刷新界面
    self.refresh_current_view()
    
    if added_tags:
        QMessageBox.information(self, "成功", f"已将标签组添加到当前图片: {', '.join(added_tags)}")
    else:
        QMessageBox.information(self, "提示", "标签组中的标签已全部存在于当前图片中")
def delete_selected_images(self):
    """
    删除选中的图片及其对应的标签文件
    """
    selected_items = self.file_list.selectedItems()
    if not selected_items:
        QMessageBox.warning(self, "警告", "请先选择要删除的图片")
        return
        
    # 检查是否已经选择了"不再提示"
    if not hasattr(self, '_skip_delete_confirm') or not self._skip_delete_confirm:
        # 确认删除操作
        msg_box = QMessageBox(QMessageBox.Question, "确认删除", 
                            f"确定要删除选中的 {len(selected_items)} 个图片文件及其标签文件吗？\n\n注意：这将从磁盘上永久删除这些文件！",
                            parent=self)
        msg_box.addButton("删除", QMessageBox.YesRole)
        msg_box.addButton("取消", QMessageBox.NoRole)
        
        # 添加"不再提示"复选框
        checkbox = QCheckBox("不再提示")
        msg_box.setCheckBox(checkbox)
        
        result = msg_box.exec_()
        
        # 如果用户勾选了"不再提示"，则保存这个选择
        if checkbox.isChecked():
            self._skip_delete_confirm = True
            
        # 如果用户点击了取消，则返回
        if result != 0:  # 0 是"删除"按钮的索引
            return
    
    # 保存当前选中项的索引，以便删除后选中下一项
    if self.file_list.currentRow() >= 0:
        current_index = self.file_list.currentRow()
    else:
        current_index = 0
        
    deleted_count = 0
    for item in selected_items:
        image_name = item.text()
        if image_name in self.image_processor.images:
            image_info = self.image_processor.images[image_name]
            image_path = image_info['image_path']
            tag_path = image_info['tag_path']
            
            # 删除图片文件
            if os.path.exists(image_path):
                try:
                    os.remove(image_path)
                except Exception as e:
                    QMessageBox.warning(self, "删除失败", f"无法删除图片文件 {image_path}: {str(e)}")
                    continue
            
            # 删除标签文件（如果存在）
            if os.path.exists(tag_path):
                try:
                    os.remove(tag_path)
                except Exception as e:
                    QMessageBox.warning(self, "删除失败", f"无法删除标签文件 {tag_path}: {str(e)}")
            
            # 从数据结构中移除
            del self.image_processor.images[image_name]
            if image_name in self.thumbnail_items:
                del self.thumbnail_items[image_name]
            if image_name in self.image_processor.thumbnail_cache:
                del self.image_processor.thumbnail_cache[image_name]
            
            deleted_count += 1
    
    # 更新UI
    self.update_file_list()
    self.update_statistics()
    
    # 自动选中下一张图片
    if self.file_list.count() > 0:
        # 确保索引在有效范围内
        next_index = min(current_index, self.file_list.count() - 1)
        self.file_list.setCurrentRow(next_index)
        # 确保焦点在文件列表上，以便键盘事件生效
        self.file_list.setFocus()
        # 强制激活窗口以确保键盘事件被正确捕获
        self.activateWindow()
        
    # 只有当用户没有选择"不再提示"时才显示删除成功的弹窗
    if not hasattr(self, '_skip_delete_confirm') or not self._skip_delete_confirm:
        QMessageBox.information(self, "删除成功", f"成功删除了 {deleted_count} 个图片文件")