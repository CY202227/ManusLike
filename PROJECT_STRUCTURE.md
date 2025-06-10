# 数字员工项目结构说明

## 📁 建议的新项目结构

```
05.数字员工/
├── core/                          # 核心业务逻辑
│   ├── __init__.py
│   ├── task_planner.py           # 任务规划器 (从manual.py分离)
│   ├── task_executor.py          # 任务执行器
│   ├── file_manager.py           # 文件管理器
│   ├── result_collector.py       # 结果收集器
│   └── event_emitter.py          # 事件系统 (从manual.py分离)
│
├── tools/                         # 工具相关
│   ├── __init__.py
│   ├── tool_manager.py           # 工具管理器
│   ├── local_tools.py            # 本地工具 (从tools.py重命名)
│   └── functions/                # 工具函数实现
│       ├── __init__.py
│       ├── file_operations.py    # 文件操作 (从function/重构)
│       ├── chart_generator.py    # 图表生成
│       └── prompts/              # 提示词
│           ├── __init__.py
│           └── chart_prompt.py
│
├── communication/                 # 通信相关
│   ├── __init__.py
│   ├── mcp_client.py             # MCP客户端
│   ├── mcp_server.py             # MCP服务器
│   └── mcp_config.json           # MCP配置
│
├── interfaces/                    # 用户接口
│   ├── __init__.py
│   ├── terminal_chat.py          # 终端聊天界面
│   ├── start_terminal_chat.py    # 终端启动脚本
│   └── web/                      # Web界面 (frontend重命名)
│       └── ...
│
├── data/                         # 数据存储
│   ├── task_files/               # 任务文件
│   ├── execution_results/        # 执行结果
│   └── generated_files/          # 临时生成文件 (待废弃)
│
├── tests/                        # 测试文件
│   ├── __init__.py
│   ├── test_task_executor.py
│   ├── test_file_manager.py
│   └── test_integration.py
│
├── scripts/                      # 脚本文件
│   ├── start_system.py           # 系统启动脚本
│   └── setup.py                  # 环境设置脚本
│
├── docs/                         # 文档
│   ├── README.md
│   ├── API.md
│   ├── 项目规划.md
│   └── 优化计划书.md
│
├── config/                       # 配置文件
│   ├── __init__.py
│   └── settings.py               # 系统配置
│
├── requirements.txt              # 依赖包
└── .gitignore                    # Git忽略文件
```

## 📝 文件迁移计划

### 1. 创建新目录结构
- [x] 创建核心目录
- [x] 创建工具目录  
- [x] 创建通信目录
- [x] 创建接口目录
- [x] 创建数据目录
- [x] 创建测试目录
- [x] 创建脚本目录
- [x] 创建文档目录
- [x] 创建配置目录

### 2. 文件迁移映射

#### 核心业务逻辑 (core/)
- `task_executor.py` → `core/task_executor.py`
- `file_manager.py` → `core/file_manager.py` 
- `result_collector.py` → `core/result_collector.py`
- `manual.py` → 拆分为:
  - `core/task_planner.py` (TaskPlanner部分)
  - `core/event_emitter.py` (ExecutionEventEmitter部分)
  - `core/models.py` (数据模型部分)

#### 工具相关 (tools/)
- `tool_manager.py` → `tools/tool_manager.py`
- `tools.py` → `tools/local_tools.py`
- `function/` → `tools/functions/`
- `_prompt/` → `tools/functions/prompts/`

#### 通信相关 (communication/)
- `mcp_client.py` → `communication/mcp_client.py`
- `mcp_server.py` → `communication/mcp_server.py`
- `mcp_config.json` → `communication/mcp_config.json`

#### 用户接口 (interfaces/)
- `terminal_chat.py` → `interfaces/terminal_chat.py`
- `start_terminal_chat.py` → `interfaces/start_terminal_chat.py`
- `frontend/` → `interfaces/web/`

#### 数据存储 (data/)
- `task_files/` → `data/task_files/`
- `execution_results/` → `data/execution_results/`
- `generated_files/` → `data/generated_files/` (待废弃)

#### 测试文件 (tests/)
- `test.py` → `tests/test_integration.py`

#### 脚本文件 (scripts/)
- `start_system.py` → `scripts/start_system.py`

#### 文档 (docs/)
- `README.md` → `docs/README.md`
- `项目规划 - 类Manus AI系统开发.md` → `docs/项目规划.md`
- `优化计划书.md` → `docs/优化计划书.md`

### 3. 需要删除的文件
- `task_modifier.py` (内容为空)
- `__pycache__/` 目录

## 🎯 重构优势

1. **模块化**: 按功能分类，职责清晰
2. **可维护性**: 代码更易理解和修改
3. **可扩展性**: 新功能更容易添加
4. **测试友好**: 便于单元测试和集成测试
5. **部署简单**: 清晰的依赖关系 