import subprocess
import sys
import os

def main():
    # 获取当前文件所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    app_file = os.path.join(current_dir, "集成工作台.py")
    
    # 启动 Streamlit 应用
    print("🚀 启动 AI 视觉处理集成工作台 Web UI...")
    print(f"📍 应用文件：{app_file}")
    print("🌐 访问地址：http://localhost:8502")
    print("💡 按 Ctrl+C 停止服务")
    
    subprocess.run([sys.executable, "-m", "streamlit", "run", app_file, "--server.port", "8502"])

if __name__ == "__main__":
    main()
