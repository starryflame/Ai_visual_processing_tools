# -*- coding: utf-8 -*-
"""
AI 视觉处理工具集 - 统一管理中心
支持多个 ComfyUI Web UI 工具的集中管理和快速切换
"""
import streamlit as st
from urllib.parse import urljoin
import requests

# 页面配置
st.set_page_config(
    page_title="AI 视觉处理工具集",
    page_icon="🔧",
    layout="wide"
)

# CSS 样式
st.markdown("""
<style>
    .tool-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
        color: white;
        cursor: pointer;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .tool-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 20px rgba(0,0,0,0.3);
    }
    .tool-title {
        font-size: 1.5rem;
        font-weight: bold;
        margin-bottom: 10px;
    }
    .tool-desc {
        font-size: 1rem;
        opacity: 0.9;
    }
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #2c3e50;
        text-align: center;
        margin-bottom: 2rem;
    }
    .server-status {
        padding: 15px;
        border-radius: 8px;
        background-color: #f8f9fa;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# 服务器状态检查
COMFYUI_SERVER = st.sidebar.text_input("ComfyUI 地址", value="http://127.0.0.1:8188")

def check_server_status(server):
    try:
        response = requests.get(f"{server}/system_stats", timeout=5)
        if response.status_code == 200:
            return True, "✅ 连接正常"
        else:
            return False, f"❌ 状态码：{response.status_code}"
    except Exception as e:
        return False, f"❌ {str(e)}"

status_ok, status_msg = check_server_status(COMFYUI_SERVER)

st.markdown(f'<div class="main-header">🔧 AI 视觉处理工具集</div>', unsafe_allow_html=True)

if st.button("🔄 刷新状态"):
    status_ok, status_msg = check_server_status(COMFYUI_SERVER)

st.markdown(f'''
<div class="server-status" style="background-color: {'#d4edda' if status_ok else '#f8d7da'}; border-left: 5px solid {'#28a745' if status_ok else '#dc3545'};">
    <strong>🖥️ ComfyUI 服务器状态:</strong> {status_msg}
</div>
''', unsafe_allow_html=True)

# 工具导航卡片
st.markdown("### 📱 选择工具")

col1, col2 = st.columns(2)

with col1:
    if st.button(
        """
        <div class="tool-card" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
            <div class="tool-title">🎨 Qwen-Image 图像生成器</div>
            <div class="tool-desc">基于 Qwen-Image Lightning 的 4 步快速海报生成工具，支持文字排版。</div>
        </div>
        """,
        use_container_width=True
    ):
        st.switch_page("其他/comfyui/web_ui/QwenImage_Generator.py")

with col2:
    if st.button(
        """
        <div class="tool-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
            <div class="tool-title">🎬 数字人视频拼接</div>
            <div class="tool-desc">基于 WanInfiniteTalkToVideo 的数字人视频生成，支持多动作提示词循环。</div>
        </div>
        """,
        use_container_width=True
    ):
        st.switch_page("其他/comfyui/web_ui/数字人视频拼接 UI.py")

# 使用说明
with st.expander("📖 使用指南"):
    st.markdown("""
    ### 🚀 快速开始
    
    1. **确保 ComfyUI 已启动** - 在另一个终端运行 `python main.py`
    
    2. **选择工具** - 点击上方卡片进入对应工具界面
    
    3. **配置参数** - 设置提示词、采样参数等
    
    4. **生成结果** - 点击生成按钮，等待 ComfyUI 处理完成
    
    ### 📋 可用工具列表
    
    | 工具名称 | 描述 |
    |---------|------|
    | Qwen-Image 图像生成器 | 快速海报生成（4 步） |
    | 数字人视频拼接 | 音频驱动数字人视频 |
    
    ### ⚙️ 高级设置
    
    - 可在侧边栏修改 ComfyUI 服务器地址
    - 点击"刷新状态"检查连接
    """)

# 页脚
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <p>💡 AI 视觉处理工具集 · 基于 Streamlit + ComfyUI</p>
</div>
""", unsafe_allow_html=True)
