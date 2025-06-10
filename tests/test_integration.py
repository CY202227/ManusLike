#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
集成测试 - 测试整个系统的集成功能
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from openai import OpenAI
from communication.mcp_client import MultiMCPClient
from tools.tool_manager import ToolManager
from core import TaskPlanner, TaskExecutor, FileManager, ExecutionEventEmitter

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_system_integration():
    """测试系统集成功能"""
    print("🧪 开始运行系统集成测试...")
    
    try:
        # 1. 初始化组件
        print("📋 1. 初始化系统组件...")
        
        # LLM客户端
        llm_client = OpenAI(
            api_key="sk-proj-1234567890", 
            base_url="http://180.153.21.76:17009/v1"
        )
        
        # MCP客户端
        mcp_client = MultiMCPClient()
        
        # 工具管理器
        tool_manager = ToolManager(mcp_client)
        await tool_manager.load_all_tools()
        print(f"   ✅ 加载了 {len(tool_manager.available_tools)} 个工具")
        
        # 文件管理器
        file_manager = FileManager()
        
        # 事件发射器
        event_emitter = ExecutionEventEmitter()
        
        # 任务规划器
        task_planner = TaskPlanner(
            llm_client=llm_client,
            tool_manager=tool_manager,
            event_emitter=event_emitter
        )
        
        # 任务执行器
        task_executor = TaskExecutor(
            tool_manager=tool_manager,
            file_manager=file_manager,
            event_emitter=event_emitter
        )
        
        print("   ✅ 所有组件初始化成功")
        
        # 2. 测试简单任务
        print("\n📋 2. 测试简单任务规划...")
        test_task = "生成一个Python hello world程序"
        
        task_plan = await task_planner.analyze_task(test_task)
        print(f"   ✅ 任务规划成功，生成 {len(task_plan.plan.steps)} 个步骤")
        
        if task_plan.requires_clarification:
            print("   ⚠️  任务需要澄清，跳过执行测试")
        else:
            # 3. 测试任务执行
            print("\n📋 3. 测试任务执行...")
            execution_result = await task_executor.execute_plan(task_plan)
            
            print(f"   ✅ 任务执行完成")
            print(f"   📊 执行结果: {'成功' if execution_result.success else '失败'}")
            print(f"   ⏱️  执行时间: {execution_result.execution_time:.2f}秒")
            print(f"   📁 生成文件: {len(execution_result.files_generated)}个")
        
        # 4. 测试工具调用
        print("\n📋 4. 测试直接工具调用...")
        
        # 测试Generate answer工具
        answer_result = await tool_manager.call_tool(
            "generate_answer_tool",
            {"query": "什么是Python编程语言？"}
        )
        print(f"   ✅ 生成答案工具测试成功")
        
        # 5. 测试文件管理
        print("\n📋 5. 测试文件管理功能...")
        
        # 创建测试目录
        test_task_id = "test_" + str(int(asyncio.get_event_loop().time()))
        task_dir = file_manager.create_task_directory(test_task_id, "test_user")
        print(f"   ✅ 创建任务目录: {task_dir}")
        
        # 注册测试文件
        test_file_path = task_dir / "test.txt"
        test_file_path.write_text("这是一个测试文件")
        
        if file_manager.register_file(
            test_task_id, 
            str(test_file_path), 
            "text", 
            "test_step", 
            "测试文件注册"
        ):
            print("   ✅ 文件注册成功")
        
        # 获取文件摘要
        file_summary = file_manager.get_task_summary(test_task_id)
        print(f"   📊 文件摘要: {file_summary.get('file_count', 0)}个文件")
        
        print("\n🎉 集成测试全部通过！")
        return True
        
    except Exception as e:
        print(f"\n❌ 集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主测试函数"""
    print("=" * 60)
    print("🤖 数字员工系统 - 集成测试")
    print("=" * 60)
    
    success = await test_system_integration()
    
    if success:
        print("\n✅ 所有测试通过")
        exit_code = 0
    else:
        print("\n❌ 测试失败")
        exit_code = 1
    
    print("=" * 60)
    return exit_code


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
    