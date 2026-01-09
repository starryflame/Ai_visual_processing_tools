import sys
from PyQt5.QtWidgets import QApplication
from tagger_ui import TaggerUI

def main():
    app = QApplication(sys.argv)
    window = TaggerUI()
    window.show()
    
    # 添加标签统计功能支持
    # 这里可以在窗口初始化后连接相关信号槽
    # 用于处理批量选中后的标签统计显示
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()