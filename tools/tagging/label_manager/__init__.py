"""
视频图片标签管理器模块

模块结构说明:
- pic_video_label_manager.py: 主文件，包含应用入口和主窗口类
- ui_components.py: UI 组件模块，处理界面布局和组件初始化
- media_handler.py: 媒体处理模块，处理媒体文件加载、显示、删除
- video_controller.py: 视频控制模块，处理视频播放、暂停、进度控制
- label_manager.py: 标签管理模块，处理标签文件的加载、保存
- utils.py: 工具函数模块，提供文件信息获取等辅助功能
"""

from .pic_video_label_manager import VideoLabelManager

__all__ = ['VideoLabelManager']
