import subprocess
import sys
import os

def main():
    # 检查依赖
    try:
        import streamlit
        from PIL import Image
        import requests
        import websocket
    except ImportError:
        print("正在安装依赖...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "streamlit", "websocket-client"])
    
    # 获取当前文件所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    app_file = os.path.join(current_dir, "数字人视频拼接 UI.py")
    
    if not os.path.exists(app_file):
        print(f"❌ 错误：找不到应用文件 {app_file}")
        return
    
    # 启动 Streamlit 应用
    print("🚀 启动 数字人视频拼接生成器 Web UI...")
    print(f"📍 应用文件：{app_file}")
    print("🌐 访问地址：http://localhost:8501")
    print("💡 按 Ctrl+C 停止服务")
    
    subprocess.run([sys.executable, "-m", "streamlit", "run", app_file, "--server.port", "8501"])

if __name__ == "__main__":
    main()
