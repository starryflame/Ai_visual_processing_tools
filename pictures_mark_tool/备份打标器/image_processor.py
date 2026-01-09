import os
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt, QObject, pyqtSignal, QThread
from concurrent.futures import ThreadPoolExecutor
import threading

class ImageProcessor(QObject):
    # 添加信号用于通知UI更新
    thumbnail_loaded = pyqtSignal(str, object)
    # 添加导入进度信号
    import_progress = pyqtSignal(int, int)  # current, total
    import_finished = pyqtSignal()
    
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
        
    def load_folder(self, folder_path):
        self.folder_path = folder_path
        # 不再清空images，改为追加模式
        # self.images = {}
        self.thumbnail_cache = {}  # 清空缩略图缓存
        
        # 支持的图片格式
        image_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.gif')
        
        # 获取文件列表
        files = [f for f in os.listdir(folder_path) if f.lower().endswith(image_extensions)]
        total_files = len(files)
        
        for i, filename in enumerate(files):
            if filename.lower().endswith(image_extensions):
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
            
        self.import_finished.emit()
        
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