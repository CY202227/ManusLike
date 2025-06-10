# Manus AI System - 智能代理系统

## 项目简介

基于FastAPI和WebSocket技术构建的类Manus AI智能代理系统，支持多用户同时使用，具备任务自动分解、独立执行和结果交付功能。

## 核心特性

- 🤖 **智能任务规划**: 自动分析用户需求，生成步骤化执行计划
- ⚡ **独立任务执行**: 自动调用工具和服务，无需人工干预
- 📊 **实时监控**: 类似Manus的分屏界面，实时显示执行状态
- 👥 **多用户支持**: 支持多个用户同时在线，独立会话管理
- 💬 **实时对话**: WebSocket实时通信，支持任务对话
- 📁 **结果收集**: 自动生成执行报告和文件下载

## 系统架构

```
Manus AI System
├── 后端组件
│   ├── TaskPlanner - 任务规划器
│   ├── TaskExecutor - 任务执行器  
│   ├── ToolManager - 工具管理器
│   ├── ResultCollector - 结果收集器
│   └── MultiMCPClient - MCP客户端
├── 前端界面
│   ├── 主页 - 用户登录和快速开始
│   ├── 聊天页面 - 分屏对话界面
│   └── 监控面板 - 实时执行状态
└── 工具生态
    ├── 网络搜索 - 信息检索
    ├── 文件生成 - 代码/文档生成
    ├── 图像生成 - AI绘图
    ├── 数据分析 - 图表生成
    └── AI对话 - 智能问答
```

## 快速开始

### 1. 环境要求

- Python 3.8+
- 已安装依赖包：
  ```bash
  pip install fastapi uvicorn jinja2 python-multipart websockets openai
  ```

### 2. 启动系统

**方式一：使用启动脚本（推荐）**
```bash
python start_system.py
```

**方式二：手动启动**
```bash
# 终端1：启动MCP服务器
python mcp_server.py

# 终端2：启动Web前端
python frontend/main.py
```

### 3. 访问系统

1. 打开浏览器访问：http://localhost:8000
2. 输入用户ID（如：user1、张三、admin等）
3. 点击"开始对话"进入聊天界面

## 使用指南

### 多用户使用

- 每个用户使用不同的用户ID登录
- 系统自动为每个用户创建独立会话
- 用户间的对话和任务执行完全隔离
- 支持同时处理多个用户的任务

### 任务类型

系统支持以下类型的任务：

1. **代码生成**
   - 示例：`"生成一个Python计算器程序,不允许追问"`
   - 功能：自动生成可运行的代码文件

2. **信息检索**
   - 示例：`"搜索最新的AI技术发展趋势,不允许追问"`
   - 功能：网络搜索并整理相关信息

3. **图像生成**
   - 示例：`"生成一张科技感十足的背景图片,不允许追问"`
   - 功能：AI绘图生成图像文件

4. **数据分析**
   - 示例：`"分析销售数据并生成图表,不允许追问"`
   - 功能：数据处理和可视化

5. **文档处理**
   - 示例：`"将PDF文档转换为Word格式"`
   - 功能：文档格式转换和处理

### 界面功能

#### 主页功能
- 用户ID输入和登录
- 系统状态监控
- 快速任务模板
- 功能特性展示

#### 聊天界面
- **左侧聊天区域**：
  - 实时消息显示
  - 支持文本、代码块格式
  - 快速任务按钮
  - 消息历史记录

- **右侧监控面板**：
  - 任务执行状态
  - 步骤进度显示
  - 实时日志输出
  - 生成文件列表

### WebSocket实时通信

系统使用WebSocket保持实时连接：
- 自动重连机制
- 心跳检测
- 连接状态显示
- 实时消息推送

### 会话管理

- 自动会话创建和管理
- 1小时不活跃自动清理
- 聊天历史持久化
- 任务状态跟踪

## API接口

### 主要端点

- `GET /` - 主页
- `GET /chat/{user_id}` - 聊天页面  
- `WebSocket /ws/{user_id}` - WebSocket连接
- `GET /api/users` - 活跃用户列表
- `GET /api/chat_history/{user_id}` - 聊天历史
- `POST /api/task/submit` - 提交任务
- `GET /api/task/status/{user_id}` - 任务状态

### WebSocket消息格式

**客户端发送：**
```json
{
    "type": "task_submit",
    "content": "用户任务内容"
}
```

**服务端推送：**
```json
{
    "type": "new_message",
    "message": {
        "sender": "assistant",
        "content": "AI回复内容",
        "timestamp": "2024-01-01T12:00:00",
        "message_type": "text"
    }
}
```

## 系统配置

### MCP服务器配置
- 端口：8001
- 协议：HTTP传输
- 调试模式：开启

### Web服务器配置  
- 端口：8000
- 主机：0.0.0.0
- 热重载：开启

### LLM配置
- 模型：Qwen-72B
- API地址：http://180.153.21.76:17009/v1
- 支持工具调用和结构化输出

## 文件结构

```
05.数字员工/
├── frontend/                 # 前端文件
│   ├── main.py              # FastAPI应用
│   ├── static/              # 静态资源
│   │   ├── css/style.css    # 样式文件
│   │   ├── js/              # JavaScript文件
│   │   └── assets/          # 图片等资源
│   └── templates/           # HTML模板
│       ├── index.html       # 主页模板
│       └── chat.html        # 聊天页面模板
├── execution_results/       # 执行结果存储
│   ├── reports/            # 执行报告
│   ├── raw_data/           # 原始数据
│   └── logs/               # 日志文件
├── generated_files/         # 生成的文件
├── manual.py               # 核心数据模型和TaskPlanner
├── task_executor.py        # 任务执行器
├── tool_manager.py         # 工具管理器
├── result_collector.py     # 结果收集器
├── mcp_server.py          # MCP服务器
├── mcp_client.py          # MCP客户端
├── tools.py               # 工具函数
├── start_system.py        # 系统启动脚本
└── README.md              # 本文档
```

## 开发说明

### 添加新工具

1. 在 `tools.py` 中定义工具函数
2. 在 `mcp_server.py` 中注册MCP工具
3. 重启MCP服务器使新工具生效

### 扩展功能

- **新的任务类型**：在TaskPlanner中添加任务分析逻辑
- **新的UI组件**：在templates和static中添加前端代码
- **新的API端点**：在frontend/main.py中添加路由

### 调试模式

启动时添加调试参数：
```bash
python frontend/main.py --debug
```

## 故障排除

### 常见问题

1. **WebSocket连接失败**
   - 检查端口8000是否被占用
   - 确认防火墙设置
   - 查看浏览器控制台错误信息

2. **MCP工具调用失败**
   - 确认MCP服务器（端口8001）正常运行
   - 检查网络连接
   - 查看后端日志错误信息

3. **任务执行失败**
   - 检查LLM API配置
   - 确认工具函数正常
   - 查看execution_results/logs中的日志

4. **文件生成失败**
   - 检查generated_files目录权限
   - 确认磁盘空间充足
   - 查看具体错误信息

### 日志查看

- **Web服务日志**：控制台输出
- **任务执行日志**：execution_results/logs/
- **MCP服务日志**：MCP服务器控制台

## 系统监控

### 实时监控

访问 http://localhost:8000/api/users 查看：
- 活跃用户数量
- 用户会话信息
- 系统运行状态

### 性能指标

- 任务执行时间
- WebSocket连接数
- 内存使用情况
- 生成文件统计

## 部署建议

### 生产环境

1. 使用进程管理器（如Supervisor）
2. 配置反向代理（如Nginx）
3. 启用HTTPS
4. 配置日志轮转
5. 设置监控告警

### 扩展性

- 支持Redis缓存用户会话
- 支持数据库持久化聊天历史
- 支持负载均衡多实例部署
- 支持Docker容器化部署

## 更新日志

### v1.0.0 (2024-06-04)
- ✅ 实现多用户会话管理
- ✅ 完成类Manus分屏界面
- ✅ 集成WebSocket实时通信
- ✅ 实现任务自动分解执行
- ✅ 添加结果收集和报告生成
- ✅ 支持8种MCP工具调用

## 技术支持

如有问题或建议，请查看：
1. 本README文档
2. 代码注释和文档字符串
3. 项目规划文档：`项目规划 - 类Manus AI系统开发.md`

---

**Manus AI System** - 让AI为您的工作赋能 🚀 