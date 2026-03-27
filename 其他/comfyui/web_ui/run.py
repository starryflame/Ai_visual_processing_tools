# -*- coding: utf-8 -*-
"""
AI 视觉处理工具集 - 批量启动脚本
使用 Python subprocess 同时启动多个 Streamlit 服务
"""
import subprocess
import sys
import os
from pathlib import Path

def main():
    """启动所有工具"""
    
    # 获取当前脚本所在目录
    script_dir = Path(__file__).parent
    
    # 定义要启动的服务
    services = [
        {
            "name": "AI 视觉工具集 - 主面板",
            "script": "多工具主面板.py",
            "port": 8502,
            "url": "http://localhost:8502"
        },
        {
            "name": "Qwen-Image 图像生成器",
            "script": "QwenImage_Generator.py",
            "port": 8503,
            "url": "http://localhost:8503"
        },
        {
            "name": "数字人视频拼接",
            "script": "数字人视频拼接 UI.py",
            "port": 8504,
            "url": "http://localhost:8504"
        }
    ]
    
    print("=" * 60)
    print("   AI 视觉处理工具集 - Python 批量启动")
    print("=" * 60)
    print()
    
    # 检查 Python 环境
    try:
        result = subprocess.run([sys.executable, "--version"], capture_output=True, text=True)
        print(f"[✓] Python: {result.stdout.strip()}")
    except Exception as e:
        print(f"[✗] Python 错误：{e}")
        sys.exit(1)
    
    # 检查 Streamlit 是否安装
    try:
        result = subprocess.run([sys.executable, "-m", "streamlit", "--version"], capture_output=True, text=True)
        print(f"[✓] Streamlit: {result.stdout.strip()}")
    except Exception as e:
        print(f"[✗] Streamlit 未安装，请运行：pip install streamlit websocket-client")
        sys.exit(1)
    
    print()
    print("[信息] 正在启动服务...")
    print()
    
    # 存储进程对象
    processes = []
    
    # 启动所有服务
    for service in services:
        try:
            cmd = [
                sys.executable, "-m", "streamlit", "run",
                str(script_dir / service["script"]),
                f"--server.port={service['port']}",
                "--server.address=127.0.0.1"
            ]
            
            # 使用 subprocess.Popen 启动进程（不阻塞）
            process = subprocess.Popen(cmd, cwd=str(script_dir))
            processes.append((service["name"], service["url"], process))
            
            print(f"[✓] {service['name']}")
            print(f"    URL: {service['url']}")
            print()
            
        except Exception as e:
            print(f"[✗] {service['name']} 启动失败：{e}")
    
    # 等待所有进程（会阻塞直到用户中断）
    if processes:
        print("=" * 60)
        print("   ✅ 所有服务已启动!")
        print("=" * 60)
        print()
        
        for name, url, _ in processes:
            print(f"   {name}: {url}")
        
        print()
        print("[提示] 按 Ctrl+C 停止所有服务")
        print("=" * 60)
        print()
    
    try:
        # 等待所有进程结束
        for name, url, process in processes:
            process.wait()
    except KeyboardInterrupt:
        print()
        print("[信息] 正在关闭所有服务...")
        
        for name, url, process in processes:
            if process.poll() is None:
                process.terminate()
        
        print("✅ 已停止所有服务")

if __name__ == "__main__":
    main()
