# 全局按钮样式定义
BUTTON_STYLE_NORMAL = """
    QPushButton {
        background-color: #4A90E2;  /* 蓝色背景 */
        border: 2px solid #357ABD;  /* 深蓝色边框 */
        color: white;               /* 白色文字 */
        padding: 8px;               /* 内边距 */
        border-radius: 8px;         /* 圆角边框 */
        font-family: 'PingFang SC';
        font-size: 14px;
        font-weight: bold;
    }
"""

BUTTON_STYLE_HOVER = """
    QPushButton:hover {
        background-color: #5AA0F0;  /* 浅蓝色背景 - 鼠标悬停时的效果 */
        border: 2px solid #4A90E2;  /* 蓝色边框 - 鼠标悬停时的效果 */
    }
"""

BUTTON_STYLE_PRESSED = """
    QPushButton:pressed {
        background-color: #357ABD;  /* 深蓝色背景 - 按钮按下时的效果 */
        border: 2px solid #2E69A0;  /* 更深蓝色边框 - 按钮按下时的效果 */
    }
"""

BUTTON_STYLE_IMPORTANT = """
    QPushButton {
        background-color: #E74C3C;  /* 红色背景 - 用于重要/危险操作按钮 */
        border: 2px solid #C0392B;  /* 深红色边框 - 用于重要/危险操作按钮 */
        color: white;
        padding: 8px;
        border-radius: 8px;
        font-family: 'PingFang SC';
        font-size: 14px;
        font-weight: bold;
    }
"""

BUTTON_STYLE_NAVIGATION = """
    QPushButton {
        background-color: #2ECC71;  /* 绿色背景 - 用于导航/前进后退按钮 */
        border: 2px solid #27AE60;  /* 深绿色边框 - 用于导航/前进后退按钮 */
        color: white;
        padding: 8px;
        border-radius: 8px;
        font-family: 'PingFang SC';
        font-size: 14px;
        font-weight: bold;
    }
"""

# 主题样式定义
LIGHT_THEME = """
    QMainWindow, QWidget, QFrame, QGroupBox, QTabWidget, QScrollArea {
        background-color: #f0f0f0;  /* 浅灰色背景 - 浅色主题 */
        color: #000000;             /* 黑色文字 - 浅色主题 */
    }
    QLabel {
        color: #000000;             /* 黑色文字 - 浅色主题 */
        background-color: transparent;
    }
    QListWidget, QTextEdit, QLineEdit {
        background-color: #ffffff;  /* 白色背景 - 浅色主题 */
        color: #000000;             /* 黑色文字 - 浅色主题 */
        border: 1px solid #cccccc;  /* 灰色边框 - 浅色主题 */
    }
    QScrollBar:vertical {
        background-color: #f0f0f0;  /* 浅灰色背景 - 滚动条 - 浅色主题 */
        width: 15px;
        border-radius: 4px;
    }
    QScrollBar::handle:vertical {
        background-color: #c0c0c0;  /* 灰色滑块 - 滚动条 - 浅色主题 */
        border-radius: 4px;
        min-height: 20px;
    }
    QTreeWidget {
        background-color: #ffffff;  /* 白色背景 - 树形控件 - 浅色主题 */
        color: #000000;             /* 黑色文字 - 树形控件 - 浅色主题 */
        alternate-background-color: #f9f9f9;  /* 交替行背景色 - 树形控件 - 浅色主题 */
    }
    QTabWidget::pane {
        border: 1px solid #cccccc;  /* 灰色边框 - 标签页 - 浅色主题 */
    }
    QTabBar::tab {
        background-color: #e0e0e0;  /* 浅灰色背景 - 标签页选项卡 - 浅色主题 */
        border: 1px solid #cccccc;  /* 灰色边框 - 标签页选项卡 - 浅色主题 */
        padding: 4px;
    }
    QTabBar::tab:selected {
        background-color: #f0f0f0;  /* 选中标签页的背景色 - 浅色主题 */
    }
"""

DARK_THEME = """
    QMainWindow, QWidget, QFrame, QGroupBox, QTabWidget, QScrollArea {
        background-color: #2b2b2b;  /* 深灰色背景 - 深色主题 */
        color: #ffffff;             /* 白色文字 - 深色主题 */
    }
    QLabel {
        color: #ffffff;             /* 白色文字 - 深色主题 */
        background-color: transparent;
    }
    QListWidget, QTextEdit, QLineEdit {
        background-color: #3c3c3c;  /* 深灰色背景 - 深色主题 */
        color: #ffffff;             /* 白色文字 - 深色主题 */
        border: 1px solid #555555;  /* 深灰色边框 - 深色主题 */
    }
    QScrollBar:vertical {
        background-color: #2b2b2b;  /* 深灰色背景 - 滚动条 - 深色主题 */
        width: 15px;
        border-radius: 4px;
    }
    QScrollBar::handle:vertical {
        background-color: #555555;  /* 中灰色滑块 - 滚动条 - 深色主题 */
        border-radius: 4px;
        min-height: 20px;
    }
    QTreeWidget {
        background-color: #3c3c3c;  /* 深灰色背景 - 树形控件 - 深色主题 */
        color: #ffffff;             /* 白色文字 - 树形控件 - 深色主题 */
        alternate-background-color: #353535;  /* 交替行背景色 - 树形控件 - 深色主题 */
    }
    QTabWidget::pane {
        border: 1px solid #555555;  /* 深灰色边框 - 标签页 - 深色主题 */
    }
    QTabBar::tab {
        background-color: #3c3c3c;  /* 深灰色背景 - 标签页选项卡 - 深色主题 */
        border: 1px solid #555555;  /* 深灰色边框 - 标签页选项卡 - 深色主题 */
        color: #ffffff;             /* 白色文字 - 标签页选项卡 - 深色主题 */
        padding: 4px;
    }
    QTabBar::tab:selected {
        background-color: #2b2b2b;  /* 选中标签页的背景色 - 深色主题 */
    }
"""

# 图片预览框样式定义
IMAGE_LABEL_STYLE_LIGHT = "border: 1px solid gray; background-color: #f0f0f0;"  # 浅色主题下的图片预览框样式 - 灰色边框，浅灰色背景
IMAGE_LABEL_STYLE_DARK = "border: 1px solid gray; background-color: #3c3c3c;"    # 深色主题下的图片预览框样式 - 灰色边框，深灰色背景

# 统计标签样式定义
STATS_LABEL_STYLE_LIGHT = "background-color: #f0f0f0; color: #000000; padding: 5px; border: 1px solid gray;"     # 浅色主题下的统计标签样式 - 浅灰色背景，黑色文字
STATS_LABEL_STYLE_DARK = "background-color: #2b2b2b; color: #ffffff; padding: 5px; border: 1px solid #555555;"   # 深色主题下的统计标签样式 - 深灰色背景，白色文字