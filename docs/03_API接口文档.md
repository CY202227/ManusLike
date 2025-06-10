# 数字员工API接口文档

## 📖 概述

本文档描述了数字员工系统提供的所有API接口，包括核心业务接口、工具管理接口、文件管理接口等。系统采用异步设计，所有接口都支持并发调用。

## 🏗️ 接口架构

### 接口分层

```
┌─────────────────────────────────────────┐
│              用户接口层                    │
│  ┌─────────────────┬─────────────────┐   │
│  │   终端接口        │    Web API接口   │   │
│  │ (terminal_chat) │   (FastAPI)    │   │
│  └─────────────────┴─────────────────┘   │
└─────────────────────────────────────────┘
                      │
┌─────────────────────────────────────────┐
│              核心业务接口                  │
│  ┌─────────────────┬─────────────────┐   │
│  │   任务规划接口    │   任务执行接口    │   │
│  │ (TaskPlanner)   │ (TaskExecutor)  │   │
│  └─────────────────┴─────────────────┘   │
└─────────────────────────────────────────┘
                      │
┌─────────────────────────────────────────┐
│              基础服务接口                  │
│  ┌─────────────────┬─────────────────┐   │
│  │   工具管理接口    │   文件管理接口    │   │
│  │ (ToolManager)   │ (FileManager)   │   │
│  └─────────────────┴─────────────────┘   │
└─────────────────────────────────────────┘
```

## 🧠 任务规划接口

### TaskPlanner 类接口

#### analyze_task()

分析用户任务并生成执行计划

**接口签名**:
```python
async def analyze_task(self, user_input: str) -> TaskPlan
```

**参数**:
- `user_input` (str): 用户输入的任务描述

**返回值**:
- `TaskPlan`: 完整的任务计划对象

**使用示例**:
```python
# 初始化任务规划器
task_planner = TaskPlanner(
    llm_client=openai_client,
    tool_manager=tool_manager,
    model_name="Qwen-72B"
)

# 分析任务
user_input = "生成一个Python版的贪吃蛇游戏"
task_plan = await task_planner.analyze_task(user_input)

print(f"任务ID: {task_plan.task_id}")
print(f"任务类型: {task_plan.task_type}")
print(f"复杂度: {task_plan.complexity_level}")
print(f"步骤数量: {len(task_plan.plan.steps)}")
```

**返回示例**:
```json
{
  "task_id": "task_123456",
  "user_input": "生成一个Python版的贪吃蛇游戏",
  "task_type": "代码开发",
  "complexity_level": "medium",
  "plan": {
    "steps": [
      {
        "step_id": "step_1",
        "step_description": "生成贪吃蛇游戏的主要代码",
        "function_name": "file_generation_tool",
        "args": {
          "prompt": "创建一个完整的Python贪吃蛇游戏",
          "file_type": "py",
          "file_name": "snake_game"
        },
        "is_final": true
      }
    ]
  },
  "status": "planning",
  "requires_clarification": false
}
```

#### refine_plan_with_feedback()

根据用户反馈优化任务计划

**接口签名**:
```python
async def refine_plan_with_feedback(self, task_plan: TaskPlan, user_feedback: str) -> TaskPlan
```

**参数**:
- `task_plan` (TaskPlan): 原始任务计划
- `user_feedback` (str): 用户反馈内容

**返回值**:
- `TaskPlan`: 优化后的任务计划

**使用示例**:
```python
# 优化计划
feedback = "请增加游戏音效和背景音乐"
improved_plan = await task_planner.refine_plan_with_feedback(task_plan, feedback)
```

### TaskClarityAnalyzer 类接口

#### analyze_clarity()

分析任务明确度

**接口签名**:
```python
async def analyze_clarity(self, user_input: str) -> TaskClarityScore
```

**参数**:
- `user_input` (str): 用户输入内容

**返回值**:
- `TaskClarityScore`: 明确度评分结果

**返回示例**:
```json
{
  "clarity_score": 8,
  "has_clear_action": true,
  "has_sufficient_params": true,
  "is_simple_task": false,
  "needs_clarification": false
}
```

## ⚙️ 任务执行接口

### TaskExecutor 类接口

#### execute_plan()

执行完整的任务计划

**接口签名**:
```python
async def execute_plan(self, task_plan: TaskPlan, user_id: str = "default") -> ExecutionResult
```

**参数**:
- `task_plan` (TaskPlan): 要执行的任务计划
- `user_id` (str, 可选): 用户ID，默认为"default"

**返回值**:
- `ExecutionResult`: 执行结果

**使用示例**:
```python
# 初始化执行器
task_executor = TaskExecutor(
    tool_manager=tool_manager,
    file_manager=file_manager,
    event_emitter=event_emitter
)

# 执行任务计划
execution_result = await task_executor.execute_plan(task_plan, user_id="user123")

print(f"执行成功: {execution_result.success}")
print(f"执行时间: {execution_result.execution_time:.2f}秒")
print(f"生成文件: {len(execution_result.files_generated)}个")
```

**返回示例**:
```json
{
  "task_id": "task_123456",
  "success": true,
  "results": [
    {
      "step_id": "step_1",
      "step_description": "生成贪吃蛇游戏的主要代码",
      "function_name": "file_generation_tool",
      "result": {
        "success": true,
        "file_path": "/data/task_files/user123/task_123456/snake_game.py",
        "file_type": "py"
      },
      "status": "completed"
    }
  ],
  "execution_time": 15.3,
  "files_generated": [
    "snake_game.py"
  ]
}
```

#### execute_step_with_events()

执行单个步骤并发射事件

**接口签名**:
```python
async def execute_step_with_events(self, step: Step) -> Any
```

**参数**:
- `step` (Step): 要执行的步骤

**返回值**:
- `Any`: 步骤执行结果

#### get_execution_status()

获取当前执行状态

**接口签名**:
```python
def get_execution_status(self) -> Dict[str, Any]
```

**返回值**:
- `Dict[str, Any]`: 当前执行状态

**返回示例**:
```json
{
  "current_task_id": "task_123456",
  "status": "executing",
  "current_step": 2,
  "total_steps": 3,
  "elapsed_time": 8.5
}
```

## 🛠️ 工具管理接口

### ToolManager 类接口

#### load_all_tools()

加载所有可用工具

**接口签名**:
```python
async def load_all_tools(self) -> None
```

**使用示例**:
```python
tool_manager = ToolManager(mcp_client)
await tool_manager.load_all_tools()
print(f"已加载{len(tool_manager.available_tools)}个工具")
```

#### call_tool()

统一工具调用接口

**接口签名**:
```python
async def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Any
```

**参数**:
- `tool_name` (str): 工具名称
- `args` (Dict[str, Any]): 工具参数

**返回值**:
- `Any`: 工具执行结果

**使用示例**:
```python
# 调用文件生成工具
result = await tool_manager.call_tool(
    tool_name="file_generation_tool",
    args={
        "prompt": "创建一个简单的HTML页面",
        "file_type": "html",
        "file_name": "index"
    }
)
print(f"生成结果: {result}")
```

#### get_available_tool_names()

获取所有可用工具名称

**接口签名**:
```python
def get_available_tool_names(self) -> List[str]
```

**返回值**:
- `List[str]`: 工具名称列表

**返回示例**:
```json
[
  "file_generation_tool",
  "web_search_tool",
  "image_generation_tool",
  "read_file_tool",
  "generate_answer_tool"
]
```

#### validate_tool_call()

验证工具调用合法性

**接口签名**:
```python
def validate_tool_call(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]
```

**参数**:
- `tool_name` (str): 工具名称
- `args` (Dict[str, Any]): 工具参数

**返回值**:
- `Dict[str, Any]`: 验证结果

**返回示例**:
```json
{
  "is_valid": true
}
```

#### get_tools_for_planning()

获取用于任务规划的工具信息

**接口签名**:
```python
def get_tools_for_planning(self) -> List[Dict[str, Any]]
```

**返回值**:
- `List[Dict[str, Any]]`: 工具信息列表

**返回示例**:
```json
[
  {
    "name": "file_generation_tool",
    "description": "生成各种类型的文件",
    "args": {
      "prompt": "string",
      "file_type": "string",
      "file_name": "string"
    }
  },
  {
    "name": "web_search_tool", 
    "description": "搜索网络信息",
    "args": {
      "query": "string",
      "num_results": "integer"
    }
  }
]
```

## 📁 文件管理接口

### FileManager 类接口

#### create_task_directory()

为任务创建专用目录

**接口签名**:
```python
def create_task_directory(self, task_id: str, user_id: str = "default") -> Path
```

**参数**:
- `task_id` (str): 任务ID
- `user_id` (str, 可选): 用户ID

**返回值**:
- `Path`: 创建的目录路径

**使用示例**:
```python
file_manager = FileManager()
task_dir = file_manager.create_task_directory("task_123456", "user123")
print(f"任务目录: {task_dir}")
```

#### register_file()

注册文件到管理系统

**接口签名**:
```python
def register_file(self, task_id: str, file_path: str, file_type: str, 
                 step_id: str, description: str, user_id: str = "default") -> str
```

**参数**:
- `task_id` (str): 任务ID
- `file_path` (str): 文件路径
- `file_type` (str): 文件类型
- `step_id` (str): 步骤ID
- `description` (str): 文件描述
- `user_id` (str, 可选): 用户ID

**返回值**:
- `str`: 文件注册ID

**使用示例**:
```python
file_id = file_manager.register_file(
    task_id="task_123456",
    file_path="/path/to/file.py",
    file_type="py",
    step_id="step_1",
    description="Python游戏代码",
    user_id="user123"
)
```

#### get_task_files()

获取任务的所有文件信息

**接口签名**:
```python
def get_task_files(self, task_id: str, user_id: str = "default") -> List[Dict]
```

**参数**:
- `task_id` (str): 任务ID
- `user_id` (str, 可选): 用户ID

**返回值**:
- `List[Dict]`: 文件信息列表

**返回示例**:
```json
[
  {
    "file_id": "file_001",
    "file_name": "snake_game.py",
    "file_path": "/data/task_files/user123/task_123456/snake_game.py",
    "file_type": "py",
    "file_size": 5432,
    "step_id": "step_1",
    "description": "Python贪吃蛇游戏",
    "created_at": "2024-01-01T10:00:00"
  }
]
```

#### create_download_package()

创建任务文件的下载包

**接口签名**:
```python
def create_download_package(self, task_id: str, user_id: str = "default") -> str
```

**参数**:
- `task_id` (str): 任务ID
- `user_id` (str, 可选): 用户ID

**返回值**:
- `str`: 下载包路径

**使用示例**:
```python
download_path = file_manager.create_download_package("task_123456", "user123")
print(f"下载包路径: {download_path}")
```

## 📡 事件发射接口

### ExecutionEventEmitter 类接口

#### emit_task_start()

发射任务开始事件

**接口签名**:
```python
async def emit_task_start(self, task_plan: TaskPlan) -> None
```

#### emit_step_start()

发射步骤开始事件

**接口签名**:
```python
async def emit_step_start(self, step: Step) -> None
```

#### emit_tool_call_complete()

发射工具调用完成事件

**接口签名**:
```python
async def emit_tool_call_complete(self, tool_name: str, result: Any, duration: float) -> None
```

**参数**:
- `tool_name` (str): 工具名称
- `result` (Any): 调用结果
- `duration` (float): 调用耗时(秒)

### WebSocket事件格式

所有WebSocket事件都遵循统一格式：

```json
{
  "event_type": "事件类型",
  "timestamp": "2024-01-01T10:00:00",
  "data": {
    // 事件具体数据
  }
}
```

**事件类型列表**:

| 事件类型 | 描述 | 数据字段 |
|---------|------|---------|
| `task_analysis_start` | 任务分析开始 | `user_input` |
| `task_start` | 任务执行开始 | `task_id`, `task_type` |
| `step_start` | 步骤开始 | `step_id`, `description` |
| `step_complete` | 步骤完成 | `step_id`, `result`, `duration` |
| `tool_call_start` | 工具调用开始 | `tool_name`, `args` |
| `tool_call_complete` | 工具调用完成 | `tool_name`, `result`, `duration` |
| `task_complete` | 任务完成 | `task_id`, `success`, `files_generated` |

## 🌐 Web API接口

### RESTful API端点

#### POST /api/tasks/analyze

分析任务并生成计划

**请求体**:
```json
{
  "user_input": "生成一个Python程序",
  "user_id": "user123"
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "task_id": "task_123456",
    "task_type": "代码开发",
    "complexity_level": "medium",
    "plan": {...}
  }
}
```

#### POST /api/tasks/execute

执行任务计划

**请求体**:
```json
{
  "task_plan": {...},
  "user_id": "user123"
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "task_id": "task_123456",
    "execution_result": {...}
  }
}
```

#### GET /api/tasks/{task_id}/status

获取任务状态

**响应**:
```json
{
  "success": true,
  "data": {
    "task_id": "task_123456",
    "status": "executing",
    "progress": 0.6,
    "current_step": 2,
    "total_steps": 3
  }
}
```

#### GET /api/tasks/{task_id}/files

获取任务文件列表

**响应**:
```json
{
  "success": true,
  "data": {
    "files": [
      {
        "file_id": "file_001",
        "file_name": "snake_game.py",
        "file_type": "py",
        "download_url": "/api/files/download/file_001"
      }
    ]
  }
}
```

#### GET /api/files/download/{file_id}

下载文件

**响应**: 文件二进制内容

### WebSocket连接

#### 连接端点
```
ws://localhost:8000/ws/{user_id}
```

#### 消息格式
客户端和服务器之间的所有消息都使用JSON格式：

**客户端发送**:
```json
{
  "type": "subscribe",
  "data": {
    "task_id": "task_123456"
  }
}
```

**服务器推送**:
```json
{
  "event_type": "step_complete",
  "timestamp": "2024-01-01T10:00:00",
  "data": {
    "step_id": "step_1",
    "result": {...}
  }
}
```

## 🔧 错误处理

### 错误响应格式

所有API错误都使用统一格式：

```json
{
  "success": false,
  "error": {
    "code": "TASK_EXECUTION_FAILED",
    "message": "任务执行失败",
    "details": "具体错误信息"
  }
}
```

### 常见错误代码

| 错误代码 | 描述 | HTTP状态码 |
|---------|------|-----------|
| `INVALID_INPUT` | 无效输入参数 | 400 |
| `TASK_NOT_FOUND` | 任务不存在 | 404 |
| `TOOL_NOT_AVAILABLE` | 工具不可用 | 503 |
| `EXECUTION_FAILED` | 执行失败 | 500 |
| `FILE_NOT_FOUND` | 文件不存在 | 404 |
| `PERMISSION_DENIED` | 权限不足 | 403 |

## 📊 性能指标

### 接口性能基准

| 接口 | 平均响应时间 | 并发支持 |
|------|-------------|---------|
| `analyze_task()` | 2-5秒 | 10个并发 |
| `execute_plan()` | 10-60秒 | 5个并发 |
| `call_tool()` | 1-10秒 | 20个并发 |
| 文件下载 | <1秒 | 50个并发 |

### 资源限制

- 最大文件大小: 100MB
- 最大任务执行时间: 300秒
- 最大并发任务数: 10个
- WebSocket连接限制: 100个

## 🔒 安全考虑

### 认证和授权

```python
# API密钥认证
headers = {
    "Authorization": "Bearer your-api-key",
    "Content-Type": "application/json"
}

# 用户权限验证
def check_user_permission(user_id: str, resource: str) -> bool:
    # 权限检查逻辑
    pass
```

### 输入验证

所有API接口都会进行严格的输入验证：

- 参数类型检查
- 参数范围验证
- 恶意输入过滤
- SQL注入防护

### 访问控制

- 用户只能访问自己的任务和文件
- 基于角色的权限控制
- API调用频率限制
- 文件访问权限控制 