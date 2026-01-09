import os
import logging
from pathlib import Path

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VideoTxtProcessor:
    def __init__(self):
        # 支持的视频格式
        self.supported_formats = ('.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.m4v', '.3gp')
        
    def process_folder(self, folder_path):
        """
        递归处理文件夹中的所有视频文件
        检查同名txt文件，如果存在且内容长度大于1000字，则删除视频和txt文件
        """
        deleted_count = 0
        
        # 递归遍历所有文件
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                # 检查是否为支持的视频格式
                if file.lower().endswith(self.supported_formats):
                    video_path = os.path.join(root, file)
                    # 构造同名txt文件路径
                    txt_path = os.path.splitext(video_path)[0] + '.txt'
                    
                    # 检查txt文件是否存在
                    if os.path.exists(txt_path):
                        try:
                            # 读取txt文件内容
                            with open(txt_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                            
                            # 检查内容长度是否大于1000字
                            if len(content) > 1000:
                                # 删除视频文件和txt文件
                                os.remove(video_path)
                                os.remove(txt_path)
                                logger.info(f"已删除: {file} 及其对应的标签文件 (标签长度: {len(content)} 字符)")
                                deleted_count += 1
                            else:
                                logger.info(f"保留: {file} (标签长度: {len(content)} 字符)")
                        except Exception as e:
                            logger.error(f"处理文件 {file} 时出错: {e}")
        
        logger.info(f"处理完成，共删除 {deleted_count} 个视频及标签文件对")

def main():
    """主函数"""
    import sys
    from tkinter import filedialog, Tk
    
    processor = VideoTxtProcessor()
    
    print("视频-TXT标签文件处理器")
    print("=" * 30)
    
    # 检查是否通过命令行参数提供了文件夹路径
    if len(sys.argv) > 1:
        folder_path = sys.argv[1]
        if not os.path.exists(folder_path):
            print(f"指定的文件夹不存在: {folder_path}")
            return
        print(f"使用命令行参数指定的文件夹: {folder_path}")
    else:
        # 创建隐藏的根窗口
        root = Tk()
        root.withdraw()
        # 选择文件夹
        folder_path = filedialog.askdirectory(title="选择包含视频文件的文件夹")
        root.destroy()
        
        if not folder_path:
            print("未选择文件夹，程序退出")
            return
        print(f"选择的文件夹: {folder_path}")
    
    # 处理文件夹
    processor.process_folder(folder_path)
    
    print("处理完成!")

if __name__ == "__main__":
    main()

