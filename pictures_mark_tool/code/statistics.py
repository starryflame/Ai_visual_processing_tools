# 统计功能
import os
from PyQt5.QtWidgets import (QTreeWidgetItem)
import re


# 更新标签统计信息
def update_tag_statistics(self):
    self.tag_statistics = {}
    
    # 统计每个标签出现的频率
    for image_name in self.selected_images:
        tag_content = self.image_processor.get_tag_content(image_name)
        # 修改: 使用逗号分隔标签，支持中英文逗号
        tags = [tag.strip() for tag in re.split('[,，]', tag_content) if tag.strip()]
        
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
    
    # 添加统计信息为树形结构，按词频排序
    for word, count in sorted(self.tag_statistics.items(), key=lambda x: x[1], reverse=True):
        percentage = count / len(self.selected_images) * 100 if self.selected_images else 0
        item = QTreeWidgetItem([word, str(count), f"{percentage:.1f}%"])
        self.stats_tree.addTopLevelItem(item)

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