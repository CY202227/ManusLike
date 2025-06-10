"""
终端问答模块 - 集成全部后端功能的测试界面
提供交互式终端界面来测试数字员工系统的所有功能
"""

import asyncio
import logging
import time
import traceback
from datetime import datetime
from typing import Dict, Any, List
import os
import json
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from openai import OpenAI
from communication.mcp_client import MultiMCPClient
from tools.tool_manager import ToolManager
from core import (
    TaskPlanner, ExecutionEventEmitter, TaskPlan, TaskStatus,
    TaskExecutor, FileManager
)
from core.result_collector import ResultCollector

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TerminalChatBot:
    """终端聊天机器人 - 完整功能测试"""
    
    def __init__(self):
        """初始化聊天机器人"""
        self.session_id = f"session_{int(time.time())}"
        self.conversation_history = []
        self.current_task = None
        
        # 核心组件
        self.llm_client = None
        self.mcp_client = None
        self.tool_manager = None
        self.file_manager = None
        self.event_emitter = None
        self.task_planner = None
        self.task_executor = None
        self.result_collector = None
        
        # 状态
        self.is_initialized = False
        
        print(self._get_welcome_banner())
    
    def _get_welcome_banner(self) -> str:
        """获取欢迎横幅"""
        return """
╔══════════════════════════════════════════════════════════════╗
║                    🤖 数字员工终端测试系统                      ║
╠══════════════════════════════════════════════════════════════╣
║  这是一个完整的后端功能测试界面                                  ║
║  支持任务规划、工具调用、文件管理等全部功能                        ║
║                                                              ║
║  输入 'help' 查看可用命令                                      ║
║  输入 'quit' 或 'exit' 退出程序                               ║
╚══════════════════════════════════════════════════════════════╝
"""
    
    async def initialize(self):
        """初始化所有组件"""
        if self.is_initialized:
            return
        
        print("🔧 正在初始化系统组件...")
        
        try:
            # 1. 初始化LLM客户端
            print("  📡 初始化LLM客户端...")
            self.llm_client = OpenAI(
                api_key="sk-proj-1234567890", 
                base_url="http://180.153.21.76:17009/v1"
            )
            
            # 2. 初始化MCP客户端
            print("  🔌 初始化MCP客户端...")
            self.mcp_client = MultiMCPClient()
            
            # 3. 初始化工具管理器
            print("  🛠️  初始化工具管理器...")
            self.tool_manager = ToolManager(self.mcp_client)
            await self.tool_manager.load_all_tools()
            
            # 4. 初始化文件管理器
            print("  📁 初始化文件管理器...")
            self.file_manager = FileManager()
            
            # 5. 初始化事件发射器
            print("  📡 初始化事件发射器...")
            self.event_emitter = ExecutionEventEmitter()
            
            # 6. 初始化任务规划器
            print("  📋 初始化任务规划器...")
            self.task_planner = TaskPlanner(
                llm_client=self.llm_client,
                tool_manager=self.tool_manager,
                event_emitter=self.event_emitter
            )
            
            # 7. 初始化任务执行器
            print("  ⚙️  初始化任务执行器...")
            self.task_executor = TaskExecutor(
                tool_manager=self.tool_manager,
                file_manager=self.file_manager,
                event_emitter=self.event_emitter
            )
            
            # 8. 初始化结果收集器
            print("  📋 初始化结果收集器...")
            self.result_collector = ResultCollector(file_manager=self.file_manager)
            
            self.is_initialized = True
            print("✅ 系统初始化完成！\n")
            
            # 显示系统状态
            await self._show_system_status()
            
        except Exception as e:
            print(f"❌ 系统初始化失败: {e}")
            print(f"错误详情: {traceback.format_exc()}")
            raise
    
    async def _show_system_status(self):
        """显示系统状态"""
        available_tools = self.tool_manager.get_available_tool_names()
        
        print(f"""
╔══════════════════════════════════════════════════════════════╗
║                        📊 系统状态                            ║
╠══════════════════════════════════════════════════════════════╣
║ 会话ID: {self.session_id}                                     ║
║ 可用工具数量: {len(available_tools)} 个                         ║
║ 文件管理器: 已就绪                                             ║
║ 事件系统: 已启用                                               ║
╚══════════════════════════════════════════════════════════════╝

🛠️  可用工具列表:
""")
        for i, tool in enumerate(available_tools, 1):
            print(f"  {i:2d}. {tool}")
        print()
    
    async def start_chat(self):
        """开始聊天循环"""
        if not self.is_initialized:
            await self.initialize()
        
        print("💬 开始对话！请输入您的需求：\n")
        
        while True:
            try:
                # 获取用户输入
                user_input = input("👤 您: ").strip()
                
                if not user_input:
                    continue
                
                # 处理特殊命令
                if user_input.lower() in ['quit', 'exit', 'bye']:
                    await self._handle_quit()
                    break
                elif user_input.lower() == 'help':
                    self._show_help()
                    continue
                elif user_input.lower() == 'status':
                    await self._show_system_status()
                    continue
                elif user_input.lower() == 'history':
                    self._show_conversation_history()
                    continue
                elif user_input.lower() == 'clear':
                    self._clear_screen()
                    continue
                elif user_input.lower().startswith('files'):
                    await self._handle_files_command(user_input)
                    continue
                
                # 记录对话历史
                self.conversation_history.append({
                    "timestamp": datetime.now().isoformat(),
                    "user_input": user_input,
                    "type": "user"
                })
                
                # 处理用户请求
                await self._process_user_request(user_input)
                
            except KeyboardInterrupt:
                print("\n\n🛑 收到中断信号，正在退出...")
                await self._handle_quit()
                break
            except Exception as e:
                print(f"\n❌ 处理请求时发生错误: {e}")
                print(f"错误详情: {traceback.format_exc()}")
                print("请重试或输入 'help' 查看帮助。\n")
    
    async def _process_user_request(self, user_input: str):
        """处理用户请求"""
        print(f"\n🤖 正在处理您的请求: {user_input}")
        print("=" * 60)
        
        start_time = time.time()
        
        try:
            # 1. 任务分析和规划
            print("📋 开始任务分析...")
            task_plan = await self.task_planner.analyze_task(user_input)
            
            # 记录到对话历史
            self.conversation_history.append({
                "timestamp": datetime.now().isoformat(),
                "task_plan": {
                    "task_id": task_plan.task_id,
                    "task_type": task_plan.task_type,
                    "complexity_level": task_plan.complexity_level,
                    "requires_clarification": task_plan.requires_clarification
                },
                "type": "task_plan"
            })
            
            # 2. 处理澄清需求
            if task_plan.requires_clarification:
                print("\n❓ 需要更多信息:")
                for i, question in enumerate(task_plan.clarification_questions, 1):
                    print(f"  {i}. {question}")
                
                # 获取用户澄清
                clarification = await self._get_clarification()
                if clarification:
                    # 根据澄清优化计划
                    task_plan = await self.task_planner.refine_plan_with_feedback(task_plan, clarification)
                else:
                    print("❌ 未获得澄清信息，任务取消。")
                    return
            
            # 3. 执行任务
            if task_plan.status != TaskStatus.FAILED and len(task_plan.plan.steps) > 0:
                print("\n⚙️  开始执行任务...")
                execution_result = await self.task_executor.execute_plan(task_plan, self.session_id)
                
                # 4. 收集和格式化结果
                print("📊 收集执行结果...")
                report = await self.result_collector.collect_and_format_result(execution_result, task_plan)
                
                # 5. 保存报告
                print("💾 保存执行报告...")
                saved_files = await self.result_collector.save_report(report, ['json', 'markdown'], self.file_manager)
                
                # 记录执行结果
                self.conversation_history.append({
                    "timestamp": datetime.now().isoformat(),
                    "execution_result": {
                        "success": execution_result.success,
                        "execution_time": execution_result.execution_time,
                        "files_generated": execution_result.files_generated,
                        "report_files": saved_files
                    },
                    "type": "execution_result"
                })
                
                # 6. 显示执行摘要
                await self._show_execution_summary(task_plan, execution_result, saved_files)
            
            processing_time = time.time() - start_time
            print(f"\n✅ 请求处理完成，总耗时: {processing_time:.2f}秒")
            
        except Exception as e:
            print(f"\n❌ 处理请求失败: {e}")
            print(f"错误详情: {traceback.format_exc()}")
        
        print("\n" + "=" * 60 + "\n")
    
    async def _get_clarification(self) -> str:
        """获取用户澄清"""
        print("\n💬 请提供更多信息（回车跳过）:")
        try:
            clarification = input("👤 您: ").strip()
            return clarification if clarification else None
        except KeyboardInterrupt:
            return None
    
    async def _show_execution_summary(self, task_plan: TaskPlan, execution_result, saved_files):
        """显示执行摘要"""
        print(f"""
╔══════════════════════════════════════════════════════════════╗
║                         📊 执行摘要                           ║
╠══════════════════════════════════════════════════════════════╣
║ 任务ID: {task_plan.task_id}                                   ║
║ 执行状态: {'✅ 成功' if execution_result.success else '❌ 失败'}   ║
║ 执行时间: {execution_result.execution_time:.2f}秒              ║
║ 生成文件: {len(execution_result.files_generated)} 个           ║
╚══════════════════════════════════════════════════════════════╝
""")
        
        # 显示生成的文件
        if execution_result.files_generated:
            print("📁 生成的文件:")
            for i, file_path in enumerate(execution_result.files_generated, 1):
                print(f"  {i}. {file_path}")
            
            # 获取文件摘要
            file_summary = self.task_executor.get_task_files_summary(task_plan.task_id)
            if file_summary.get("files"):
                print("\n📄 文件详情:")
                for file_info in file_summary["files"]:
                    print(f"  • {file_info['name']} ({file_info['type']}, {file_info['size']} bytes)")
            
            # 提供下载包
            download_package = self.task_executor.get_task_download_package(task_plan.task_id, self.session_id)
            if download_package:
                print(f"\n📦 下载包: {download_package}")
        
        # 显示错误信息
        if execution_result.error_message:
            print(f"\n❌ 错误信息: {execution_result.error_message}")
        
        # 显示保存的报告文件
        if saved_files:
            print("\n📁 保存的报告文件:")
            for i, file_path in enumerate(saved_files, 1):
                print(f"  {i}. {file_path}")
    
    def _show_help(self):
        """显示帮助信息"""
        print("""
╔══════════════════════════════════════════════════════════════╗
║                         📖 帮助信息                           ║
╠══════════════════════════════════════════════════════════════╣
║ 基本命令:                                                    ║
║   help    - 显示此帮助信息                                     ║
║   status  - 显示系统状态                                       ║
║   history - 显示对话历史                                       ║
║   clear   - 清屏                                             ║
║   files   - 查看文件管理相关命令                                 ║
║   quit    - 退出程序                                          ║
║                                                              ║
║ 任务示例:                                                     ║
║   "生成一个Python hello world程序"                           ║
║   "搜索Python教程"                                           ║
║   "帮我制定一个学习计划"                                        ║
║   "生成一张科技感的图片"                                        ║
║                                                              ║
║ 文件命令:                                                     ║
║   files list        - 列出所有任务文件                         ║
║   files <task_id>   - 查看特定任务的文件                       ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    def _show_conversation_history(self):
        """显示对话历史"""
        if not self.conversation_history:
            print("📝 暂无对话历史")
            return
        
        print(f"""
╔══════════════════════════════════════════════════════════════╗
║                         📝 对话历史                           ║
║                     (最近 {min(10, len(self.conversation_history))} 条)                              ║
╚══════════════════════════════════════════════════════════════╝
""")
        
        # 显示最近10条记录
        recent_history = self.conversation_history[-10:]
        for i, record in enumerate(recent_history, 1):
            timestamp = record["timestamp"]
            if record["type"] == "user":
                print(f"{i:2d}. [{timestamp}] 👤 {record['user_input']}")
            elif record["type"] == "task_plan":
                plan = record["task_plan"]
                print(f"    📋 任务: {plan['task_type']} (复杂度: {plan['complexity_level']})")
            elif record["type"] == "execution_result":
                result = record["execution_result"]
                status = "✅" if result["success"] else "❌"
                print(f"    {status} 执行: {result['execution_time']:.2f}秒, 文件: {len(result['files_generated'])}个")
        print()
    
    async def _handle_files_command(self, command: str):
        """处理文件相关命令"""
        parts = command.split()
        
        if len(parts) == 1 or parts[1] == "list":
            # 列出所有任务文件
            print("📁 任务文件管理:")
            print("  使用 'files <task_id>' 查看特定任务的文件")
            print("  示例: files abc123")
        elif len(parts) == 2:
            task_id = parts[1]
            file_summary = self.task_executor.get_task_files_summary(task_id)
            if file_summary.get("error"):
                print(f"❌ {file_summary['error']}")
            else:
                print(f"📊 任务 {task_id} 的文件摘要:")
                print(f"  文件数量: {file_summary.get('file_count', 0)}")
                print(f"  总大小: {file_summary.get('total_size', 0)} bytes")
                if file_summary.get("files"):
                    print("  文件列表:")
                    for file_info in file_summary["files"]:
                        print(f"    • {file_info['name']} ({file_info['type']})")
        else:
            print("❌ 无效的files命令。使用 'help' 查看帮助。")
    
    def _clear_screen(self):
        """清屏"""
        os.system('cls' if os.name == 'nt' else 'clear')
        print(self._get_welcome_banner())
    
    async def _handle_quit(self):
        """处理退出"""
        print("""
╔══════════════════════════════════════════════════════════════╗
║                         👋 再见！                             ║
╠══════════════════════════════════════════════════════════════╣
║ 感谢使用数字员工终端测试系统                                     ║
║                                                              ║
║ 会话统计:                                                     ║
║   对话轮次: {:2d} 轮                                           ║
║   会话时长: {} 分钟                                           ║
╚══════════════════════════════════════════════════════════════╝
""".format(
            len([r for r in self.conversation_history if r["type"] == "user"]),
            "N/A"  # 可以计算实际会话时长
        ))
        
        # 保存会话历史
        await self._save_session_history()
    
    async def _save_session_history(self):
        """保存会话历史"""
        try:
            history_file = f"session_history_{self.session_id}.json"
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "session_id": self.session_id,
                    "start_time": datetime.now().isoformat(),
                    "conversation_history": self.conversation_history
                }, f, ensure_ascii=False, indent=2)
            print(f"💾 会话历史已保存到: {history_file}")
        except Exception as e:
            print(f"⚠️  保存会话历史失败: {e}")


# ========== 主程序入口 ==========

async def main():
    """主程序入口"""
    try:
        chat_bot = TerminalChatBot()
        await chat_bot.start_chat()
    except KeyboardInterrupt:
        print("\n\n🛑 程序被用户中断")
    except Exception as e:
        print(f"\n❌ 程序异常退出: {e}")
        print(f"错误详情: {traceback.format_exc()}")

if __name__ == "__main__":
    print("🚀 启动数字员工终端测试系统...")
    asyncio.run(main()) 