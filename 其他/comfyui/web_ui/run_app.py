import subprocess
import sys
import os

def main():
    # 检查依赖
    try:
        import streamlit
        import PIL
        import requests
    except ImportError:
        print("正在安装依赖...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    
    # 获取当前文件所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    app_file = os.path.join(current_dir, "wan22_i2v_app.py")
    
    # 启动 Streamlit 应用
    print("🚀 启动 Wan2.2 视频生成器 Web UI...")
    print(f"📍 应用文件：{app_file}")
    print("🌐 访问地址：http://localhost:8501")
    print("💡 按 Ctrl+C 停止服务")
    
    subprocess.run([sys.executable, "-m", "streamlit", "run", app_file, "--server.port", "8501"])

if __name__ == "__main__":
    main()