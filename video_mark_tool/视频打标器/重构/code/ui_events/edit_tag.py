# This is a method from class VideoTagger
import tkinter as tk
from tkinter import messagebox
def edit_tag(self):
    """编辑选中的标签"""
    selection = self.tag_listbox.curselection()
    if not selection:
        return
        
    index = selection[0]
    tag_info = self.tags[index]
    
    # 创建编辑窗口
    edit_window = tk.Toplevel(self.root)
    edit_window.title("编辑标签")
    edit_window.geometry("400x300")  # 增大窗口尺寸
    edit_window.transient(self.root)
    edit_window.grab_set()
    
    # 将窗口居中显示
    edit_window.update_idletasks()
    x = (edit_window.winfo_screenwidth() // 2) - (400 // 2)
    y = (edit_window.winfo_screenheight() // 2) - (300 // 2)
    edit_window.geometry(f"400x300+{x}+{y}")
    
    # 标签输入框
    tk.Label(edit_window, text="标签内容:", font=self.font).pack(pady=(20, 5))
    # 修改为支持多行文本的文本框
    tag_entry = tk.Text(edit_window, width=40, height=8, font=self.font)
    tag_entry.pack(pady=5, padx=20, fill=tk.BOTH, expand=True)
    tag_entry.insert("1.0", tag_info["tag"])
    tag_entry.focus()
    
    # 添加滚动条
    scrollbar = tk.Scrollbar(edit_window, command=tag_entry.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    tag_entry.config(yscrollcommand=scrollbar.set)
    
    # 按钮框架
    button_frame = tk.Frame(edit_window)
    button_frame.pack(pady=20)
    
    def save_edit():
        # 修改获取标签文本的方式
        new_tag = tag_entry.get("1.0", tk.END).strip()
        if not new_tag:
            messagebox.showerror("错误", "请输入标签文本", parent=edit_window)
            return
            
        # 更新数据
        self.tags[index]["tag"] = new_tag
        
        # 更新列表框显示
        start_frame = self.tags[index]["start"]
        end_frame = self.tags[index]["end"]
        self.tag_listbox.delete(index)
        self.tag_listbox.insert(index, f"帧 {start_frame}-{end_frame}: {new_tag}")
        self.tag_listbox.selection_set(index)
        
        # 更新标记可视化
        self.draw_tag_markers()
        
        edit_window.destroy()
        
    def cancel_edit():
        edit_window.destroy()
        
    tk.Button(button_frame, text="保存", command=save_edit, font=self.font).pack(side=tk.LEFT, padx=5)
    tk.Button(button_frame, text="取消", command=cancel_edit, font=self.font).pack(side=tk.LEFT, padx=5)

# Note: This was originally a method of class VideoTagger
# You may need to adjust the implementation based on class context
__all__ = ['edit_tag']
