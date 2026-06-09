# 批量操作功能
# 全选图片
def select_all_images(self):
    self.file_list.selectAll()
    
# 取消全选
def deselect_all_images(self):
    self.file_list.clearSelection()