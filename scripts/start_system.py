#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Manus AI System 启动脚本
同时启动MCP服务器和Web前端
"""

import subprocess
import time
import sys
import threading
import signal
import os
from pathlib import Path

def start_mcp_server():
    """启动MCP服务器"""
    print("🚀 启动MCP服务器...")
    # 获取项目根目录
    project_root = Path(__file__).parent.parent
    process = subprocess.Popen([
        sys.executable, "communication/mcp_server.py"
    ], cwd=project_root)
    return process

def start_web_frontend():
    """启动Web前端"""
    print("🌐 启动Web前端...")
    # 获取项目根目录
    project_root = Path(__file__).parent.parent
    process = subprocess.Popen([
        sys.executable, "interfaces/web/frontend/main.py"
    ], cwd=project_root)
    return process

def signal_handler(sig, frame):
    """信号处理器"""
    print("\n⏹️ 正在关闭系统...")
    sys.exit(0)

def main():
    """主函数"""
    print("=" * 60)
    print("🤖 Manus AI System - 智能代理系统")
    print("=" * 60)
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    
    processes = []
    
    try:
        # 启动MCP服务器
        mcp_process = start_mcp_server()
        processes.append(mcp_process)
        time.sleep(3)  # 等待MCP服务器启动
        
        # 启动Web前端
        web_process = start_web_frontend()
        processes.append(web_process)
        time.sleep(2)  # 等待Web服务启动
        
        print("\n✅ 系统启动完成！")
        print("📋 服务信息:")
        print("   • MCP服务器: http://localhost:8001")
        print("   • Web前端:   http://localhost:8000")
        print("   • 系统监控: http://localhost:8000/api/users")
        print("\n💡 使用说明:")
        print("   1. 打开浏览器访问 http://localhost:8000")
        print("   2. 输入用户ID开始使用")
        print("   3. 支持多用户同时在线")
        print("   4. 按 Ctrl+C 退出系统")
        print("\n🔄 系统运行中...\n")
        
        # 保持主进程运行
        while True:
            # 检查进程状态
            for i, proc in enumerate(processes):
                if proc.poll() is not None:
                    print(f"⚠️ 进程 {i+1} 已退出，退出码: {proc.returncode}")
                    return
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n⏹️ 接收到中断信号，正在关闭...")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
    finally:
        # 清理进程
        print("🧹 清理进程...")
        for proc in processes:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except Exception as e:
                print(f"⚠️ 清理进程时出错: {e}")
                try:
                    proc.kill()
                except:
                    pass
        
        print("✅ 系统已关闭")

if __name__ == "__main__":
    main() 