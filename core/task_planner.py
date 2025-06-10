"""
任务规划器
负责分析用户需求并生成执行计划
"""

import asyncio
import json
import logging
from typing import Dict, Any

from openai import OpenAI
from .models import (
    TaskPlan, Plan, Step, TaskStatus, TaskType, 
    TaskNeedClarification, TaskClarityScore,IsTaskOrConversation
)
from .event_emitter import ExecutionEventEmitter

logger = logging.getLogger(__name__)


class TaskClarityAnalyzer:
    """任务明确度分析器"""
    
    def __init__(self, llm_client: OpenAI, model_name: str = "Qwen-72B"):
        self.llm_client = llm_client
        self.model_name = model_name
        self.stream_callback = None  # 流式输出回调函数
    
    async def analyze_clarity(self, user_input: str) -> TaskClarityScore:
        """分析任务明确度"""
        clarity_prompt = """
# 角色：
你是一个任务分析专家，需要判断用户需求是否足够明确。

# 任务：
请分析用户输入的任务明确度，从以下维度评分：

用户输入: {user_input}

请按照以下标准评估：
1. clarity_score (0-10分): 整体明确度评分
2. has_clear_action: 是否包含明确的动作词（如：生成、创建、搜索、转换等）
3. has_sufficient_params: 是否包含足够的参数信息
4. is_simple_task: 是否为简单的单步骤任务
5. needs_clarification: 综合判断是否需要澄清

评分标准：
- 9-10分: 非常明确，包含完整目标和参数
- 7-8分: 比较明确，可以直接执行
- 5-6分: 基本明确，但可能需要少量澄清
- 3-4分: 不够明确，需要澄清关键信息
- 0-2分: 非常模糊，必须澄清

示例：
- "生成一个Python hello world程序" -> 9分，不需要澄清
- "搜索Python教程" -> 8分，不需要澄清
- "生成一个程序" -> 4分，需要澄清
- "帮我处理文件" -> 2分，需要澄清
"""
        
        try:
            messages = [
                {"role": "system", "content": clarity_prompt.format(user_input=user_input)}
            ]
            
            await self._stream_print("🔍 分析任务明确度...")
            # 添加流式输出
            response = self.llm_client.beta.chat.completions.parse(
                model=self.model_name,
                messages=messages,
                temperature=0.1,
                response_format=TaskClarityScore
            )
            return response.choices[0].message.parsed
        
        except Exception as e:
            logger.error(f"任务明确度分析失败: {e}")
            # 返回保守的默认值
            return TaskClarityScore(
                clarity_score=5,
                has_clear_action=False,
                has_sufficient_params=False,
                is_simple_task=False,
                needs_clarification=True
            )

    async def _stream_print(self, message: str = "", end: str = "\n"):
        """流式输出函数，支持终端和Web前端"""
        if self.stream_callback:
            # Web前端模式：通过回调发送到前端
            await self.stream_callback(message + end)
        else:
            # 终端模式：直接打印
            print(message, end=end, flush=True)


# ========== 系统提示词 ==========

IMPROVED_REASON_SYSTEM_PROMPT = """
# 角色定位
你是一个智能任务分析助手，需要判断用户需求是否足够明确。

# 判断标准
## 不需要追问的情况（直接返回 need_clarification: false）：
1. 用户需求具体明确，包含完整的操作目标
2. 简单的单步骤任务（如搜索、生成简单文件等）  
3. 用户使用了明确的动作词（生成、创建、搜索、转换等）
4. 已包含必要的参数信息
5. 任务目标清晰，即使缺少细节也可以合理推断

## 需要追问的情况：
1. 用户需求模糊或包含多个可能的解释
2. 缺少关键参数且无法合理推断
3. 复杂任务但缺少执行细节
4. 用户明确表示不确定或询问建议

# 示例判断
- "生成一个Python程序" → 需要追问（缺少具体功能）
- "生成一个Python hello world程序" → 不需要追问
- "生成一个简单的Python游戏" → 不需要追问（可以推断为简单游戏）
- "帮我搜索" → 需要追问（缺少搜索内容）
- "搜索Python教程" → 不需要追问
- "转换这个文件" → 需要追问（缺少文件路径和目标格式）
- "把PDF转成Word" → 需要追问（缺少文件路径）

# 重要原则
- 倾向于不追问，除非确实必要
- 优先尝试合理推断用户意图
- 对于明确的动作+简单描述，不要追问
"""

PLAN_SYSTEM_PROMPT = """
# 角色：
你是一个任务解决专家，你很擅长根据用户的问题结合可用的工具，按步骤制定一个解决方案。

# 任务：
1. 根据用户问题和可用工具，制定详细的步骤化解决方案
2. 步骤要逻辑清晰，能够完美解决用户问题
3. 合理选择和组合工具，避免不必要的步骤
4. 你需要合理使用文件保存工具来保存过程中的文件,并使用文件保存工具来保存最终结果
5. 按照指定的JSON格式输出解决方案
6. 如果用户的问题是闲聊，请调用普通回复工具'generate_answer_tool'来进行回复,结果不需要保存成文件
7. 除非用户要求,否则必须使用中文来进行回答

# 重要工具使用规则：
- 当用户要求"生成"、"创建"、"写"程序/代码/文件时，必须使用file_generation_tool来创建实际文件
- 当用户要求"搜索"、"查找"信息时，使用web_search_tool
- 当用户要求"读取"、"分析"已有文件时，使用read_file_tool
- 当用户要求生成图片时，使用image_generation_tool
- 只有在用户仅仅是询问问题、需要解释或闲聊时，才使用generate_answer_tool
- 不要仅仅用generate_answer_tool来回答关于如何创建文件的问题，而是调用后再创建文件

# 工具列表：
```
{tools}
```

# 任务复杂度分析：
- simple: 单一工具调用即可完成
- medium: 需要2-3个步骤，工具组合使用
- complex: 需要多步骤，包含条件判断和数据传递

# 输出格式：
```json
{output_format}
```

# 注意事项：
1. function_name必须从工具列表中选择，必须使用完全准确的工具名称
2. args参数要与工具定义完全匹配
3. step_description要清晰描述这一步要做什么
4. 最后一步设置is_final为true
5. 考虑步骤间的数据依赖关系
6. 不要进行任何工具名称映射或修改，严格使用工具列表中的名称
7. 当用户明确要求生成文件时，直接使用file_generation_tool，不要用generate_answer_tool
"""


class TaskPlanner:
    """任务规划器 - 负责分析用户需求并生成执行计划"""
    
    def __init__(self, 
                 llm_client: OpenAI,
                 tool_manager,
                 model_name: str = "Qwen-72B",
                 event_emitter: ExecutionEventEmitter = None):
        """
        初始化任务规划器
        
        Args:
            llm_client: OpenAI客户端
            tool_manager: 工具管理器
            model_name: 使用的LLM模型名称
            event_emitter: 事件发射器
        """
        self.llm_client = llm_client
        self.tool_manager = tool_manager
        self.model_name = model_name
        self.event_emitter = event_emitter or ExecutionEventEmitter()
        self.clarity_analyzer = TaskClarityAnalyzer(llm_client, model_name)
        self.stream_callback = None  # 流式输出回调函数
        self.last_completed_task = None  # 最后完成的任务
        
        logger.info("TaskPlanner初始化完成")
    
    def set_stream_callback(self, callback):
        """设置流式输出回调函数"""
        self.stream_callback = callback
        self.clarity_analyzer.stream_callback = callback
    
    def set_last_completed_task(self, task_plan: 'TaskPlan'):
        """设置最后完成的任务，用于检测改进请求"""
        self.last_completed_task = task_plan
    
    async def _stream_print(self, message: str = "", end: str = "\n"):
        """流式输出函数，支持终端和Web前端"""
        if self.stream_callback:
            # Web前端模式：通过回调发送到前端
            await self.stream_callback(message + end)
        else:
            # 终端模式：直接打印
            print(message, end=end, flush=True)
    
    async def _load_tools(self) -> None:
        """加载所有可用工具"""
        await self.tool_manager.load_all_tools()
    
    async def analyze_task(self, user_input: str) -> TaskPlan:
        """
        分析用户任务，生成执行计划
        
        Args:
            user_input: 用户输入的任务描述
            
        Returns:
            TaskPlan: 完整的任务计划
        """
        logger.info(f"📋 开始分析任务: {user_input[:100]}...")
        
        try:
            # 首先检查是否为任务改进请求
            if self.last_completed_task:
                is_improvement = await self._detect_task_improvement(user_input)
                if is_improvement:
                    logger.info("🔄 检测到任务改进请求")
                    return await self._handle_task_improvement(user_input, self.last_completed_task)
            
            # 其次检测是否为对话而非任务
            is_conversation = await self._detect_conversation(user_input)
            if is_conversation:
                logger.info("💬 检测到对话内容，直接回复")
                # 创建对话类型的TaskPlan，包含直接回复
                conversation_plan = TaskPlan(
                    user_input=user_input,
                    task_type="对话",
                    complexity_level="simple",
                    plan=Plan(steps=[
                        Step(
                            step_description="直接对话回复",
                            function_name="chat_response",
                            args={"response": await self._generate_conversation_response(user_input)},
                            is_final=True
                        )
                    ]),
                    status=TaskStatus.PLANNING,
                    is_conversation=True  # 标记为对话
                )
                return conversation_plan
            
            # 发射任务分析开始事件
            if self.event_emitter:
                await self.event_emitter.emit_task_analysis_start(user_input)
                # 小延迟让前端看到事件
                await asyncio.sleep(0.5)
            
            # 确保工具已加载
            await self._load_tools()
            
            # 第一步：使用改进的明确度分析
            if self.event_emitter:
                await self.event_emitter.emit_clarity_check_start()
                # 小延迟让前端看到事件
                await asyncio.sleep(0.3)
            
            clarity_result = await self.clarity_analyzer.analyze_clarity(user_input)
            logger.info(f"📊 任务明确度评分: {clarity_result.clarity_score}/10")
            
            # 发射明确度评分事件
            if self.event_emitter:
                await self.event_emitter.emit_clarity_score(
                    clarity_result.clarity_score / 10.0,
                    clarity_result.needs_clarification,
                    getattr(clarity_result, 'questions', [])
                )
                # 小延迟让前端处理
                await asyncio.sleep(0.5)
            
            # 第二步：基于明确度决定是否需要澄清
            if clarity_result.needs_clarification and clarity_result.clarity_score < 6:
                clarification_result = await self._analyze_requirements(user_input)
                if clarification_result.get("needs_clarification", False):
                    logger.info("❓ 任务需要澄清")
                    
                    # 发射需要澄清事件
                    if self.event_emitter:
                        await self.event_emitter.emit_general_progress(
                            "clarification_needed",
                            "任务需要进一步澄清"
                        )
                    
                    return TaskPlan(
                        user_input=user_input,
                        task_type="需要澄清",
                        complexity_level="unknown",
                        plan=Plan(steps=[]),
                        requires_clarification=True,
                        clarification_questions=clarification_result.get("questions", [])
                    )
            
            # 第三步：生成执行计划
            logger.info("🔧 生成执行计划...")
            
            # 先分析任务类型和复杂度
            task_type = await self._analyze_task_type(user_input)
            if self.event_emitter:
                await self.event_emitter.emit_task_type_detected(task_type, 0.8)  # 假设80%置信度
                await asyncio.sleep(0.3)
            
            # 发射计划生成开始事件
            if self.event_emitter:
                await self.event_emitter.emit_plan_generation_start("unknown")  # 复杂度稍后确定
                await asyncio.sleep(0.5)
            
            plan = await self._generate_plan(user_input)
            
            # 发射每个步骤生成事件（增加延迟）
            if self.event_emitter:
                for i, step in enumerate(plan.steps):
                    await self.event_emitter.emit_plan_step_generated(
                        i, len(plan.steps), step.step_description, step.function_name
                    )
                    # 每个步骤之间稍微延迟，让前端能看到逐个生成
                    await asyncio.sleep(0.2)
            
            # 第四步：验证计划中的工具（不修改，只验证）
            if self.event_emitter:
                await self.event_emitter.emit_general_progress(
                    "plan_validation",
                    "验证计划中的工具可用性..."
                )
                await asyncio.sleep(0.3)
            
            validated_plan = await self._validate_plan(plan)
            
            # 第五步：分析任务复杂度和类型
            task_analysis = await self._analyze_task_complexity(user_input, validated_plan)
            
            task_plan = TaskPlan(
                user_input=user_input,
                task_type=task_analysis.get("task_type", task_type),
                complexity_level=task_analysis.get("complexity_level", "medium"),
                plan=validated_plan,
                status=TaskStatus.PLANNING
            )
            
            # 发射计划生成完成事件
            if self.event_emitter:
                await self.event_emitter.emit_plan_generated(
                    task_plan.task_id,
                    len(validated_plan.steps),
                    task_plan.task_type
                )
                await asyncio.sleep(0.5)
            
            logger.info(f"✅ 任务分析完成，生成{len(validated_plan.steps)}个执行步骤")
            await self._format_plan_output(task_plan)
            return task_plan
            
        except Exception as e:
            logger.error(f"❌ 任务分析失败: {e}")
            if self.event_emitter:
                await self.event_emitter.emit_general_progress(
                    "analysis_failed",
                    f"任务分析失败: {str(e)}"
                )
            raise
    
    async def _analyze_requirements(self, user_input: str) -> Dict[str, Any]:
        """分析用户需求，判断是否需要追问"""
        try:
            messages = [
                {"role": "system", "content": IMPROVED_REASON_SYSTEM_PROMPT},
                {"role": "user", "content": user_input}
            ]
            
            await self._stream_print("🤔 分析是否需要澄清...")

            response = self.llm_client.beta.chat.completions.parse(
                    model=self.model_name,
                    messages=messages,
                    temperature=0.3,
                    response_format=TaskNeedClarification
                )
            response_text = json.loads(response.choices[0].message.content.strip())
            
            if response_text.get("need_clarification", False):
                questions_list = response_text.get("questions", [])
                if isinstance(questions_list, list):
                    valid_questions = [q.strip() for q in questions_list if isinstance(q, str) and q.strip() and ('?' in q or '？' in q)]
                    return {
                        "needs_clarification": True,
                        "questions": valid_questions if valid_questions else ["请提供更多详细信息以便我为您制定解决方案。"]
                    }
                else:
                    return {
                        "needs_clarification": True,
                        "questions": ["请提供更多详细信息以便我为您制定解决方案。"]
                    }
            else:
                # 不需要追问的情况
                return {"needs_clarification": False}
                
        except Exception as e:
            logger.error(f"需求分析失败: {e}")
            return {"needs_clarification": False}
    
    async def _generate_plan(self, user_input: str) -> Plan:
        """生成具体的执行计划"""
        try:
            # 获取工具信息
            tools_info = self.tool_manager.get_tools_for_planning()
            
            # 生成工具约束提示
            tool_constraint = self.tool_manager.generate_tool_constraint_prompt()
            
            # 格式化提示词
            formatted_prompt = PLAN_SYSTEM_PROMPT.format(
                tools=json.dumps(tools_info, ensure_ascii=False, indent=2),
                output_format=json.dumps(Plan.model_json_schema(), ensure_ascii=False, indent=2)
            ) + tool_constraint
            
            messages = [
                {"role": "system", "content": formatted_prompt},
                {"role": "user", "content": user_input}
            ]
            
            await self._stream_print("⚙️ 生成执行计划...")
            # 添加流式输出
            response = self.llm_client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.1,
                stream=True
            )
            
            # 处理流式响应
            full_response = ""
            for chunk in response:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    await self._stream_print(content, end="")
                    full_response += content
            await self._stream_print()  # 换行
            
            response_text = full_response.strip()
            
            # 尝试解析JSON响应
            try:
                # 提取JSON部分
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    json_text = response_text[json_start:json_end].strip()
                elif "{" in response_text:
                    json_start = response_text.find("{")
                    json_end = response_text.rfind("}") + 1
                    json_text = response_text[json_start:json_end]
                else:
                    raise ValueError("未找到JSON格式的计划")
                
                plan_data = json.loads(json_text)
                return Plan(**plan_data)
                
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"解析计划JSON失败: {e}")
                # 如果解析失败，创建一个默认计划
                return self._create_fallback_plan(user_input)
                
        except Exception as e:
            logger.error(f"生成计划失败: {e}")
            return self._create_fallback_plan(user_input)
    
    async def _validate_plan(self, plan: Plan) -> Plan:
        """验证计划中的工具调用（不修改工具名称）"""
        available_tools = self.tool_manager.get_available_tool_names()
        
        for step in plan.steps:
            # 只验证工具是否存在，不进行修改
            if not self.tool_manager.is_tool_available(step.function_name):
                logger.warning(f"⚠️  工具不存在: {step.function_name}，可用工具: {available_tools}")
                # 可以在这里记录警告，但不修改工具名称
        
        return plan
    
    def _create_fallback_plan(self, user_input: str) -> Plan:
        """创建后备计划"""
        return Plan(steps=[
            Step(
                step_description=f"处理用户请求: {user_input}",
                function_name="generate_answer_tool",
                args={"query": user_input},
                is_final=True
            )
        ])
    
    async def _analyze_task_type(self, user_input: str) -> str:
        """分析任务类型"""
        try:
            messages = [
                {"role": "system", "content": "请分析用户输入的任务类型"},
                {"role": "user", "content": user_input}
            ]
            
            await self._stream_print("🔍 分析任务类型...")
            # 对于简单的分析任务，先尝试流式输出
            response = self.llm_client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.1,
                stream=True
            )
            
            # 处理流式响应
            full_response = ""
            for chunk in response:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    await self._stream_print(content, end="")
                    full_response += content
            await self._stream_print()  # 换行
            
            # 如果需要结构化输出，使用非流式方式
            response = self.llm_client.beta.chat.completions.parse(
                model=self.model_name,
                messages=messages,
                temperature=0.1,
                response_format=TaskType
            )
            response_text = response.choices[0].message.parsed
            return response_text.type
        except Exception as e:
            logger.error(f"任务类型分析失败: {e}")
            return "通用任务"
    
    async def _analyze_task_complexity(self, user_input: str, plan: Plan) -> Dict[str, str]:
        """分析任务复杂度和类型"""
        step_count = len(plan.steps)
        
        # 基于步骤数量判断复杂度
        if step_count == 1:
            complexity = "simple"
        elif step_count <= 3:
            complexity = "medium"
        else:
            complexity = "complex"
        
        # 基于大模型判断任务类型
        task_type = await self._analyze_task_type(user_input)
        
        return {
            "complexity_level": complexity,
            "task_type": task_type
        }
    
    async def _format_plan_output(self, task_plan: TaskPlan):
        """格式化并输出任务计划"""
        try:
            await self._stream_print(f"\n📋 任务分析完成！")
            await self._stream_print(f"📊 任务类型: {task_plan.task_type}")
            await self._stream_print(f"⚡ 复杂度: {task_plan.complexity_level}")
            await self._stream_print(f"🔧 执行步骤: {len(task_plan.plan.steps)}个\n")
            
            for i, step in enumerate(task_plan.plan.steps, 1):
                await self._stream_print(f"步骤{i}: {step.step_description}")
                await self._stream_print(f"   工具: {step.function_name}")
                if hasattr(step, 'args') and step.args:
                    await self._stream_print(f"   参数: {step.args}")
                await self._stream_print("")
            
        except Exception as e:
            logger.warning(f"格式化计划输出失败: {e}")
    
    async def _detect_conversation(self, user_input: str) -> bool:
        """
        检测用户输入是否为对话而非任务
        
        Args:
            user_input: 用户输入
            
        Returns:
            bool: True表示是对话，False表示是任务
        """
        conversation_prompt = """
请判断用户输入是对话交流还是具体任务请求。

对话交流特征（返回conversation）：
- 问候语：你好、早上好、晚安、hi、hello等
- 感谢表达：谢谢、感谢、太好了等
- 简单闲聊：今天天气如何、你是谁、你好吗等  
- 系统询问：你能做什么、你的功能是什么等
- 纯粹的情感表达或评价

任务请求特征（返回task）：
- 包含明确动作词：生成、创建、搜索、分析、转换、制定、学习、写、做等
- 有具体目标：学习某个技能、制定计划、创建文件、搜索信息等
- 请求帮助完成具体事情：即使表述不够清晰，但有明确的做事意图
- 需要产出结果：文件、计划、分析报告、代码等

判断原则：
- 只有纯粹的问候、感谢、闲聊才是对话
- 任何带有"做事"意图的都是任务，即使描述不够详细
- "我想学习..."、"请帮我制定..."、"我需要..."等都是任务
- 宁可误判为任务，也不要把任务误判为对话

输入: {user_input}

请直接回答: conversation 或 task
"""
        
        try:
            messages = [
                {"role": "system", "content": conversation_prompt.format(user_input=user_input)}
            ]
            
            response = self.llm_client.beta.chat.completions.parse(
                model=self.model_name,
                messages=messages,
                temperature=0.1,
                max_tokens=10,
                response_format=IsTaskOrConversation
            )

            result = response.choices[0].message.parsed
            return result.type == "conversation"
            
        except Exception as e:
            logger.error(f"对话检测失败: {e}")
            # 默认认为是任务，避免误判
            return False
    
    async def _generate_conversation_response(self, user_input: str) -> str:
        """
        为对话类型的输入生成回复
        
        Args:
            user_input: 用户输入
            
        Returns:
            str: 对话回复
        """
        conversation_system = """
你是一个友好的AI助手。用户正在与你进行日常对话，请自然地回应。
保持简洁、友好和有帮助的语调。
如果用户问候，请礼貌回应。
如果用户感谢，请客气回复。
如果用户询问你的能力，请简要介绍你可以帮助完成的任务类型。
"""
        
        try:
            messages = [
                {"role": "system", "content": conversation_system},
                {"role": "user", "content": user_input}
            ]
            
            response = self.llm_client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.7,
                max_tokens=150
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"生成对话回复失败: {e}")
            return "您好！我是您的AI助手，有什么可以帮您的吗？"
    
    async def refine_plan_with_feedback(self, task_plan: TaskPlan, user_feedback: str) -> TaskPlan:
        """根据用户反馈优化计划"""
        try:
            logger.info("🔄 根据用户反馈优化计划...")
            
            # 结合原始需求和用户反馈重新生成计划
            combined_input = f"{task_plan.user_input}\n\n用户补充要求: {user_feedback}"
            new_plan = await self._generate_plan(combined_input)
            
            # 更新任务计划
            task_plan.plan = new_plan
            task_plan.user_input = combined_input
            task_plan.requires_clarification = False
            task_plan.clarification_questions = []
            
            logger.info("✅ 计划优化完成")
            return task_plan
            
        except Exception as e:
            logger.error(f"❌ 计划优化失败: {e}")
            raise 
    
    async def _detect_task_improvement(self, user_input: str) -> bool:
        """
        检测用户输入是否为对上一个任务的改进请求
        
        Args:
            user_input: 用户输入
            
        Returns:
            bool: True表示是改进请求，False表示不是
        """
        improvement_prompt = """
请判断用户输入是否为对上一个任务的改进请求。

改进请求特征：
- 使用"增加"、"添加"、"修改"、"改进"、"优化"、"调整"等词汇
- 提到"背景"、"样式"、"颜色"、"功能"、"界面"等具体改进点
- 使用"帮我"、"给我"、"让它"等指代性词汇，暗示对现有内容的修改
- 没有明确说明要创建全新的东西
- 语境暗示是在现有基础上进行修改

非改进请求特征：
- 明确要求创建全新的项目或文件
- 与上一个任务完全无关的新需求
- 独立的问题或任务

示例：
- "帮我增加一个好看的背景" → 改进请求
- "添加音效" → 改进请求  
- "修改颜色为蓝色" → 改进请求
- "优化界面" → 改进请求
- "生成一个新的Python程序" → 非改进请求
- "搜索机器学习资料" → 非改进请求

输入: {user_input}

请直接回答: improvement 或 new_task
"""
        
        try:
            messages = [
                {"role": "system", "content": improvement_prompt.format(user_input=user_input)}
            ]
            
            response = self.llm_client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.1,
                max_tokens=10
            )
            
            result = response.choices[0].message.content.strip().lower()
            return "improvement" in result
            
        except Exception as e:
            logger.error(f"任务改进检测失败: {e}")
            # 默认认为不是改进请求
            return False
    
    async def _handle_task_improvement(self, user_input: str, last_task: 'TaskPlan') -> 'TaskPlan':
        """
        处理任务改进请求
        
        Args:
            user_input: 用户的改进要求
            last_task: 上一个完成的任务
            
        Returns:
            TaskPlan: 改进任务的计划
        """
        try:
            logger.info("🔧 处理任务改进请求...")
            
            # 发射任务分析开始事件
            if self.event_emitter:
                await self.event_emitter.emit_task_analysis_start(f"改进: {user_input}")
                await asyncio.sleep(0.5)
            
            # 确保工具已加载
            await self._load_tools()
            
            # 获取上一个任务的文件信息
            last_task_info = ""
            if hasattr(last_task, 'plan') and last_task.plan.steps:
                last_task_info = f"上一个任务: {last_task.user_input}\n"
                if hasattr(last_task, 'generated_files') and last_task.generated_files:
                    last_task_info += f"已生成的文件: {', '.join(last_task.generated_files)}\n"
            
            # 构建改进请求的完整描述
            improvement_request = f"""
基于上一个任务的结果进行改进：

{last_task_info}
用户改进要求: {user_input}

请在现有文件的基础上进行修改和改进，不要重新创建全新的文件。
"""
            
            # 发射计划生成开始事件
            if self.event_emitter:
                await self.event_emitter.emit_plan_generation_start("improvement")
                await asyncio.sleep(0.5)
            
            # 生成改进计划
            plan = await self._generate_improvement_plan(improvement_request, last_task)
            
            # 发射每个步骤生成事件
            if self.event_emitter:
                for i, step in enumerate(plan.steps):
                    await self.event_emitter.emit_plan_step_generated(
                        i, len(plan.steps), step.step_description, step.function_name
                    )
                    await asyncio.sleep(0.2)
            
            # 验证计划
            validated_plan = await self._validate_plan(plan)
            
            # 创建改进任务计划
            improvement_task = TaskPlan(
                user_input=f"改进: {user_input}",
                task_type="任务改进",
                complexity_level="medium",
                plan=validated_plan,
                status=TaskStatus.PLANNING,
                parent_task_id=last_task.task_id if hasattr(last_task, 'task_id') else None
            )
            
            # 发射计划生成完成事件
            if self.event_emitter:
                await self.event_emitter.emit_plan_generated(
                    improvement_task.task_id,
                    len(validated_plan.steps),
                    improvement_task.task_type
                )
                await asyncio.sleep(0.5)
            
            logger.info(f"✅ 任务改进计划生成完成，包含{len(validated_plan.steps)}个步骤")
            await self._format_plan_output(improvement_task)
            
            return improvement_task
            
        except Exception as e:
            logger.error(f"❌ 任务改进处理失败: {e}")
            # 如果改进处理失败，降级为普通任务处理
            return await self._handle_as_normal_task(user_input)
    
    async def _generate_improvement_plan(self, improvement_request: str, last_task: 'TaskPlan') -> Plan:
        """
        生成改进计划
        
        Args:
            improvement_request: 改进请求描述
            last_task: 上一个任务
            
        Returns:
            Plan: 改进计划
        """
        improvement_prompt = """
# 角色：
你是一个任务改进专家，专门负责在现有成果基础上进行优化和改进。

# 任务：
根据用户的改进要求，制定具体的改进计划。重点是在现有文件和成果的基础上进行修改，而不是重新创建。

# 改进原则：
1. 优先使用read_file_tool读取现有文件
2. 使用file_generation_tool修改现有文件或创建增强版本
3. 保持原有功能的同时添加新功能
4. 如果需要图片素材，使用image_generation_tool
5. 合理使用其他工具来完善改进

# 工具列表：
```
{tools}
```

# 输出格式：
```json
{output_format}
```

# 注意事项：
1. 第一步通常是读取现有文件内容
2. 基于现有内容进行改进，不要重新开始
3. function_name必须从工具列表中选择
4. 最后一步设置is_final为true
"""
        
        try:
            # 获取工具信息
            tools_info = self.tool_manager.get_tools_for_planning()
            tool_constraint = self.tool_manager.generate_tool_constraint_prompt()
            
            # 格式化提示词
            formatted_prompt = improvement_prompt.format(
                tools=json.dumps(tools_info, ensure_ascii=False, indent=2),
                output_format=json.dumps(Plan.model_json_schema(), ensure_ascii=False, indent=2)
            ) + tool_constraint
            
            messages = [
                {"role": "system", "content": formatted_prompt},
                {"role": "user", "content": improvement_request}
            ]
            
            await self._stream_print("⚙️ 生成改进计划...")
            response = self.llm_client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.1,
                stream=True
            )
            
            # 处理流式响应
            full_response = ""
            for chunk in response:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    await self._stream_print(content, end="")
                    full_response += content
            await self._stream_print()  # 换行
            
            response_text = full_response.strip()
            
            # 解析JSON响应
            try:
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    json_text = response_text[json_start:json_end].strip()
                elif "{" in response_text:
                    json_start = response_text.find("{")
                    json_end = response_text.rfind("}") + 1
                    json_text = response_text[json_start:json_end]
                else:
                    raise ValueError("未找到JSON格式的计划")
                
                plan_data = json.loads(json_text)
                return Plan(**plan_data)
                
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"解析改进计划JSON失败: {e}")
                return self._create_fallback_improvement_plan(improvement_request)
                
        except Exception as e:
            logger.error(f"生成改进计划失败: {e}")
            return self._create_fallback_improvement_plan(improvement_request)
    
    def _create_fallback_improvement_plan(self, improvement_request: str) -> Plan:
        """创建后备改进计划"""
        return Plan(steps=[
            Step(
                step_description=f"处理改进请求: {improvement_request}",
                function_name="file_generation_tool",
                args={
                    "prompt": improvement_request,
                    "file_type": "py",
                    "file_name": "improved_version"
                },
                is_final=True
            )
        ])
    
    async def _handle_as_normal_task(self, user_input: str) -> 'TaskPlan':
        """将输入作为普通任务处理（改进失败时的降级方案）"""
        logger.info("🔄 改进处理失败，降级为普通任务处理")
        # 清除last_completed_task避免递归
        self.last_completed_task = None
        return await self.analyze_task(user_input) 