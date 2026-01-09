import os
from PyQt5.QtWidgets import (QFileDialog, QMessageBox,
                             QCheckBox, QListWidgetItem,
                             QInputDialog)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSize
# 文件操作相关功能
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
    prefix_dialog = QInputDialog(self)
    prefix_dialog.setWindowTitle("重命名设置")
    prefix_dialog.setLabelText("请输入文件名前缀:")
    prefix_dialog.setTextValue("image")
    # 增大弹窗尺寸
    prefix_dialog.resize(400, 200)
    # 应用全局字体设置
    prefix_dialog.setFont(self.font())
    ok = prefix_dialog.exec_()
    prefix = prefix_dialog.textValue()
    
    if not ok:
        return
        
    # 获取起始编号
    start_num_dialog = QInputDialog(self)
    start_num_dialog.setWindowTitle("重命名设置")
    start_num_dialog.setLabelText("请输入起始编号:")
    start_num_dialog.setIntValue(1)
    start_num_dialog.setIntMinimum(0)
    # 增大弹窗尺寸
    start_num_dialog.resize(400, 200)
    # 应用全局字体设置
    start_num_dialog.setFont(self.font())
    ok = start_num_dialog.exec_()
    start_num = start_num_dialog.intValue()
    
    if not ok:
        return

    # 询问是否要打乱文件命名顺序
    shuffle_reply = QMessageBox.question(self, "打乱顺序", 
                                       "是否要打乱文件命名顺序？\n选择是将随机打乱文件的编号顺序。",
                                       QMessageBox.Yes | QMessageBox.No, 
                                       QMessageBox.No)
    shuffle_order = (shuffle_reply == QMessageBox.Yes)
        
    try:
        exported_count = 0
        # 按照图片名称排序进行重命名
        sorted_images = list(self.image_processor.images.items())
        
        # 如果需要打乱顺序，则随机打乱列表
        if shuffle_order:
            import random
            random.shuffle(sorted_images)
        
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

def update_file_list(self):
    self.file_list.clear()
    self.thumbnail_items.clear()
    
    # 添加所有文件项（无缩略图）
    for image_name in self.image_processor.images.keys():
        item = QListWidgetItem(image_name)
        item.setIcon(QIcon())  # 先设置空图标
        # 设置合适的图标大小和文本位置，解决部分区域无法点击的问题
        item.setSizeHint(QSize(350, 370))  # 调整项目大小，应该与网格大小匹配，高度略大于网格大小以容纳文字
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