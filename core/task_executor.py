"""
TaskExecutor - 任务执行器
负责按计划执行各个步骤，处理异常和重试逻辑，实时状态反馈
"""

import asyncio
import logging
import time
import traceback
from datetime import datetime
from typing import Dict, Any
import os
from pathlib import Path

from .models import TaskPlan, Step, StepStatus, TaskStatus, ExecutionResult
from .event_emitter import ExecutionEventEmitter
from .file_manager import FileManager

# 配置日志
logger = logging.getLogger(__name__)

class TaskExecutor:
    """任务执行器 - 负责执行TaskPlanner生成的任务计划"""
    
    def __init__(self, tool_manager, file_manager: FileManager = None, event_emitter: ExecutionEventEmitter = None):
        """
        初始化任务执行器
        
        Args:
            tool_manager: 工具管理器
            file_manager: 文件管理器，可选
            event_emitter: 事件发射器，用于格式化输出
        """
        self.tool_manager = tool_manager
        self.file_manager = file_manager or FileManager()
        self.event_emitter = event_emitter or ExecutionEventEmitter()
        self.execution_queue = []
        self.current_task = None
        
        logger.info("TaskExecutor初始化完成")
    
    async def execute_plan(self, task_plan: TaskPlan, user_id: str = "default") -> ExecutionResult:
        """
        执行完整的任务计划（流式输出版本）
        
        Args:
            task_plan: 要执行的任务计划
            user_id: 用户ID，用于文件管理
            
        Returns:
            ExecutionResult: 执行结果
        """
        logger.info(f"开始执行任务计划: {task_plan.task_id}")
        
        # 检查是否为对话类型
        if getattr(task_plan, 'is_conversation', False):
            logger.info("💬 检测到对话类型，简化执行流程")
            return await self._execute_conversation_plan(task_plan, user_id)
        
        self.current_task = task_plan
        start_time = time.time()
        results = []
        files_generated = []
        
        try:
            # 发射任务开始事件
            await self.event_emitter.emit_task_start(task_plan)
            
            # 为任务创建文件目录，并获取目录路径
            task_dir = self.file_manager.create_task_directory(task_plan.task_id, user_id)
            
            # 更新任务状态为执行中
            task_plan.status = TaskStatus.EXECUTING
            
            # 逐步执行计划中的每个步骤
            for i, step in enumerate(task_plan.plan.steps):
                logger.info(f"执行步骤 {i+1}/{len(task_plan.plan.steps)}: {step.step_description}")
                
                # 发射步骤开始事件
                await self.event_emitter.emit_step_start(step)
                
                # 为文件生成类工具添加任务目录参数
                if step.function_name == 'file_generation_tool':
                    step.args['output_dir'] = str(task_dir)
                
                # 执行步骤
                step_result = await self.execute_step_with_events(step)
                results.append({
                    "step_id": step.step_id,
                    "step_description": step.step_description,
                    "function_name": step.function_name,
                    "result": step_result,
                    "status": step.status.value
                })
                
                # 发射步骤完成事件
                await self.event_emitter.emit_step_complete(step, step_result)
                
                # 从步骤结果中提取和注册文件（现在文件应该已经在正确位置）
                logger.info(f"🔍 开始提取文件，步骤结果类型: {type(step_result)}")
                logger.info(f"🔍 步骤结果内容: {str(step_result)[:200]}...")
                step_files = self._extract_and_register_files(
                    task_plan.task_id, step_result, step.function_name, step.step_id, step.step_description
                )
                logger.info(f"🔍 提取到的文件: {step_files}")
                files_generated.extend(step_files)

                # 如果步骤失败且不是最后一步，考虑是否继续
                if step.status == StepStatus.FAILED and not step.is_final:
                    logger.warning(f"步骤失败，但继续执行后续步骤: {step.error_message}")
                elif step.status == StepStatus.FAILED and step.is_final:
                    logger.error(f"关键步骤失败，终止执行: {step.error_message}")
                    break
            
            # 判断整体执行是否成功
            failed_steps = [r for r in results if r["status"] == StepStatus.FAILED.value]
            success = len(failed_steps) == 0
            
            execution_time = time.time() - start_time
            
            # 更新任务状态
            task_plan.status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
            
            # 创建执行结果
            execution_result = ExecutionResult(
                task_id=task_plan.task_id,
                success=success,
                results=results,
                execution_time=execution_time,
                files_generated=files_generated
            )
            
            # 发射任务完成事件
            await self.event_emitter.emit_task_complete(task_plan, execution_result)
            
            # 为任务创建下载包 (只有当有文件被注册时才创建)
            if files_generated:
                download_package = self.file_manager.create_download_package(task_plan.task_id, user_id)
                if download_package:
                    logger.info(f"任务 {task_plan.task_id} 的下载包已创建: {download_package}")
            
            logger.info(f"任务计划执行完成，用时: {execution_time:.2f}秒，生成文件: {len(files_generated)}个")
            
            return execution_result
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"任务执行过程中发生异常: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            
            task_plan.status = TaskStatus.FAILED
            
            execution_result = ExecutionResult(
                task_id=task_plan.task_id,
                success=False,
                results=results,
                error_message=error_msg,
                execution_time=execution_time,
                files_generated=files_generated
            )
            
            # 发射任务完成事件（失败）
            await self.event_emitter.emit_task_complete(task_plan, execution_result)
            
            return execution_result
    
    async def execute_step_with_events(self, step: Step) -> Any:
        """
        执行单个步骤并发射事件
        
        Args:
            step: 要执行的步骤
            
        Returns:
            Any: 步骤执行结果
        """
        logger.info(f"开始执行步骤: {step.step_description}")
        
        step.status = StepStatus.RUNNING
        step.start_time = datetime.now()
        
        try:
            # 发射工具调用开始事件
            await self.event_emitter.emit_tool_call_start(step.function_name, step.args)
            
            # 记录开始时间
            call_start_time = time.time()
            
            # 特殊处理聊天回复
            if step.function_name == "chat_response":
                result = {
                    "type": "chat_response",
                    "response": step.args.get("response", ""),
                    "success": True
                }
            else:
                # 使用ToolManager统一调用工具
                raw_result = await self.tool_manager.call_tool(step.function_name, step.args)
                # 序列化结果以确保可处理
                result = self.tool_manager._ensure_serializable_result(raw_result)
            
            # 计算耗时
            call_duration = time.time() - call_start_time
            
            # 发射工具调用完成事件
            await self.event_emitter.emit_tool_call_complete(
                step.function_name, 
                result, 
                success=True, 
                duration=call_duration
            )
            
            step.result = result
            step.status = StepStatus.COMPLETED
            step.end_time = datetime.now()
            
            logger.info(f"步骤执行成功: {step.step_description}")
            return result
            
        except Exception as e:
            call_duration = time.time() - call_start_time if 'call_start_time' in locals() else 0
            error_msg = f"步骤执行失败: {str(e)}"
            
            # 发射工具调用完成事件（失败）
            await self.event_emitter.emit_tool_call_complete(
                step.function_name, 
                {"error": error_msg}, 
                success=False, 
                duration=call_duration
            )
            
            step.error_message = error_msg
            step.status = StepStatus.FAILED
            step.end_time = datetime.now()
            
            logger.error(f"步骤执行失败: {step.step_description} - {error_msg}")
            
            return {"error": error_msg}
    
    async def execute_step(self, step: Step) -> Any:
        """
        执行单个步骤（保留原有方法以保持兼容性）
        
        Args:
            step: 要执行的步骤
            
        Returns:
            Any: 步骤执行结果
        """
        return await self.execute_step_with_events(step)
    
    def _extract_and_register_files(self, task_id: str, result: Any, function_name: str, 
                                   step_id: str, description: str) -> list:
        """
        从步骤结果中提取文件并注册到FileManager
        
        Args:
            task_id: 任务ID
            result: 步骤执行结果
            function_name: 函数名称
            step_id: 步骤ID
            description: 步骤描述
            
        Returns:
            list: 提取到的文件路径列表
        """
        extracted_files = []
        
        try:
            logger.info(f"📋 文件提取 - 结果类型: {type(result)}, 函数: {function_name}")
            
            # 处理字典格式的结果
            if isinstance(result, dict):
                logger.info(f"📋 字典结果键: {list(result.keys())}")
                
                # 检查是否有直接的file_path
                if "file_path" in result and result.get("success", True):
                    file_path = result["file_path"]
                    file_type = result.get("file_type", "unknown")
                    logger.info(f"📋 找到直接文件路径: {file_path}")
                    
                    # 智能文件路径处理和注册
                    registered_path = self._smart_file_registration(task_id, file_path, file_type, step_id, description)
                    if registered_path:
                        logger.info(f"📋 文件注册成功: {registered_path}")
                        extracted_files.append(registered_path)
                    else:
                        logger.warning(f"📋 文件注册失败: {file_path}")
                
                # 检查是否是MCP调用结果格式（有result字段）
                elif "result" in result and result.get("success", True):
                    logger.info(f"📋 检测到MCP结果格式，提取result字段")
                    inner_result = result["result"]
                    logger.info(f"📋 内部结果类型: {type(inner_result)}")
                    
                    # 如果inner_result仍然是CallToolResult对象，需要序列化
                    if hasattr(inner_result, 'content'):
                        logger.info(f"📋 内部结果是CallToolResult，进行序列化")
                        serialized_result = self.tool_manager._ensure_serializable_result(inner_result)
                        logger.info(f"📋 序列化后结果类型: {type(serialized_result)}")
                        logger.info(f"📋 序列化后结果: {serialized_result}")
                        inner_result = serialized_result
                    
                    # 如果inner_result是字典且包含file_path
                    if isinstance(inner_result, dict) and "file_path" in inner_result:
                        file_path = inner_result["file_path"]
                        file_type = inner_result.get("file_type", "unknown")
                        logger.info(f"📋 从MCP结果中找到文件路径: {file_path}")
                        
                        # 智能文件路径处理和注册
                        registered_path = self._smart_file_registration(task_id, file_path, file_type, step_id, description)
                        if registered_path:
                            logger.info(f"📋 文件注册成功: {registered_path}")
                            extracted_files.append(registered_path)
                        else:
                            logger.warning(f"📋 文件注册失败: {file_path}")
                    else:
                        logger.info(f"📋 MCP内部结果不是字典或无file_path: {inner_result}")
                        
                # 处理图表生成结果
                elif result.get("type") == "chart" and result.get("success", False):
                    if "file_path" in result:
                        file_path = result["file_path"]
                        file_type = result.get("file_type", "html")
                        chart_description = f"图表文件 - {description}"
                        
                        # 注册图表HTML文件
                        registered_path = self._smart_file_registration(task_id, file_path, file_type, step_id, chart_description)
                        if registered_path:
                            extracted_files.append(registered_path)
                            logger.info(f"图表文件已注册: {registered_path}")
                
                # 处理图片生成结果 (阿里云万相大模型返回格式)
                elif isinstance(result, list) and function_name == "image_generation":
                    for img_result in result:
                        if isinstance(img_result, dict) and "url" in img_result:
                            # 这里可以扩展处理图片URL，下载并保存本地
                            logger.info(f"图片生成结果: {img_result['url']}")
                else:
                    logger.info(f"📋 字典中无file_path或success=False")
            
            # 处理列表格式的结果
            elif isinstance(result, list):
                for item in result:
                    if isinstance(item, str) and any(item.endswith(ext) for ext in ['.txt', '.py', '.json', '.html', '.css', '.md', '.csv']):
                        # 智能文件路径处理和注册
                        registered_path = self._smart_file_registration(task_id, item, "unknown", step_id, description)
                        if registered_path:
                            extracted_files.append(registered_path)
            
            # 处理纯字符串结果（可能是文件路径）
            elif isinstance(result, str):
                # 检查是否是文件路径
                if any(result.endswith(ext) for ext in ['.txt', '.py', '.json', '.html', '.css', '.md', '.csv']):
                    # 智能文件路径处理和注册
                    registered_path = self._smart_file_registration(task_id, result, "unknown", step_id, description)
                    if registered_path:
                        extracted_files.append(registered_path)
            else:
                logger.info(f"📋 非字典结果，跳过文件提取")
            
        except Exception as e:
            logger.error(f"提取文件时发生错误: {e}")
        
        return extracted_files
    
    def _smart_file_registration(self, task_id: str, file_path: str, file_type: str, 
                                step_id: str, description: str) -> str:
        """
        智能文件注册：直接注册文件（文件应该已经在正确位置）
        
        Args:
            task_id: 任务ID
            file_path: 文件路径
            file_type: 文件类型
            step_id: 步骤ID
            description: 描述
            
        Returns:
            str: 注册成功的文件路径，失败返回空字符串
        """
        try:
            # 标准化文件路径
            if os.path.exists(file_path):
                normalized_path = str(Path(file_path).resolve())
            else:
                logger.info(f"文件不存在: {file_path}")
                # 如果原路径不存在，尝试在项目目录下寻找
                script_dir = os.path.dirname(os.path.abspath(__file__))
                project_root = os.path.dirname(script_dir)  # 项目根目录
                possible_paths = [
                    os.path.join(project_root, file_path),  # 基于项目根目录的路径
                    os.path.join(script_dir, file_path),    # 基于core目录的路径（保持兼容）
                    os.path.join(project_root, 'generated_files', os.path.basename(file_path)),
                    os.path.join(script_dir, 'generated_files', os.path.basename(file_path)),
                    os.path.join(project_root, os.path.basename(file_path)),
                    os.path.join(script_dir, os.path.basename(file_path))
                ]
                
                found_path = None
                for test_path in possible_paths:
                    if os.path.exists(test_path):
                        found_path = test_path
                        break
                
                if not found_path:
                    logger.warning(f"文件不存在，无法注册: {file_path}")
                    return ""
                
                normalized_path = str(Path(found_path).resolve())
            
            # 推断文件类型
            if file_type == "unknown":
                file_extension = os.path.splitext(normalized_path)[1].lower()
                type_mapping = {
                    '.py': 'python',
                    '.txt': 'text',
                    '.md': 'markdown',
                    '.html': 'html',
                    '.css': 'css',
                    '.js': 'javascript',
                    '.json': 'json',
                    '.csv': 'csv'
                }
                file_type = type_mapping.get(file_extension, 'unknown')
            
            if self.file_manager.register_file(task_id, normalized_path, file_type, step_id, description):
                logger.info(f"文件已注册: {normalized_path}")
                return normalized_path
            else:
                logger.warning(f"文件注册失败: {normalized_path}")
                return ""
                
        except Exception as e:
            logger.error(f"文件注册失败: {e}")
            return ""
    
    def get_execution_status(self) -> Dict[str, Any]:
        """获取当前执行状态"""
        if not self.current_task:
            return {"status": "idle", "message": "没有正在执行的任务"}
        
        completed_steps = sum(1 for step in self.current_task.plan.steps 
                            if step.status in [StepStatus.COMPLETED, StepStatus.FAILED])
        total_steps = len(self.current_task.plan.steps)
        
        return {
            "task_id": self.current_task.task_id,
            "status": self.current_task.status.value,
            "progress": f"{completed_steps}/{total_steps}",
            "progress_percentage": (completed_steps / total_steps * 100) if total_steps > 0 else 0,
            "current_step": next((step.step_description for step in self.current_task.plan.steps 
                                if step.status == StepStatus.RUNNING), None)
        }
    
    def get_task_files_summary(self, task_id: str) -> Dict[str, Any]:
        """
        获取任务的文件摘要
        
        Args:
            task_id: 任务ID
            
        Returns:
            Dict: 文件摘要信息
        """
        return self.file_manager.get_task_summary(task_id)
    
    def get_task_download_package(self, task_id: str, user_id: str = "default") -> str:
        """
        获取任务的下载包路径
        
        Args:
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            str: 下载包路径，如果不存在则创建
        """
        return self.file_manager.create_download_package(task_id, user_id)

    def _extract_generated_files(self, result: Any, function_name: str) -> list:
        """
        提取生成的文件（保留原有方法以保持兼容性）
        """
        if isinstance(result, dict) and "file_path" in result:
            return [result["file_path"]]
        elif isinstance(result, list):
            return [r for r in result if isinstance(r, str) and r.endswith(('.txt', '.png', '.jpg', '.pdf'))]
        else:
            logger.warning(f"无法识别的文件提取逻辑: {function_name}")
            return []

    async def _execute_conversation_plan(self, task_plan: TaskPlan, user_id: str = "default") -> ExecutionResult:
        """
        执行对话类型的任务计划（简化流程，不生成报告）
        
        Args:
            task_plan: 对话类型的任务计划
            user_id: 用户ID
            
        Returns:
            ExecutionResult: 简化的执行结果
        """
        start_time = time.time()
        results = []
        
        try:
            # 对话类型只需要执行回复步骤，不需要文件管理和报告生成
            for step in task_plan.plan.steps:
                if step.function_name == "chat_response":
                    # 直接返回聊天回复，不需要工具调用
                    step.status = StepStatus.COMPLETED
                    step.start_time = datetime.now()
                    step.end_time = datetime.now()
                    step.result = {
                        "type": "chat_response",
                        "response": step.args.get("response", ""),
                        "success": True
                    }
                    
                    results.append({
                        "step_id": step.step_id,
                        "step_description": step.step_description,
                        "function_name": step.function_name,
                        "result": step.result,
                        "status": step.status.value
                    })
            
            execution_time = time.time() - start_time
            task_plan.status = TaskStatus.COMPLETED
            
            # 创建简化的执行结果（不生成文件和报告）
            execution_result = ExecutionResult(
                task_id=task_plan.task_id,
                success=True,
                results=results,
                execution_time=execution_time,
                files_generated=[]  # 对话不生成文件
            )
            
            logger.info(f"对话执行完成，用时: {execution_time:.3f}秒")
            return execution_result
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"对话执行失败: {str(e)}"
            logger.error(error_msg)
            
            execution_result = ExecutionResult(
                task_id=task_plan.task_id,
                success=False,
                results=results,
                error_message=error_msg,
                execution_time=execution_time,
                files_generated=[]
            )
            
            return execution_result


# ========== 测试函数 ==========

async def test_task_executor():
    """测试TaskExecutor功能"""
    from tool_manager import ToolManager
    from mcp_client import MultiMCPClient
    from manual import TaskPlanner, ExecutionEventEmitter
    from openai import OpenAI
    
    # 初始化客户端
    client = OpenAI(
        api_key="sk-proj-1234567890", 
        base_url="http://180.153.21.76:17009/v1"
    )
    mcp_client = MultiMCPClient()
    
    # 创建事件发射器
    event_emitter = ExecutionEventEmitter()
    
    # 创建简化的组件
    tool_manager = ToolManager(mcp_client)
    await tool_manager.load_all_tools()
    
    file_manager = FileManager()
    planner = TaskPlanner(client, tool_manager, event_emitter=event_emitter)
    executor = TaskExecutor(tool_manager, file_manager, event_emitter)
    
    # 测试用例
    test_tasks = [
        "帮我指定一个学习计划"
    ]
    
    for i, task_input in enumerate(test_tasks, 1):
        print(f"\n=== 集成格式化输出的执行测试 {i} ===")
        print(f"任务: {task_input}")
        
        try:
            # 生成任务计划
            task_plan = await planner.analyze_task(task_input)
            
            if task_plan.requires_clarification:
                print("任务需要澄清，跳过执行")
                continue
            
            print(f"任务计划生成成功，包含 {len(task_plan.plan.steps)} 个步骤")
            
            # 执行任务计划
            execution_result = await executor.execute_plan(task_plan)
            
            print(f"执行结果:")
            print(f"  成功: {execution_result.success}")
            print(f"  执行时间: {execution_result.execution_time:.2f}秒")
            print(f"  生成文件: {execution_result.files_generated}")
            
            # 获取文件摘要
            file_summary = executor.get_task_files_summary(task_plan.task_id)
            print(f"  文件摘要: {file_summary}")
            
            # 获取下载包
            download_package = executor.get_task_download_package(task_plan.task_id)
            print(f"  下载包: {download_package}")
            
            if execution_result.error_message:
                print(f"  错误信息: {execution_result.error_message}")
            
            print("  步骤结果:")
            for result in execution_result.results:
                print(f"    - {result['step_description']}: {result['status']}")
                
        except Exception as e:
            print(f"测试失败: {e}")

if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_task_executor()) 