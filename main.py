#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数字员工系统主启动脚本
提供多种启动选项：终端聊天、Web界面、系统测试等
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def show_menu():
    """显示启动菜单"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                    🤖 数字员工系统启动器                        ║
╠══════════════════════════════════════════════════════════════╣
║  请选择启动模式：                                              ║
║                                                              ║
║  1. 终端聊天模式 - 命令行交互界面                               ║
║  2. Web界面模式 - 浏览器界面                                   ║
║  3. 系统测试模式 - 运行集成测试                                 ║
║  4. 完整系统模式 - 启动所有服务                                 ║
║                                                              ║
║  输入数字选择模式，或输入 'q' 退出                              ║
╚══════════════════════════════════════════════════════════════╝
""")

async def start_terminal_chat():
    """启动终端聊天模式"""
    print("🚀 启动终端聊天模式...")
    try:
        from interfaces.terminal_chat import main
        await main()
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        print("请确保所有依赖已正确安装")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        import traceback
        traceback.print_exc()

def start_web_interface():
    """启动Web界面模式"""
    print("🌐 启动Web界面模式...")
    try:
        import subprocess
        # 使用绝对路径
        web_main_path = project_root / "interfaces" / "web" / "frontend" / "main.py"
        subprocess.run([sys.executable, str(web_main_path)])
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        import traceback
        traceback.print_exc()

async def run_system_tests():
    """运行系统测试"""
    print("🧪 运行系统测试...")
    try:
        from tests.test_integration import main as test_main
        await test_main()
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        print("如果是相对导入问题，请使用以下命令启动测试：")
        print("python -m tests.test_integration")
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

def start_full_system():
    """启动完整系统"""
    print("🚀 启动完整系统...")
    try:
        import subprocess
        subprocess.run([sys.executable, "scripts/start_system.py"])
    except Exception as e:
        print(f"❌ 启动失败: {e}")

async def main():
    """主函数"""
    while True:
        show_menu()
        
        try:
            choice = input("👤 请选择 (1-4 或 q): ").strip().lower()
            
            if choice == 'q' or choice == 'quit':
                print("👋 再见！")
                break
            elif choice == '1':
                await start_terminal_chat()
            elif choice == '2':
                start_web_interface()
            elif choice == '3':
                await run_system_tests()
            elif choice == '4':
                start_full_system()
            else:
                print("❌ 无效选择，请输入 1-4 或 q")
                
        except KeyboardInterrupt:
            print("\n👋 程序被用户中断，再见！")
            break
        except Exception as e:
            print(f"❌ 发生错误: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 程序被用户中断")
    except Exception as e:
        print(f"❌ 程序运行出错: {e}")
        import traceback
        traceback.print_exc() 