#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数字员工系统启动脚本
提供终端聊天和Web界面两种模式
"""

import sys
import subprocess
from pathlib import Path

def show_menu():
    """显示启动菜单"""
    print("=" * 60)
    print("🤖 数字员工系统 - 启动菜单")
    print("=" * 60)
    print("请选择启动模式:")
    print("1. 终端聊天模式 (Terminal Chat)")
    print("2. Web界面模式 (Web UI)")
    print("3. 系统测试模式 (Integration Test)")
    print("4. 启动MCP服务器 (MCP Server Only)")
    print("q. 退出 (Quit)")
    print("=" * 60)

def run_terminal_chat():
    """启动终端聊天模式"""
    print("🖥️ 启动终端聊天模式...")
    try:
        subprocess.run([sys.executable, "interfaces/terminal_chat.py"], cwd=Path(__file__).parent)
    except KeyboardInterrupt:
        print("\n👋 终端聊天模式已退出")
    except Exception as e:
        print(f"❌ 启动终端聊天失败: {e}")

def run_web_interface():
    """启动Web界面模式"""
    print("🌐 启动Web界面模式...")
    try:
        subprocess.run([sys.executable, "interfaces/web/frontend/main.py"], cwd=Path(__file__).parent)
    except KeyboardInterrupt:
        print("\n👋 Web界面模式已退出")
    except Exception as e:
        print(f"❌ 启动Web界面失败: {e}")

def run_integration_test():
    """运行系统集成测试"""
    print("🧪 启动系统集成测试...")
    try:
        subprocess.run([sys.executable, "tests/test_integration.py"], cwd=Path(__file__).parent)
    except KeyboardInterrupt:
        print("\n👋 集成测试已退出")
    except Exception as e:
        print(f"❌ 启动集成测试失败: {e}")

def run_mcp_server():
    """启动MCP服务器"""
    print("🔌 启动MCP服务器...")
    try:
        subprocess.run([sys.executable, "communication/mcp_server.py"], cwd=Path(__file__).parent)
    except KeyboardInterrupt:
        print("\n👋 MCP服务器已退出")
    except Exception as e:
        print(f"❌ 启动MCP服务器失败: {e}")

def main():
    """主函数"""
    while True:
        show_menu()
        choice = input("👤 请选择 (1-4 或 q): ").strip().lower()
        
        if choice == '1':
            run_terminal_chat()
        elif choice == '2':
            run_web_interface()
        elif choice == '3':
            run_integration_test()
        elif choice == '4':
            run_mcp_server()
        elif choice == 'q':
            print("👋 再见！")
            break
        else:
            print("❌ 无效选择，请重新输入")
        
        print("\n" + "="*60)
        input("按Enter键返回主菜单...")

if __name__ == "__main__":
    main() 