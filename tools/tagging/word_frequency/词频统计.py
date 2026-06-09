import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import re
from collections import Counter
import threading
# 添加PIL库导入
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    messagebox.showwarning("警告", "未安装PIL库，图片预览功能受限")

# 添加sys和requests导入以支持AI功能
import sys
import io
import base64
import logging
import configparser
from openai import OpenAI
from PIL import Image as PILImage

class LabelAnalyzer:
    def __init__(self, root):
        self.root = root
        self.root.title("图片标签分析工具")
        self.root.geometry("1200x800")
        
        # 数据存储
        self.image_files = []
        self.label_files = []
        self.current_index = 0
        self.all_labels_content = ""
        # 新增: 存储所有标签内容的列表，提高查询效率
        self.all_labels_list = []
        self.word_frequency = Counter()
        
        self.setup_ui()
        
    def setup_ui(self):
        # 主框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 顶部框架 - 文件夹选择
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(top_frame, text="数据文件夹:").pack(side=tk.LEFT)
        self.folder_path_var = tk.StringVar()
        ttk.Entry(top_frame, textvariable=self.folder_path_var, width=50).pack(side=tk.LEFT, padx=(5, 5))
        ttk.Button(top_frame, text="浏览", command=self.browse_folder).pack(side=tk.LEFT)
        ttk.Button(top_frame, text="加载数据", command=self.load_data).pack(side=tk.LEFT, padx=(5, 0))
        
        # 中间主要内容框架 - 使用PanedWindow实现可拖拽调整大小
        content_paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        content_paned_window.pack(fill=tk.BOTH, expand=True)
        
        # 左侧框架 - 图片和标签显示
        left_frame = ttk.Frame(content_paned_window)
        content_paned_window.add(left_frame, weight=1)
        
        # 右侧框架 - 词频统计和操作
        right_frame = ttk.Frame(content_paned_window, width=400)
        content_paned_window.add(right_frame, weight=1)
        
        # 在左侧框架内创建垂直方向的PanedWindow，以便图片和标签区域可以调整大小
        left_paned_window = ttk.PanedWindow(left_frame, orient=tk.VERTICAL)
        left_paned_window.pack(fill=tk.BOTH, expand=True)
        
        # 图片显示区域框架
        image_frame = ttk.Frame(left_paned_window)
        left_paned_window.add(image_frame, weight=1)
        
        # 标签显示区域框架
        label_frame = ttk.Frame(left_paned_window)
        left_paned_window.add(label_frame, weight=1)
        
        # 图片显示区域
        ttk.Label(image_frame, text="图片预览:").pack(anchor=tk.W)
        self.image_canvas = tk.Canvas(image_frame, bg="lightgray", height=300)
        self.image_canvas.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 标签内容显示区域
        ttk.Label(label_frame, text="标签内容:").pack(anchor=tk.W)
        # 修改: 将Text控件设置为可编辑状态，不再只读
        self.label_text = tk.Text(label_frame, height=10)
        self.label_text.pack(fill=tk.BOTH, expand=True)
        
        # 导航按钮
        nav_frame = ttk.Frame(label_frame)
        nav_frame.pack(fill=tk.X, pady=(5, 0))
        self.prev_btn = ttk.Button(nav_frame, text="上一个", command=self.previous_item, state=tk.DISABLED)
        self.prev_btn.pack(side=tk.LEFT)
        self.next_btn = ttk.Button(nav_frame, text="下一个", command=self.next_item, state=tk.DISABLED)
        self.next_btn.pack(side=tk.RIGHT)
        self.position_label = ttk.Label(nav_frame, text="0 / 0")
        self.position_label.pack()
        
        # 词频统计标题
        ttk.Label(right_frame, text="词频统计:", font=("Arial", 12, "bold")).pack(anchor=tk.W)
        
        # 词频显示区域
        freq_frame = ttk.Frame(right_frame)
        freq_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建滚动条和列表框
        scrollbar = ttk.Scrollbar(freq_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 修改: 将Listbox改为可点击的Listbox，并绑定双击事件
        self.freq_listbox = tk.Listbox(freq_frame, yscrollcommand=scrollbar.set)
        self.freq_listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.freq_listbox.yview)
        # 绑定双击事件
        self.freq_listbox.bind('<Double-Button-1>', self.on_freq_listbox_double_click)
        # 存储句子与文件索引的映射关系
        self.sentence_to_index_map = []
        
        # 操作区域
        operation_frame = ttk.LabelFrame(right_frame, text="批量操作", padding=10)
        operation_frame.pack(fill=tk.X, pady=(10, 0))
        
        # 输入框和按钮
        ttk.Label(operation_frame, text="查找文本:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(operation_frame, textvariable=self.search_var)
        search_entry.grid(row=1, column=0, columnspan=2, sticky=tk.EW, pady=(0, 10))
        # 绑定实时监听事件
        #self.search_var.trace_add("write", self.on_search_text_change)
        
        ttk.Label(operation_frame, text="替换为:").grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        self.replace_var = tk.StringVar()
        ttk.Entry(operation_frame, textvariable=self.replace_var).grid(row=3, column=0, columnspan=2, sticky=tk.EW, pady=(0, 10))
        
        operation_frame.columnconfigure(1, weight=1)
        
        # 操作按钮
        btn_frame = ttk.Frame(operation_frame)
        btn_frame.grid(row=4, column=0, columnspan=2, sticky=tk.EW, pady=(0, 5))
        btn_frame.columnconfigure((0, 1), weight=1)
        
        ttk.Button(btn_frame, text="统计频率", command=self.calculate_frequency).grid(row=0, column=0, padx=(0, 5), sticky=tk.EW)
        ttk.Button(btn_frame, text="执行替换", command=self.perform_replace).grid(row=0, column=1, padx=(5, 0), sticky=tk.EW)
        
        ttk.Button(operation_frame, text="删除匹配项", command=self.perform_delete).grid(row=5, column=0, columnspan=2, sticky=tk.EW, pady=(0, 5))
        ttk.Button(operation_frame, text="保存更改", command=self.save_changes).grid(row=6, column=0, columnspan=2, sticky=tk.EW)
        
        # 添加AI生成功能区域
        ai_frame = ttk.LabelFrame(right_frame, text="AI提示词生成", padding=10)
        ai_frame.pack(fill=tk.X, pady=(10, 0))
        
        # 当前图片重新生成按钮
        ttk.Button(ai_frame, text="重新生成当前图片提示词", command=self.regenerate_current_caption).pack(fill=tk.X, pady=(0, 5))
        
        # 关键词筛选重新生成
        keyword_frame = ttk.Frame(ai_frame)
        keyword_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(keyword_frame, text="关键词:").pack(anchor=tk.W)
        self.keyword_var = tk.StringVar()
        ttk.Entry(keyword_frame, textvariable=self.keyword_var).pack(fill=tk.X)
        ttk.Button(keyword_frame, text="重新生成含关键词图片提示词", 
                  command=self.regenerate_keyword_captions).pack(fill=tk.X, pady=(5, 0))
        
        # 字数筛选重新生成
        wordcount_frame = ttk.Frame(ai_frame)
        wordcount_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(wordcount_frame, text="重新生成字数少于:").pack(anchor=tk.W)
        wordcount_subframe = ttk.Frame(wordcount_frame)
        wordcount_subframe.pack(fill=tk.X)
        self.wordcount_var = tk.StringVar(value="10")
        ttk.Entry(wordcount_subframe, textvariable=self.wordcount_var, width=10).pack(side=tk.LEFT)
        ttk.Label(wordcount_subframe, text=" 字的提示词").pack(side=tk.LEFT)
        ttk.Button(wordcount_frame, text="执行", command=self.regenerate_short_captions).pack(fill=tk.X, pady=(5, 0))
        
    def browse_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.folder_path_var.set(folder_selected)
            
    def load_data(self):
        folder_path = self.folder_path_var.get()
        if not folder_path:
            messagebox.showerror("错误", "请选择数据文件夹")
            return
            
        if not os.path.exists(folder_path):
            messagebox.showerror("错误", "文件夹不存在")
            return
            
        # 清空之前的数据
        self.image_files.clear()
        self.label_files.clear()
        self.all_labels_list.clear()  # 清空标签内容列表
        
        # 查找图片和标签文件
        for file in os.listdir(folder_path):
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                image_path = os.path.join(folder_path, file)
                label_path = os.path.join(folder_path, os.path.splitext(file)[0] + '.txt')
                
                if os.path.exists(label_path):
                    self.image_files.append(image_path)
                    self.label_files.append(label_path)
        
        if not self.image_files:
            messagebox.showwarning("警告", "未找到匹配的图片和标签文件")
            return
            
        self.current_index = 0
        self.display_current_item()
        self.prev_btn.config(state=tk.NORMAL if len(self.image_files) > 1 else tk.DISABLED)
        self.next_btn.config(state=tk.NORMAL if len(self.image_files) > 1 else tk.DISABLED)
        
        # 加载所有标签内容用于词频统计
        self.load_all_labels()
        # 自动显示全局词频统计
        self.display_global_frequency()
        messagebox.showinfo("成功", f"已加载 {len(self.image_files)} 个图片和标签文件")
        
    def load_all_labels(self):
        self.all_labels_content = ""
        self.all_labels_list.clear()  # 清空列表
        for label_file in self.label_files:
            try:
                with open(label_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self.all_labels_content += content + "\n"
                    # 新增: 将每个文件的内容存储到列表中，便于后续快速访问
                    self.all_labels_list.append(content)
            except Exception as e:
                print(f"读取文件 {label_file} 出错: {e}")
                self.all_labels_list.append("")  # 出错时添加空字符串占位
                
    def calculate_frequency(self):
            if not self.all_labels_content:
                messagebox.showwarning("警告", "没有标签数据可供分析")
                return
                
            search_text = self.search_var.get().strip()
            if not search_text:
                # 如果没有输入特定文本，则显示全局词频统计
                self.display_global_frequency()
                return
                
            # 统计频率 - 直接在内存中操作，提高效率
            count = self.all_labels_content.count(search_text)
            
            # 更新列表框
            self.freq_listbox.delete(0, tk.END)
            self.sentence_to_index_map.clear()  # 清空映射关系
            
            # 添加标题行并记录映射关系
            self.freq_listbox.insert(tk.END, f"'{search_text}' 出现次数: {count}")
            self.sentence_to_index_map.append(-1)  # 标题行不对应任何文件
            
            # 显示包含该词语的句子
            sentences = self.find_sentences_with_word_fast(search_text)
            if sentences:
                self.freq_listbox.insert(tk.END, "")
                self.sentence_to_index_map.append(-1)  # 空行不对应任何文件
                self.freq_listbox.insert(tk.END, f"包含'{search_text}'的句子:")
                self.sentence_to_index_map.append(-1)  # 标题行不对应任何文件
                self.freq_listbox.insert(tk.END, "-" * 30)
                self.sentence_to_index_map.append(-1)  # 分隔行不对应任何文件
                
                # 使用集合去重，但保持顺序
                seen_sentences = set()
                unique_sentences = []
                for sentence in sentences:
                    if sentence not in seen_sentences:
                        seen_sentences.add(sentence)
                        unique_sentences.append(sentence)
                
                for i, sentence in enumerate(unique_sentences[:]):  # 不限制显示句子
                    self.freq_listbox.insert(tk.END, f"{i+1}. {sentence}")
                    # 在统计时就记录句子与文件的映射关系
                    found = False
                    # 优化: 使用已加载到内存中的标签列表进行查找
                    for idx, content in enumerate(self.all_labels_list):
                        if sentence in content:
                            self.sentence_to_index_map.append(idx)
                            found = True
                            break
                    if not found:
                        self.sentence_to_index_map.append(-1)  # 无法定位到文件
            
            
    # 新增: 更高效的句子查找方法
    def find_sentences_with_word_fast(self, word):
        """
        查找包含指定词语的所有句子 - 优化版本
        """
        if not word or not self.all_labels_content:
            return []
        
        matched_sentences = []
        # 优化: 直接在已加载的标签列表中查找，避免重复读取文件
        for content in self.all_labels_list:
            if word in content:
                # 使用正则表达式按照中英文标点符号分割句子
                sentences = re.split(r'([。！？；，.!?,;])', content)
                
                # 重构句子，将标点符号与前面的内容合并
                reconstructed_sentences = []
                for i in range(0, len(sentences)-1, 2):
                    if i+1 < len(sentences):
                        sentence = sentences[i].strip() + sentences[i+1].strip()
                    else:
                        sentence = sentences[i].strip()
                    if sentence:  # 只添加非空句子
                        reconstructed_sentences.append(sentence)
                
                # 如果最后还有剩余内容且不为空，则也加入
                if len(sentences) % 2 == 1 and sentences[-1].strip():
                    reconstructed_sentences.append(sentences[-1].strip())
                
                # 查找包含指定词语的句子
                for sentence in reconstructed_sentences:
                    if word in sentence and sentence.strip():  # 确保句子不为空
                        matched_sentences.append(sentence.strip())
                        
        return matched_sentences

    def display_current_item(self):
        if not self.image_files:
            return
            
        # 显示图片
        image_path = self.image_files[self.current_index]
        self.image_canvas.delete("all")
        
        # 如果有PIL库则显示实际图片，否则显示文本提示
        if PIL_AVAILABLE:
            try:
                # 打开并调整图片大小以适应画布
                img = Image.open(image_path)
                canvas_width = self.image_canvas.winfo_width()
                canvas_height = self.image_canvas.winfo_height()
                
                # 如果画布尺寸为1，则使用默认高度300
                if canvas_width <= 1:
                    canvas_width = 400
                if canvas_height <= 1:
                    canvas_height = 300
                
                # 调整图片大小
                img.thumbnail((canvas_width, canvas_height), Image.LANCZOS)
                self.photo = ImageTk.PhotoImage(img)
                
                # 在画布中心显示图片
                self.image_canvas.create_image(canvas_width//2, canvas_height//2, image=self.photo)
            except Exception as e:
                self.image_canvas.create_text(
                    self.image_canvas.winfo_width()//2,
                    self.image_canvas.winfo_height()//2,
                    text=f"无法加载图片: {os.path.basename(image_path)}\n错误: {str(e)}",
                    justify=tk.CENTER
                )
        else:
            self.image_canvas.create_text(
                self.image_canvas.winfo_width()//2,
                self.image_canvas.winfo_height()//2,
                text=f"图片: {os.path.basename(image_path)}\n\n(安装PIL库可获得完整预览功能)",
                justify=tk.CENTER
            )
        
        # 显示标签内容
        label_path = self.label_files[self.current_index]
        try:
            with open(label_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.label_text.delete(1.0, tk.END)
            self.label_text.insert(1.0, content)
        except Exception as e:
            self.label_text.delete(1.0, tk.END)
            self.label_text.insert(1.0, f"无法读取标签文件: {e}")
            
        # 更新位置标签
        self.position_label.config(text=f"{self.current_index + 1} / {len(self.image_files)}")
        
    def previous_item(self):
        if self.image_files and self.current_index > 0:
            self.current_index -= 1
            self.display_current_item()
            
    def next_item(self):
        if self.image_files and self.current_index < len(self.image_files) - 1:
            self.current_index += 1
            self.display_current_item()
            
    def perform_replace(self):
        search_text = self.search_var.get().strip()
        replace_text = self.replace_var.get()
        
        if not search_text:
            messagebox.showwarning("警告", "请输入要替换的文本")
            return
            
        if not self.label_files:
            messagebox.showwarning("警告", "没有加载标签文件")
            return
            
        # 执行替换
        replaced_count = 0
        # 优化: 同时更新内存中的标签内容列表
        for i, label_file in enumerate(self.label_files):
            try:
                content = self.all_labels_list[i]  # 从内存中获取内容
                
                if search_text in content:
                    new_content = content.replace(search_text, replace_text)
                    with open(label_file, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    # 更新内存中的内容
                    self.all_labels_list[i] = new_content
                    replaced_count += 1
            except Exception as e:
                print(f"处理文件 {label_file} 出错: {e}")
                
        # 重新构建所有标签内容字符串
        self.all_labels_content = "\n".join(self.all_labels_list) + "\n"
        # 更新当前显示
        self.display_current_item()
        # 更新全局词频统计
        self.display_global_frequency()
        
        messagebox.showinfo("完成", f"已在 {replaced_count} 个文件中执行替换操作")
        
    def perform_delete(self):
        search_text = self.search_var.get().strip()
        
        if not search_text:
            messagebox.showwarning("警告", "请输入要删除的文本")
            return
            
        if not messagebox.askyesno("确认", f"确定要从所有标签中删除 '{search_text}' 吗?"):
            return
            
        if not self.label_files:
            messagebox.showwarning("警告", "没有加载标签文件")
            return
            
        # 执行删除
        deleted_count = 0
        # 优化: 同时更新内存中的标签内容列表
        for i, label_file in enumerate(self.label_files):
            try:
                content = self.all_labels_list[i]  # 从内存中获取内容
                
                if search_text in content:
                    new_content = content.replace(search_text, '')
                    with open(label_file, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    # 更新内存中的内容
                    self.all_labels_list[i] = new_content
                    deleted_count += 1
            except Exception as e:
                print(f"处理文件 {label_file} 出错: {e}")
                
        # 重新构建所有标签内容字符串
        self.all_labels_content = "\n".join(self.all_labels_list) + "\n"
        # 更新当前显示
        self.display_current_item()
        # 更新全局词频统计
        self.display_global_frequency()
        
        messagebox.showinfo("完成", f"已在 {deleted_count} 个文件中执行删除操作")
        
    def save_changes(self):
        # 获取当前编辑的标签内容并保存
        if 0 <= self.current_index < len(self.label_files):
            label_path = self.label_files[self.current_index]
            content = self.label_text.get(1.0, tk.END)
            
            try:
                with open(label_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                # 更新内存中的内容
                self.all_labels_list[self.current_index] = content
                # 更新全局标签内容字符串
                self.all_labels_content = "\n".join(self.all_labels_list) + "\n"
                # 更新全局词频统计
                self.display_global_frequency()
                messagebox.showinfo("成功", "已保存更改")
            except Exception as e:
                messagebox.showerror("错误", f"保存失败: {e}")
                
    # 添加AI生成功能
    def regenerate_current_caption(self):
        """重新生成当前图片的提示词"""
        if not self.image_files:
            messagebox.showwarning("警告", "没有加载图片文件")
            return
            
        # 显示确认对话框
        if not messagebox.askyesno("确认", "确定要重新生成当前图片的提示词吗？这将覆盖现有内容。"):
            return
            
        try:
            # 获取当前图片和标签路径
            image_path = self.image_files[self.current_index]
            label_path = self.label_files[self.current_index]
            
            # 生成新的提示词
            new_caption = self.generate_caption_with_ai(image_path)
            
            # 保存新提示词
            with open(label_path, 'w', encoding='utf-8') as f:
                f.write(new_caption)
            
            # 更新显示
            self.label_text.delete(1.0, tk.END)
            self.label_text.insert(1.0, new_caption)
            
            # 更新全局标签内容
            self.load_all_labels()
            self.display_global_frequency()
            
            messagebox.showinfo("成功", "已重新生成并保存提示词")
        except Exception as e:
            messagebox.showerror("错误", f"生成提示词失败: {str(e)}")
            
    def regenerate_keyword_captions(self):
        """重新生成包含关键词的图片提示词"""
        keyword = self.keyword_var.get().strip()
        if not keyword:
            messagebox.showwarning("警告", "请输入关键词")
            return
            
        # 查找包含关键词的标签文件
        matching_indices = []
        for i, label_path in enumerate(self.label_files):
            try:
                with open(label_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                if keyword in content:
                    matching_indices.append(i)
            except Exception as e:
                print(f"读取文件 {label_path} 出错: {e}")
                
        if not matching_indices:
            messagebox.showinfo("信息", f"未找到包含关键词 '{keyword}' 的图片")
            return
            
        # 确认操作
        if not messagebox.askyesno("确认", f"找到 {len(matching_indices)} 个包含关键词 '{keyword}' 的图片，确定要重新生成它们的提示词吗？"):
            return
            
        # 处理每个匹配的图片
        success_count = 0
        for i in matching_indices:
            try:
                image_path = self.image_files[i]
                label_path = self.label_files[i]
                
                # 生成新的提示词
                new_caption = self.generate_caption_with_ai(image_path)
                
                # 保存新提示词
                with open(label_path, 'w', encoding='utf-8') as f:
                    f.write(new_caption)
                    
                success_count += 1
            except Exception as e:
                print(f"处理图片 {self.image_files[i]} 时出错: {e}")
                
        # 更新全局标签内容
        self.load_all_labels()
        self.display_global_frequency()
        
        # 如果当前显示的图片被更新了，刷新显示
        if self.current_index in matching_indices:
            self.display_current_item()
            
        messagebox.showinfo("完成", f"已成功重新生成 {success_count} 个提示词")
        
    def regenerate_short_captions(self):
        """重新生成字数少于指定数量的提示词"""
        try:
            max_length = int(self.wordcount_var.get())
        except ValueError:
            messagebox.showwarning("警告", "请输入有效的数字")
            return
            
        # 查找字数少于指定数量的标签文件
        short_indices = []
        for i, label_path in enumerate(self.label_files):
            try:
                with open(label_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                if len(content) < max_length:
                    short_indices.append(i)
            except Exception as e:
                print(f"读取文件 {label_path} 出错: {e}")
                
        if not short_indices:
            messagebox.showinfo("信息", f"未找到字数少于 {max_length} 的提示词")
            return
            
        # 确认操作
        if not messagebox.askyesno("确认", f"找到 {len(short_indices)} 个字数少于 {max_length} 的提示词，确定要重新生成它们吗？"):
            return
            
        # 处理每个短提示词
        success_count = 0
        for i in short_indices:
            try:
                image_path = self.image_files[i]
                label_path = self.label_files[i]
                
                # 生成新的提示词
                new_caption = self.generate_caption_with_ai(image_path)
                
                # 保存新提示词
                with open(label_path, 'w', encoding='utf-8') as f:
                    f.write(new_caption)
                    
                success_count += 1
            except Exception as e:
                print(f"处理图片 {self.image_files[i]} 时出错: {e}")
                
        # 更新全局标签内容
        self.load_all_labels()
        self.display_global_frequency()
        
        # 如果当前显示的图片被更新了，刷新显示
        if self.current_index in short_indices:
            self.display_current_item()
            
        messagebox.showinfo("完成", f"已成功重新生成 {success_count} 个提示词")
        
    def generate_caption_with_ai(self, image_path):
        """使用AI为指定图片生成提示词"""
        try:
            # 打开并调整图片大小
            image = PILImage.open(image_path).convert('RGB')
            max_size = (1024, 1024)
            image.thumbnail(max_size, PILImage.Resampling.LANCZOS)
            
            # 转换图片为base64格式
            buffered = io.BytesIO()
            image.save(buffered, format="PNG")
            encoded = base64.b64encode(buffered.getvalue()).decode("utf-8")
            data_url = f"data:image/png;base64,{encoded}"
            
            # 从配置中获取Ollama API设置
            api_base_url = "http://127.0.0.1:11434/v1"  # Ollama默认值
            api_key = "ollama"  # Ollama默认值
            model_name = "qwen3-vl:30b"  # Ollama模型名称
            
            # 尝试从配置文件读取设置
            config_path = os.path.join(os.path.dirname(__file__), '..', 'code', 'config.ini')
            filter_words = []  # 过滤词列表
            if os.path.exists(config_path):
                config = configparser.ConfigParser()
                config.read(config_path, encoding='utf-8')
                if 'OLLAMA' in config:  # 修改为从OLLAMA节读取配置
                    api_base_url = config.get('OLLAMA', 'api_base_url', fallback=api_base_url)
                    api_key = config.get('OLLAMA', 'api_key', fallback=api_key)
                    model_name = config.get('OLLAMA', 'model_name', fallback=model_name)
                
                # 读取过滤词列表
                if 'FILTER_WORDS' in config:
                    filter_words_str = config.get('FILTER_WORDS', 'words', fallback='')
                    if filter_words_str:
                        filter_words = [word.strip().lower() for word in filter_words_str.split(',') if word.strip()]
            
            # 初始化客户端
            client = OpenAI(
                api_key=api_key,
                base_url=api_base_url,
                timeout=3600
            )
            
            # 使用默认提示词
            prompt_text = '你是一名专业的图片内容描述大师，用最大胆直白的语言和明确清晰的句子描述，禁止隐瞒，暗示或者用笼统的词汇。详细全面描述画面里的所有元素。只输出内容本身，不要重复和输出其他内容，中文回答。'
            config_path = os.path.join(os.path.dirname(__file__), '..', 'code', 'config.ini')
            if os.path.exists(config_path):
                config = configparser.ConfigParser()
                config.read(config_path, encoding='utf-8')
                if 'PROMPTS' in config:
                    prompt_text = config.get('PROMPTS', 'image_prompt', fallback=prompt_text)
            
            # 构造消息
            content_list = [
                {
                    "type": "text",
                    "text": prompt_text
                },
                {
                    "type": "image_url",
                    "image_url": {"url": data_url}
                }
            ]
            
            messages = [{"role": "user", "content": content_list}]

            # 发送请求并检查生成的提示词长度
            max_attempts = 10  # 最多尝试10次
            for attempt in range(max_attempts):
                # 发送请求
                response = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    max_tokens=1024,
                    temperature=0.3,
                    top_p=0.9,
                )
                
                caption = response.choices[0].message.content.strip()
                
                # 检查是否包含过滤词
                contains_filter_word = False
                caption_lower = caption.lower()
                for word in filter_words:
                    if word in caption_lower:
                        contains_filter_word = True
                        print(f"生成的提示词包含过滤词 '{word}'，正在重新生成... (尝试 {attempt + 1}/{max_attempts})")
                        break
                
                # 如果包含过滤词且不是最后一次尝试，则重新生成
                if contains_filter_word and attempt < max_attempts - 1:
                    continue
                
                # 检查提示词长度，如果超过1000字则重新生成
                if len(caption) > 1000:
                    print(f"生成的提示词长度为 {len(caption)} 字，超过1000字限制，正在重新生成... (尝试 {attempt + 1}/{max_attempts})")
                    # 如果不是最后一次尝试，继续循环重新生成
                    if attempt < max_attempts - 1:
                        continue
                    else:
                        # 最后一次尝试后仍然超长，则截断并添加提示
                        print(f"经过 {max_attempts} 次尝试后，提示词长度仍超过1000字，将截断处理")
                        return caption[:1000] + "...(内容过长已截断)"
                
                # 检查提示词是否为空或少于10个字
                if len(caption) < 10:
                    print(f"生成的提示词长度为 {len(caption)} 字，少于10字，正在重新生成... (尝试 {attempt + 1}/{max_attempts})")
                    # 如果不是最后一次尝试，继续循环重新生成
                    if attempt < max_attempts - 1:
                        continue
                    else:
                        # 最后一次尝试后仍然太短，则返回默认提示
                        print(f"经过 {max_attempts} 次尝试后，提示词长度仍少于10字")
                        return "提示词内容过短，无法提供有效描述"
                
                # 如果不包含过滤词且长度符合要求，则返回结果
                if not contains_filter_word:
                    return caption
            
            # 如果所有尝试都包含过滤词，则在最后返回时移除过滤词
            print(f"经过 {max_attempts} 次尝试后，生成的提示词仍包含过滤词，将强制移除")
            for word in filter_words:
                caption = caption.replace(word, '')
            return caption.strip() or "提示词内容已被过滤"
            
        except Exception as e:
            raise Exception(f"使用AI生成提示词失败: {str(e)}")

    def on_search_text_change(self, *args):
        """当搜索文本改变时实时更新统计结果"""
        # 使用线程延迟执行，避免频繁触发
        if hasattr(self, '_after_id'):
            self.root.after_cancel(self._after_id)
        self._after_id = self.root.after(1000, self.calculate_frequency_delayed)
    
    def calculate_frequency_delayed(self):
        """延迟执行的词频统计"""
        # 检查是否有足够的内容再进行统计
        search_text = self.search_var.get().strip()
        if len(search_text) >= 1:  # 至少输入1个字符才开始统计
            self.calculate_frequency()
        elif len(search_text) == 0:  # 如果清空了输入框，显示全局词频统计
            self.display_global_frequency()

    def display_global_frequency(self):
        if not self.all_labels_content:
            return
            
        # 更新列表框
        self.freq_listbox.delete(0, tk.END)
        self.sentence_to_index_map.clear()  # 清空映射关系
        
        # 添加全局词频统计标题并记录映射关系
        self.freq_listbox.insert(tk.END, "全局词频统计 (前500个):")
        self.sentence_to_index_map.append(-1)  # 标题行不对应任何文件
        self.freq_listbox.insert(tk.END, "=" * 30)
        self.sentence_to_index_map.append(-1)  # 分隔行不对应任何文件
        
        # 提取中文词语和英文单词
        chinese_words = re.findall(r'[\u4e00-\u9fff]+', self.all_labels_content)
        english_words = re.findall(r'[a-zA-Z]+', self.all_labels_content)
        
        # 合并所有词语并统计频率
        all_words = chinese_words + english_words
        word_counts = Counter(all_words)
        
        # 显示前500个最常见的词并记录映射关系
        for word, cnt in word_counts.most_common(500):
            self.freq_listbox.insert(tk.END, f"  '{word}': {cnt}")
            self.sentence_to_index_map.append(-1)  # 词频统计不直接关联具体文件
    # 添加: 双击词频列表框项目的事件处理函数
    def on_freq_listbox_double_click(self, event):
        """处理词频列表框双击事件，跳转到对应的图片"""
        selection = self.freq_listbox.curselection()
        if not selection:
            return
            
        index = selection[0]
        if index < len(self.sentence_to_index_map):
            file_index = self.sentence_to_index_map[index]
            if file_index >= 0 and file_index < len(self.image_files):
                self.current_index = file_index
                self.display_current_item()
                # 更新导航按钮状态
                self.prev_btn.config(state=tk.NORMAL if self.current_index > 0 else tk.DISABLED)
                self.next_btn.config(state=tk.NORMAL if self.current_index < len(self.image_files) - 1 else tk.DISABLED)

# 添加程序启动入口
if __name__ == "__main__":
    root = tk.Tk()
    app = LabelAnalyzer(root)
    root.mainloop()