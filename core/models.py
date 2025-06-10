"""
数据模型定义
包含任务、步骤、计划等核心数据结构
"""

import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Literal
from enum import Enum

from pydantic import BaseModel, Field


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    ANALYZING = "analyzing"
    PLANNING = "planning"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(Enum):
    """步骤状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class Step(BaseModel):
    """执行步骤模型"""
    step_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    step_description: str = Field(description="步骤描述")
    function_name: str = Field(description="要调用的函数名")
    args: Dict[str, Any] = Field(description="函数参数")
    is_final: bool = Field(default=False, description="是否为最终步骤")
    status: StepStatus = Field(default=StepStatus.PENDING)
    result: Optional[Any] = None
    error_message: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class Plan(BaseModel):
    """任务执行计划模型"""
    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    steps: List[Step] = Field(description="执行步骤列表")
    created_at: datetime = Field(default_factory=datetime.now)
    estimated_duration: Optional[int] = None  # 预估执行时间(秒)


class TaskPlan(BaseModel):
    """完整任务计划"""
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_input: str = Field(description="用户原始输入")
    task_type: str = Field(description="任务类型")
    complexity_level: str = Field(description="复杂度等级: simple/medium/complex")
    plan: Plan = Field(description="执行计划")
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    requires_clarification: bool = Field(default=False)
    clarification_questions: List[str] = Field(default_factory=list)
    is_conversation: bool = Field(default=False, description="是否为对话而非任务")
    parent_task_id: Optional[str] = Field(default=None, description="父任务ID，用于任务改进关联")
    generated_files: List[str] = Field(default_factory=list, description="任务生成的文件列表")


class ExecutionResult(BaseModel):
    """执行结果"""
    task_id: str
    success: bool
    results: List[Dict[str, Any]]
    error_message: Optional[str] = None
    execution_time: float = 0.0
    files_generated: List[str] = Field(default_factory=list)


class TaskType(BaseModel):
    """任务类型枚举"""
    type: Literal["通用任务", "文档处理", "信息检索", "图像生成", "数据分析"] = Field(
        description="任务类型，可选值：通用任务、文档处理、信息检索、图像生成、数据分析"
    )


class TaskNeedClarification(BaseModel):
    """任务需要澄清"""
    need_clarification: bool = Field(description="是否需要澄清")
    questions: List[str] = Field(description="需要澄清的问题")


class TaskClarityScore(BaseModel):
    """任务明确度评分"""
    clarity_score: int = Field(description="明确度评分(0-10)")
    has_clear_action: bool = Field(description="是否包含明确的动作词")
    has_sufficient_params: bool = Field(description="是否包含足够的参数信息")
    is_simple_task: bool = Field(description="是否为简单任务")
    needs_clarification: bool = Field(description="是否需要澄清") 

class IsTaskOrConversation(BaseModel):
    """任务类型"""
    type: Literal["conversation", "task"] = Field(
        description="任务类型，可选值：conversation, task"
    )