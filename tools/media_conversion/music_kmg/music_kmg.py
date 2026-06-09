import os
import sys

def rename_kgm_flac_to_kgm(directory):
    """
    扫描指定目录下所有以.kgm.flac结尾的文件，并将其重命名为.kgm结尾
    """
    # 检查目录是否存在
    if not os.path.isdir(directory):
        print(f"错误: 目录 '{directory}' 不存在")
        return
    
    # 统计处理的文件数量
    count = 0
    
    # 遍历目录中的所有文件
    for filename in os.listdir(directory):
        # 检查文件是否以.kgm.flac结尾
        if filename.endswith('.kgm.flac'):
            old_path = os.path.join(directory, filename)
            # 创建新的文件名，将.kgm.flac替换为.kgm
            new_filename = filename[:-9] + '.kgm'  # -9是因为'.kgm.flac'有9个字符
            new_path = os.path.join(directory, new_filename)
            
            try:
                # 重命名文件
                os.rename(old_path, new_path)
                print(f"已重命名: {filename} -> {new_filename}")
                count += 1
            except OSError as e:
                print(f"重命名失败 {filename}: {e}")
    
    print(f"完成! 共处理了 {count} 个文件")

if __name__ == "__main__":
    # 如果命令行提供了参数，则使用第一个参数作为目录
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    else:
        # 否则提示用户输入目录
        directory = input("请输入要处理的目录路径: ")
    
    rename_kgm_flac_to_kgm(directory)