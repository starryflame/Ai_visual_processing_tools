"""
标签管理模块
处理标签文件的加载、保存、自动创建等功能
"""
import os
from PyQt5.QtWidgets import QMessageBox


class LabelManagerMixin:
    """标签管理功能混入类"""

    def update_label_preview(self, base_name):
        """更新标签预览内容"""
        if not self.current_folder:
            return

        media_file = self.media_files[self.current_index]
        media_full_path = self.media_files_full_path[self.current_index]

        # 查找标签文件
        self.current_label_file = self._find_label_file(media_file, media_full_path)

        if self.current_label_file:
            try:
                with open(self.current_label_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.label_content.setPlainText(content)
                self.label_modified = False
                self.update_save_status()
            except Exception as e:
                self.label_content.setPlainText(f"无法读取标签文件：{str(e)}")
                self.current_label_file = None
                self.label_modified = False
                self.update_save_status()
        else:
            self.label_content.setPlainText("未找到对应的标签文件")
            self.current_label_file = None
            self.label_modified = False
            self.update_save_status()

    def _find_label_file(self, media_file, media_full_path):
        """查找标签文件"""
        from utils import find_label_file
        return find_label_file(media_file, media_full_path)

    def on_label_text_changed(self):
        """标签内容改变时的回调函数"""
        self.label_modified = True
        self.update_save_status()

    def update_save_status(self):
        """更新保存状态显示"""
        if self.label_modified and self.current_label_file:
            self.save_status_label.setText("● 未保存")
            self.save_status_label.setStyleSheet("""
                QLabel {
                    color: #f44336;
                    font-style: italic;
                    font-size: 12px;
                    padding: 2px;
                }
            """)
        elif self.current_label_file:
            self.save_status_label.setText("✓ 已保存")
            self.save_status_label.setStyleSheet("""
                QLabel {
                    color: #4CAF50;
                    font-style: italic;
                    font-size: 12px;
                    padding: 2px;
                }
            """)
        else:
            self.save_status_label.setText("")

    def save_current_label(self):
        """保存当前标签内容"""
        if self.current_label_file and self.label_modified:
            try:
                content = self.label_content.toPlainText()
                with open(self.current_label_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.label_modified = False
                self.update_save_status()
                return True
            except Exception as e:
                QMessageBox.warning(self, "保存失败", f"无法保存标签文件：{str(e)}")
                return False
        return True

    def auto_create_label_if_needed(self):
        """自动创建标签文件（如果没有且有内容）"""
        if (self.current_label_file is None and
                self.label_modified and
                self.current_index >= 0 and
                len(self.media_files) > 0):

            current_media_file = self.media_files[self.current_index]
            current_media_path = self.media_files_full_path[self.current_index]
            media_dir = os.path.dirname(current_media_path)
            base_name = os.path.splitext(os.path.basename(current_media_file))[0]

            new_label_file = os.path.join(media_dir, base_name + '.txt')

            try:
                content = self.label_content.toPlainText()
                with open(new_label_file, 'w', encoding='utf-8') as f:
                    f.write(content)

                self.current_label_file = new_label_file
                self.label_modified = False
                self.update_save_status()

                print(f"自动创建标签文件：{new_label_file}")

            except Exception as e:
                QMessageBox.warning(self, "创建标签文件失败", f"无法创建标签文件：{str(e)}")
