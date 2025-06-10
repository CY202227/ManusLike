"""
事件系统
负责任务执行过程中的事件发射和格式化输出
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Callable

from .models import TaskPlan, Step, ExecutionResult

logger = logging.getLogger(__name__)


class ExecutionEventEmitter:
    """执行事件发射器"""
    
    def __init__(self):
        self.listeners: List[Callable] = []
    
    def add_listener(self, callback: Callable):
        """添加事件监听器"""
        self.listeners.append(callback)
    
    def remove_listener(self, callback: Callable):
        """移除事件监听器"""
        if callback in self.listeners:
            self.listeners.remove(callback)
    
    async def emit_event(self, event_type: str, data: Dict[str, Any]):
        """发射事件"""
        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        
        # 格式化输出事件
        formatted_event = self._format_event_output(event)
        print(formatted_event)
        
        # 通知所有监听器
        for listener in self.listeners:
            try:
                if asyncio.iscoroutinefunction(listener):
                    await listener(event)
                else:
                    listener(event)
            except Exception as e:
                logger.error(f"事件监听器执行失败: {e}")
    
    def _format_event_output(self, event: Dict[str, Any]) -> str:
        """格式化事件输出"""
        event_type = event["type"]
        data = event["data"]
        timestamp = event["timestamp"]
        
        if event_type == "task_start":
            return f"""
╭─────────────────────────────────────────────────────────────╮
│ 🚀 任务开始执行                                               │
│ 任务ID: {data.get('task_id', 'N/A')}                          │
│ 任务描述: {data.get('description', 'N/A')[:40]}...            │
│ 预估步骤: {data.get('total_steps', 0)} 个                      │
│ 开始时间: {timestamp}                                          │
╰─────────────────────────────────────────────────────────────╯
"""
        elif event_type == "step_start":
            return f"""
┌─ 步骤开始 ─────────────────────────────────────────────────┐
│ 📋 {data.get('description', 'N/A')}
│ 🔧 工具: {data.get('tool_name', 'N/A')}
│ ⏰ 时间: {timestamp}
└───────────────────────────────────────────────────────────┘
"""
        elif event_type == "tool_call_start":
            return f"""
    ┌─ 🔧 工具调用开始 ─────────────────────────────────────┐
    │ 工具名: {data.get('tool_name', 'N/A')}
    │ 参数: {json.dumps(data.get('args', {}), ensure_ascii=False)}
    │ 时间: {timestamp}
    └─────────────────────────────────────────────────────┘
"""
        elif event_type == "tool_call_complete":
            result = data.get('result', {})
            success = data.get('success', False)
            status_icon = "✅" if success else "❌"
            return f"""
    └─ 🔧 工具调用完成 ─────────────────────────────────────┘
      {status_icon} 状态: {'成功' if success else '失败'}
      📄 结果: {self._format_result_for_display(result)}
      ⏱️  耗时: {data.get('duration', 0):.2f}秒
"""
        elif event_type == "step_progress":
            progress = data.get('progress', 0)
            progress_bar = "█" * int(progress / 10) + "░" * (10 - int(progress / 10))
            return f"📊 进度: [{progress_bar}] {progress}%"
        
        elif event_type == "step_complete":
            status = data.get('status', 'unknown')
            status_icon = "✅" if status == "completed" else "❌"
            return f"""
└─ 步骤完成 ─────────────────────────────────────────────────┘
  {status_icon} 状态: {status}
  ⏱️  完成时间: {timestamp}
"""
        elif event_type == "task_complete":
            success = data.get('success', False)
            status_icon = "🎉" if success else "💥"
            return f"""
╭─────────────────────────────────────────────────────────────╮
│ {status_icon} 任务执行完成                                       │
│ 成功: {'是' if success else '否'}                               │
│ 执行时间: {data.get('execution_time', 0):.2f}秒                │
│ 生成文件: {len(data.get('files_generated', []))} 个             │
│ 完成时间: {timestamp}                                          │
╰─────────────────────────────────────────────────────────────╯
"""
        else:
            return f"📡 {event_type}: {json.dumps(data, ensure_ascii=False, indent=2)}"
    
    async def emit_task_start(self, task_plan: TaskPlan):
        """发射任务开始事件"""
        await self.emit_event("task_start", {
            "task_id": task_plan.task_id,
            "description": task_plan.user_input,
            "total_steps": len(task_plan.plan.steps),
            "task_type": task_plan.task_type
        })
    
    async def emit_step_start(self, step: Step):
        """发射步骤开始事件"""
        await self.emit_event("step_start", {
            "step_id": step.step_id,
            "description": step.step_description,
            "tool_name": step.function_name
        })
    
    async def emit_tool_call_start(self, tool_name: str, args: Dict[str, Any]):
        """发射工具调用开始事件"""
        await self.emit_event("tool_call_start", {
            "tool_name": tool_name,
            "args": args
        })
    
    async def emit_tool_call_complete(self, tool_name: str, result: Any, success: bool, duration: float):
        """发射工具调用完成事件"""
        await self.emit_event("tool_call_complete", {
            "tool_name": tool_name,
            "result": result,
            "success": success,
            "duration": duration
        })
    
    async def emit_step_progress(self, step_id: str, progress: float):
        """发射步骤进度事件"""
        await self.emit_event("step_progress", {
            "step_id": step_id,
            "progress": progress
        })
    
    async def emit_step_complete(self, step: Step, result: Any):
        """发射步骤完成事件"""
        await self.emit_event("step_complete", {
            "step_id": step.step_id,
            "result": self._format_result_for_display(result),
            "status": step.status.value
        })
    
    async def emit_task_complete(self, task_plan: TaskPlan, execution_result: ExecutionResult):
        """发射任务完成事件"""
        await self.emit_event("task_complete", {
            "task_id": task_plan.task_id,
            "success": execution_result.success,
            "execution_time": execution_result.execution_time,
            "files_generated": execution_result.files_generated
        })
    
    # ========== 新增任务分析阶段事件 ==========
    
    async def emit_task_analysis_start(self, user_input: str):
        """发射任务分析开始事件"""
        await self.emit_event("task_analysis_start", {
            "user_input": user_input,
            "message": "开始分析任务需求..."
        })
    
    async def emit_task_type_detected(self, task_type: str, confidence: float):
        """发射任务类型检测事件"""
        await self.emit_event("task_type_detected", {
            "task_type": task_type,
            "confidence": confidence,
            "message": f"检测到任务类型: {task_type} (置信度: {confidence:.1%})"
        })
    
    async def emit_clarity_check_start(self):
        """发射明确度检查开始事件"""
        await self.emit_event("clarity_check_start", {
            "message": "检查任务明确度..."
        })
    
    async def emit_clarity_score(self, score: float, needs_clarification: bool, questions: list = None):
        """发射明确度评分事件"""
        await self.emit_event("clarity_score", {
            "score": score,
            "needs_clarification": needs_clarification,
            "questions": questions or [],
            "message": f"任务明确度评分: {score:.1%}" + (" (需要澄清)" if needs_clarification else " (明确)")
        })
    
    async def emit_plan_generation_start(self, complexity_level: str):
        """发射计划生成开始事件"""
        await self.emit_event("plan_generation_start", {
            "complexity_level": complexity_level,
            "message": f"开始生成执行计划 (复杂度: {complexity_level})..."
        })
    
    async def emit_plan_step_generated(self, step_index: int, total_steps: int, step_description: str, tool_name: str):
        """发射计划步骤生成事件"""
        await self.emit_event("plan_step_generated", {
            "step_index": step_index,
            "total_steps": total_steps,
            "step_description": step_description,
            "tool_name": tool_name,
            "message": f"步骤 {step_index + 1}/{total_steps}: {step_description}"
        })
    
    async def emit_plan_generated(self, task_id: str, total_steps: int, task_type: str):
        """发射计划生成完成事件"""
        await self.emit_event("plan_generated", {
            "task_id": task_id,
            "total_steps": total_steps,
            "task_type": task_type,
            "message": f"执行计划生成完成！共 {total_steps} 个步骤"
        })
    
    async def emit_result_collection_start(self, task_id: str):
        """发射结果收集开始事件"""
        await self.emit_event("result_collection_start", {
            "task_id": task_id,
            "message": "开始收集执行结果..."
        })
    
    async def emit_report_generation_start(self, formats: list):
        """发射报告生成开始事件"""
        await self.emit_event("report_generation_start", {
            "formats": formats,
            "message": f"开始生成执行报告 ({', '.join(formats)} 格式)..."
        })
    
    async def emit_report_saved(self, format_type: str, file_path: str):
        """发射报告保存事件"""
        await self.emit_event("report_saved", {
            "format": format_type,
            "file_path": file_path,
            "message": f"保存 {format_type.upper()} 报告: {file_path}"
        })
    
    async def emit_file_registered(self, file_name: str, file_type: str, description: str):
        """发射文件注册事件"""
        await self.emit_event("file_registered", {
            "file_name": file_name,
            "file_type": file_type,
            "description": description,
            "message": f"注册文件: {file_name} ({file_type})"
        })
    
    async def emit_general_progress(self, stage: str, message: str, progress: float = None):
        """发射通用进度事件"""
        data = {
            "stage": stage,
            "message": message
        }
        if progress is not None:
            data["progress"] = progress
        
        await self.emit_event("general_progress", data)
    
    def _format_result_for_display(self, result: Any) -> str:
        """格式化结果用于显示"""
        if isinstance(result, dict):
            if "error" in result:
                return f"❌ 错误: {result['error']}"
            elif result.get("type") == "chart":
                if result.get("success", False):
                    file_name = result.get("file_name", "chart.html")
                    return f"📊 图表生成成功: {file_name}"
                else:
                    error_msg = result.get("error", "未知错误")
                    return f"❌ 图表生成失败: {error_msg}"
            elif "file_path" in result:
                return f"📁 生成文件: {result['file_path']}"
            else:
                return f"📄 结果: {str(result)[:100]}..."
        elif isinstance(result, str):
            # 检查是否是HTML内容（图表的旧格式返回）
            if result.strip().startswith('<!DOCTYPE html>') or result.strip().startswith('<html'):
                return f"📊 图表HTML内容已生成 (长度: {len(result)} 字符)"
            else:
                return f"📝 文本结果: {result[:100]}..."
        else:
            return f"📊 数据: {str(result)[:100]}..." 