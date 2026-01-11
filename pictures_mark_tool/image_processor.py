import os
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt, QObject, pyqtSignal, QThread
from concurrent.futures import ThreadPoolExecutor
import threading
from PIL import Image as PILImage
import io
# 添加文件系统监视器
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class ImageProcessor(QObject):
    # 添加信号用于通知UI更新
    thumbnail_loaded = pyqtSignal(str, object)
    # 添加导入进度信号
    import_progress = pyqtSignal(int, int)  # current, total
    import_finished = pyqtSignal()
    # 添加文件变化信号
    file_changed = pyqtSignal(str, str)  # action, filename
    
    def __init__(self):
        super().__init__()
        self.folder_path = ""
        self.images = {}  # {image_name: {path, tag_path}}
        # 添加缩略图缓存
        self.thumbnail_cache = {}
        # 添加线程池，增加工作线程数量以提高并发处理能力
        self.thread_pool = ThreadPoolExecutor(max_workers=24)
        # 添加缩略图尺寸缓存
        self.thumbnail_size_cache = {}
        # 添加文件监视器
        self.observer = None
        self.event_handler = None
        
    def convert_image_to_png(self, filename, folder_path):
        """将单个图片文件转换为PNG格式"""
        name, ext = os.path.splitext(filename)
        if ext.lower() in ['.jpg', '.jpeg', '.bmp', '.gif']:
            old_path = os.path.join(folder_path, filename)
            new_filename = name + '.png'
            new_path = os.path.join(folder_path, new_filename)
            
            try:
                # 打开原始图片并转换为PNG格式
                img = PILImage.open(old_path)
                img.save(new_path, 'PNG')
                # 删除原文件
                os.remove(old_path)
                return True
            except Exception as e:
                print(f"转换图片失败 {filename}: {e}")
                return False
        return False
        
    def load_folder(self, folder_path):
        self.folder_path = folder_path
        # 不再清空images，改为追加模式
        self.images = {}
        self.thumbnail_cache = {}  # 清空缩略图缓存
        
        # 支持的图片格式
        image_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.gif')
        
        # 先将所有非PNG格式的图片转换为PNG格式，使用多线程加速
        files = [f for f in os.listdir(folder_path) if f.lower().endswith(image_extensions)]
        
        # 使用线程池并行处理图片转换
        convert_futures = []
        for filename in files:
            name, ext = os.path.splitext(filename)
            if ext.lower() in ['.jpg', '.jpeg', '.bmp', '.gif']:
                # 提交转换任务到线程池
                future = self.thread_pool.submit(self.convert_image_to_png, filename, folder_path)
                convert_futures.append((future, filename))
        
        # 等待所有转换任务完成
        for future, filename in convert_futures:
            try:
                future.result()  # 获取结果，确保任务已完成
            except Exception as e:
                print(f"转换图片时出错 {filename}: {e}")
        
        # 重新获取文件列表，只处理PNG格式的图片
        png_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.png')]
        total_files = len(png_files)
        
        for i, filename in enumerate(png_files):
            if filename.lower().endswith('.png'):
                image_name = os.path.splitext(filename)[0]
                image_path = os.path.join(folder_path, filename)
                tag_path = os.path.join(folder_path, image_name + '.txt')
                
                # 即使标签文件不存在也记录图片信息
                self.images[image_name] = {
                    'image_path': image_path,
                    'tag_path': tag_path
                }
                
            # 发送进度信号
            self.import_progress.emit(i + 1, total_files)
            
        # 启动文件监视器
        self.start_monitoring()
        self.import_finished.emit()
        
    # 添加文件监视方法
    def start_monitoring(self):
        """启动文件监视器"""
        if self.observer is not None:
            self.stop_monitoring()
            
        if self.folder_path and os.path.exists(self.folder_path):
            self.event_handler = FileChangeHandler(self)
            self.observer = Observer()
            self.observer.schedule(self.event_handler, self.folder_path, recursive=False)
            self.observer.start()
    
    def stop_monitoring(self):
        """停止文件监视器"""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            self.event_handler = None
    
    def handle_file_created(self, file_path):
        """处理新创建的文件"""
        filename = os.path.basename(file_path)
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
            # 转换为PNG格式（如果需要）
            name, ext = os.path.splitext(filename)
            if ext.lower() in ['.jpg', '.jpeg', '.bmp', '.gif']:
                if self.convert_image_to_png(filename, self.folder_path):
                    # 转换成功后更新文件名为.png
                    filename = name + '.png'
                    file_path = os.path.join(self.folder_path, filename)
            
            # 如果是PNG文件，添加到图片列表
            if filename.lower().endswith('.png'):
                image_name = os.path.splitext(filename)[0]
                image_path = os.path.join(self.folder_path, filename)
                tag_path = os.path.join(self.folder_path, image_name + '.txt')
                
                # 添加到images字典
                self.images[image_name] = {
                    'image_path': image_path,
                    'tag_path': tag_path
                }
                
                # 发送文件变化信号
                self.file_changed.emit('created', image_name)
                
        elif filename.lower().endswith('.txt'):
            # 处理标签文件的变化
            image_name = os.path.splitext(filename)[0]
            if image_name in self.images:
                # 发送文件变化信号
                self.file_changed.emit('tag_updated', image_name)

    def get_pixmap(self, image_name):
        if image_name in self.images:
            image_path = self.images[image_name]['image_path']
            if os.path.exists(image_path):
                return QPixmap(image_path)
        return None
        
    def get_tag_content(self, image_name):
        if image_name in self.images:
            tag_path = self.images[image_name]['tag_path']
            if os.path.exists(tag_path):
                try:
                    with open(tag_path, 'r', encoding='utf-8') as f:
                        return f.read().strip()
                except Exception:
                    return ""
        return ""
        
    # 添加获取缩略图的方法
    def get_thumbnail(self, image_name, size=(400, 400)):
        # 检查缓存中是否有缩略图
        if image_name in self.thumbnail_cache:
            return self.thumbnail_cache[image_name]
            
        if image_name in self.images:
            image_path = self.images[image_name]['image_path']
            tag_path = self.images[image_name]['tag_path']
            if os.path.exists(image_path):
                # 使用QImage直接加载并缩放，性能更好
                image = QImage(image_path)
                if not image.isNull():
                    # 直接使用QImage进行缩放，比QPixmap更高效
                    scaled_image = image.scaled(size[0], size[1], 
                                              Qt.KeepAspectRatio, 
                                              Qt.SmoothTransformation)
                    thumbnail = QPixmap.fromImage(scaled_image)
                    
                    # 检查是否已打标（标签文件是否存在且非空）
                    is_tagged = False
                    if os.path.exists(tag_path):
                        try:
                            with open(tag_path, 'r', encoding='utf-8') as f:
                                if f.read().strip():
                                    is_tagged = True
                        except Exception:
                            pass
                    
                    # 如果未打标，在缩略图上添加标识
                    if not is_tagged:
                        from PyQt5.QtGui import QPainter, QPen, QFont
                        painter = QPainter(thumbnail)
                        painter.setPen(QPen(Qt.red, 3))
                        painter.setFont(QFont("Arial", 12, QFont.Bold))
                        painter.drawText(thumbnail.rect(), Qt.AlignCenter, "未打标")
                        painter.end()
                    
                    # 缓存并返回缩略图
                    self.thumbnail_cache[image_name] = thumbnail
                    return thumbnail
        return None
        
    # 添加异步加载缩略图方法
    def load_thumbnail_async(self, image_name, size=(400, 400)):
        def load_and_emit():
            thumbnail = self.get_thumbnail(image_name, size)
            # 发送信号通知UI更新
            self.thumbnail_loaded.emit(image_name, thumbnail)
        
        # 提交到线程池执行
        self.thread_pool.submit(load_and_emit)
        
    def save_tags_to_image(self, image_name, tags):
        """
        将选中的标签保存到图片对应的标签文件中
        """
        if image_name not in self.images:
            return False
            
        tag_path = self.images[image_name]['tag_path']
        content = ", ".join(tags)
        
        try:
            with open(tag_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception:
            return False
            

    def shutdown(self):
        # 关闭线程池
        self.thread_pool.shutdown(wait=False)
        # 停止文件监视器
        self.stop_monitoring()

# 添加文件变化处理器
class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, image_processor):
        super().__init__()
        self.image_processor = image_processor
    
    def on_created(self, event):
        if not event.is_directory:
            # 在主线程中处理文件创建事件
            self.image_processor.handle_file_created(event.src_path)