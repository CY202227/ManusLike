#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数字员工终端测试系统 - 启动脚本
快速启动完整的后端功能测试界面
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from interfaces.terminal_chat import main

if __name__ == "__main__":
    print("🚀 启动数字员工终端测试系统...")
    print("📝 如需退出，请输入 'quit' 或按 Ctrl+C")
    print("-" * 50)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 程序已退出，感谢使用！")
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        print("请检查依赖项是否正确安装")
        import traceback
        traceback.print_exc() 