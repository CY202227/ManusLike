"""
ResultCollector - 结果收集器
负责收集各步骤执行结果、结果格式化和整理、生成最终报告、结果持久化存储
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

from .models import TaskPlan, ExecutionResult

# 配置日志
logger = logging.getLogger(__name__)

class ResultReport:
    """结果报告类"""
    
    def __init__(self, execution_result: ExecutionResult, task_plan: TaskPlan):
        self.execution_result = execution_result
        self.task_plan = task_plan
        self.generated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "task_info": {
                "task_id": self.task_plan.task_id,
                "user_input": self.task_plan.user_input,
                "task_type": self.task_plan.task_type,
                "complexity_level": self.task_plan.complexity_level,
                "status": self.task_plan.status.value
            },
            "execution_summary": {
                "success": self.execution_result.success,
                "execution_time": self.execution_result.execution_time,
                "total_steps": len(self.execution_result.results),
                "successful_steps": len([r for r in self.execution_result.results if r["status"] == "completed"]),
                "failed_steps": len([r for r in self.execution_result.results if r["status"] == "failed"]),
                "files_generated": self.execution_result.files_generated,
                "error_message": self.execution_result.error_message
            },
            "step_details": self.execution_result.results,
            "metadata": {
                "generated_at": self.generated_at.isoformat(),
                "report_version": "1.0"
            }
        }

class ResultCollector:
    """结果收集器 - 负责收集、格式化和存储执行结果"""
    
    def __init__(self, storage_dir: str = "./execution_results", file_manager=None):
        """
        初始化结果收集器
        
        Args:
            storage_dir: 结果存储目录
            file_manager: 文件管理器实例，用于注册报告文件
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.file_manager = file_manager
        
        # 创建子目录
        (self.storage_dir / "reports").mkdir(exist_ok=True)
        (self.storage_dir / "raw_data").mkdir(exist_ok=True)
        (self.storage_dir / "logs").mkdir(exist_ok=True)
        
        logger.info(f"ResultCollector初始化完成，存储目录: {self.storage_dir}")
    
    async def collect_and_format_result(self, execution_result: ExecutionResult, task_plan: TaskPlan) -> ResultReport:
        """
        收集并格式化执行结果
        
        Args:
            execution_result: 执行结果
            task_plan: 任务计划
            
        Returns:
            ResultReport: 格式化的结果报告
        """
        logger.info(f"开始收集和格式化结果，任务ID: {execution_result.task_id}")
        
        # 创建结果报告
        report = ResultReport(execution_result, task_plan)
        
        # 分析和增强结果
        enhanced_result = await self._enhance_execution_result(execution_result, task_plan)
        report.execution_result = enhanced_result
        
        logger.info("结果收集和格式化完成")
        return report
    
    async def _enhance_execution_result(self, execution_result: ExecutionResult, task_plan: TaskPlan) -> ExecutionResult:
        """增强执行结果，添加额外的分析信息"""
        
        # 添加分析结果到执行结果中
        enhanced_results = []
        for result in execution_result.results:
            enhanced_result = dict(result)
            enhanced_result["analysis"] = {
                "execution_duration": self._calculate_step_duration(task_plan, result["step_id"]),
                "result_type": self._analyze_result_type(result["result"]),
                "success_score": 1.0 if result["status"] == "completed" else 0.0
            }
            enhanced_results.append(enhanced_result)
        
        # 创建增强版执行结果
        enhanced_execution_result = ExecutionResult(
            task_id=execution_result.task_id,
            success=execution_result.success,
            results=enhanced_results,
            error_message=execution_result.error_message,
            execution_time=execution_result.execution_time,
            files_generated=execution_result.files_generated
        )
        
        return enhanced_execution_result
    
    def _calculate_step_statistics(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算步骤统计信息"""
        total_steps = len(results)
        completed_steps = len([r for r in results if r["status"] == "completed"])
        failed_steps = len([r for r in results if r["status"] == "failed"])
        
        return {
            "total": total_steps,
            "completed": completed_steps,
            "failed": failed_steps,
            "success_rate": completed_steps / total_steps if total_steps > 0 else 0
        }
    
    def _analyze_generated_files(self, files: List[str]) -> Dict[str, Any]:
        """分析生成的文件"""
        file_types = {}
        total_size = 0
        
        for file_path in files:
            if os.path.exists(file_path):
                # 获取文件扩展名
                ext = Path(file_path).suffix.lower()
                file_types[ext] = file_types.get(ext, 0) + 1
                
                # 获取文件大小
                try:
                    total_size += os.path.getsize(file_path)
                except OSError:
                    pass
        
        return {
            "count": len(files),
            "types": file_types,
            "total_size": total_size,
            "average_size": total_size / len(files) if files else 0
        }
    
    def _calculate_step_duration(self, task_plan: TaskPlan, step_id: str) -> Optional[float]:
        """计算步骤执行时长"""
        for step in task_plan.plan.steps:
            if step.step_id == step_id and step.start_time and step.end_time:
                duration = (step.end_time - step.start_time).total_seconds()
                return duration
        return None
    
    def _analyze_result_type(self, result: Any) -> str:
        """分析结果类型"""
        if isinstance(result, dict):
            if "error" in result:
                return "error"
            elif "file_path" in result:
                return "file_generation"
            elif "url" in result or "urls" in result:
                return "web_content"
            else:
                return "structured_data"
        elif isinstance(result, str):
            return "text_content"
        elif isinstance(result, (list, tuple)):
            return "list_data"
        else:
            return "unknown"
    
    async def save_report(self, report: ResultReport, formats: List[str] = ['json', 'text'], file_manager=None) -> Dict[str, str]:
        """
        保存结果报告并自动注册到FileManager
        
        Args:
            report: 结果报告
            formats: 保存格式列表，支持 'json', 'markdown', 'text'
            file_manager: 文件管理器实例，如果提供则自动注册文件
            
        Returns:
            Dict[str, str]: 保存的文件路径
        """
        
        # 使用传入的file_manager或实例变量
        file_mgr = file_manager or self.file_manager
        
        saved_files = {}
        task_id = report.execution_result.task_id
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            # 保存JSON格式
            if 'json' in formats:
                json_path = self.storage_dir / "reports" / f"report_{task_id}_{timestamp}.json"
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)
                saved_files['json'] = str(json_path)
                logger.info(f"JSON报告已保存: {json_path}")
                
                # 注册到FileManager
                if file_mgr:
                    try:
                        file_mgr.register_file(
                            task_id,
                            str(json_path),
                            "json",
                            "report",
                            "任务执行报告 (JSON格式)"
                        )
                        logger.info(f"JSON报告已注册到FileManager: {json_path}")
                    except Exception as e:
                        logger.warning(f"注册JSON报告文件失败: {e}")
            
            # 保存纯文本格式
            if 'text' in formats:
                txt_path = self.storage_dir / "reports" / f"report_{task_id}_{timestamp}.txt"
                with open(txt_path, 'w', encoding='utf-8') as f:
                    # 简化的文本格式
                    report_dict = report.to_dict()
                    f.write(f"任务执行报告\n")
                    f.write(f"=" * 50 + "\n")
                    f.write(f"任务ID: {report_dict['task_info']['task_id']}\n")
                    f.write(f"用户输入: {report_dict['task_info']['user_input']}\n")
                    f.write(f"执行结果: {'成功' if report_dict['execution_summary']['success'] else '失败'}\n")
                    f.write(f"执行时间: {report_dict['execution_summary']['execution_time']:.2f}秒\n")
                    f.write(f"生成文件: {len(report_dict['execution_summary']['files_generated'])}个\n")
                saved_files['text'] = str(txt_path)
                logger.info(f"文本报告已保存: {txt_path}")
                
                # 注册到FileManager
                if file_mgr:
                    try:
                        file_mgr.register_file(
                            task_id,
                            str(txt_path),
                            "text",
                            "report",
                            "任务执行报告 (文本格式)"
                        )
                        logger.info(f"文本报告已注册到FileManager: {txt_path}")
                    except Exception as e:
                        logger.warning(f"注册文本报告文件失败: {e}")
            
            return saved_files
            
        except Exception as e:
            logger.error(f"保存报告失败: {e}")
            raise
    
    async def save_raw_data(self, execution_result: ExecutionResult, task_plan: TaskPlan) -> str:
        """
        保存原始执行数据
        
        Args:
            execution_result: 执行结果
            task_plan: 任务计划
            
        Returns:
            str: 保存的文件路径
        """
        task_id = execution_result.task_id
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        raw_data = {
            "task_plan": {
                "task_id": task_plan.task_id,
                "user_input": task_plan.user_input,
                "task_type": task_plan.task_type,
                "complexity_level": task_plan.complexity_level,
                "status": task_plan.status.value,
                "plan": {
                    "plan_id": task_plan.plan.plan_id,
                    "steps": [
                        {
                            "step_id": step.step_id,
                            "step_description": step.step_description,
                            "function_name": step.function_name,
                            "args": step.args,
                            "is_final": step.is_final,
                            "status": step.status.value,
                            "start_time": step.start_time.isoformat() if step.start_time else None,
                            "end_time": step.end_time.isoformat() if step.end_time else None,
                            "error_message": step.error_message
                        }
                        for step in task_plan.plan.steps
                    ]
                }
            },
            "execution_result": {
                "task_id": execution_result.task_id,
                "success": execution_result.success,
                "results": execution_result.results,
                "error_message": execution_result.error_message,
                "execution_time": execution_result.execution_time,
                "files_generated": execution_result.files_generated
            },
            "metadata": {
                "saved_at": datetime.now().isoformat(),
                "version": "1.0"
            }
        }
        
        try:
            raw_data_path = self.storage_dir / "raw_data" / f"raw_{task_id}_{timestamp}.json"
            with open(raw_data_path, 'w', encoding='utf-8') as f:
                json.dump(raw_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"原始数据已保存: {raw_data_path}")
            return str(raw_data_path)
            
        except Exception as e:
            logger.error(f"保存原始数据失败: {e}")
            raise
    
    def get_execution_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取执行历史记录
        
        Args:
            limit: 返回记录数量限制
            
        Returns:
            List[Dict[str, Any]]: 历史记录列表
        """
        history = []
        reports_dir = self.storage_dir / "reports"
        
        try:
            # 获取所有JSON报告文件
            json_files = list(reports_dir.glob("report_*.json"))
            json_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            for json_file in json_files[:limit]:
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        report_data = json.load(f)
                    
                    # 提取关键信息
                    history.append({
                        "task_id": report_data['task_info']['task_id'],
                        "user_input": report_data['task_info']['user_input'][:100] + "..." if len(report_data['task_info']['user_input']) > 100 else report_data['task_info']['user_input'],
                        "success": report_data['execution_summary']['success'],
                        "execution_time": report_data['execution_summary']['execution_time'],
                        "files_generated": len(report_data['execution_summary']['files_generated']),
                        "generated_at": report_data['metadata']['generated_at'],
                        "report_file": str(json_file)
                    })
                    
                except Exception as e:
                    logger.warning(f"读取报告文件失败 {json_file}: {e}")
                    continue
            
            return history
            
        except Exception as e:
            logger.error(f"获取执行历史失败: {e}")
            return []
    
    def cleanup_old_results(self, days: int = 30) -> int:
        """
        清理旧的结果文件
        
        Args:
            days: 保留天数
            
        Returns:
            int: 清理的文件数量
        """
        from datetime import timedelta
        
        cutoff_time = datetime.now() - timedelta(days=days)
        cleaned_count = 0
        
        try:
            # 清理报告文件
            for file_path in self.storage_dir.rglob("*"):
                if file_path.is_file():
                    file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_mtime < cutoff_time:
                        file_path.unlink()
                        cleaned_count += 1
                        logger.info(f"清理旧文件: {file_path}")
            
            logger.info(f"清理完成，共清理{cleaned_count}个文件")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"清理旧结果失败: {e}")
            return cleaned_count


# ========== 测试函数 ==========

async def test_result_collector():
    """测试ResultCollector功能"""
    from tool_manager import ToolManager
    from task_executor import TaskExecutor
    from manual import TaskPlanner
    from mcp_client import MultiMCPClient
    from openai import OpenAI
    
    # 初始化组件
    client = OpenAI(
        api_key="sk-proj-1234567890", 
        base_url="http://180.153.21.76:17009/v1"
    )
    mcp_client = MultiMCPClient()
    tool_manager = ToolManager(mcp_client)
    await tool_manager.load_all_tools()
    
    planner = TaskPlanner(client, tool_manager)
    executor = TaskExecutor(tool_manager)
    collector = ResultCollector()
    
    print("=== ResultCollector测试 ===")
    
    # 测试任务
    test_task = "写一个简单的Python函数来计算两个数的和,不允许追问"
    
    try:
        # 生成并执行任务
        print(f"测试任务: {test_task}")
        task_plan = await planner.analyze_task(test_task)
        
        if task_plan.requires_clarification:
            print("任务需要澄清，跳过测试")
            return
        
        print(f"生成了{len(task_plan.plan.steps)}个执行步骤")
        
        # 执行任务
        execution_result = await executor.execute_plan(task_plan)
        print(f"任务执行完成，成功: {execution_result.success}")
        
        # 收集和格式化结果
        print("\n=== 结果收集测试 ===")
        report = await collector.collect_and_format_result(execution_result, task_plan)
        print("结果收集完成")
        
        # 保存报告
        print("\n=== 报告保存测试 ===")
        saved_files = await collector.save_report(report, ['json', 'text'])
        print("保存的报告文件:")
        for format_type, file_path in saved_files.items():
            print(f"  {format_type}: {file_path}")
        
        # 保存原始数据
        print("\n=== 原始数据保存测试 ===")
        raw_data_path = await collector.save_raw_data(execution_result, task_plan)
        print(f"原始数据保存至: {raw_data_path}")
        
        # 获取执行历史
        print("\n=== 执行历史测试 ===")
        history = collector.get_execution_history(limit=5)
        print(f"找到{len(history)}条历史记录")
        for record in history:
            print(f"  - {record['task_id'][:8]}: {record['user_input'][:50]}...")
        
        
    except Exception as e:
        print(f"测试失败: {e}")
        logger.error(f"ResultCollector测试失败: {e}")

if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_result_collector()) 