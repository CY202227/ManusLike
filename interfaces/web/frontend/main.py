"""
FastAPI Web应用 - 支持多用户的Manus AI系统前端
提供Web界面、WebSocket实时通信、多用户会话管理
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from contextlib import asynccontextmanager

# 导入现有组件
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# 正确导入项目模块
from core import TaskPlanner, TaskExecutor, FileManager
from core.models import TaskPlan, TaskStatus
from core.result_collector import ResultCollector
from tools.tool_manager import ToolManager
from communication.mcp_client import MultiMCPClient
from openai import OpenAI

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ========== 数据模型 ==========

class UserMessage(BaseModel):
    """用户消息模型"""
    content: str
    timestamp: datetime = None
    
    def __init__(self, **data):
        if 'timestamp' not in data:
            data['timestamp'] = datetime.now()
        super().__init__(**data)

class TaskRequest(BaseModel):
    """任务请求模型"""
    user_input: str
    user_id: str

class ChatMessage(BaseModel):
    """聊天消息模型"""
    sender: str  # 'user' or 'assistant' or 'system'
    content: str
    timestamp: datetime = None
    message_type: str = "text"  # 'text', 'task_start', 'task_progress', 'task_complete'
    task_id: Optional[str] = None
    
    def __init__(self, **data):
        if 'timestamp' not in data:
            data['timestamp'] = datetime.now()
        super().__init__(**data)

class UserSession:
    """用户会话类"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.session_id = str(uuid.uuid4())
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.chat_history: List[ChatMessage] = []
        self.current_task: Optional[TaskPlan] = None
        self.websocket: Optional[WebSocket] = None
        self.max_history_length = 1000  # 最大历史记录数量
        
    def add_message(self, message: ChatMessage):
        """添加聊天消息，自动管理历史记录长度"""
        self.chat_history.append(message)
        self.last_activity = datetime.now()
        
        # 管理历史记录长度，保留最新的消息
        if len(self.chat_history) > self.max_history_length:
            # 保留最新的80%消息，删除最旧的20%
            keep_count = int(self.max_history_length * 0.8)
            self.chat_history = self.chat_history[-keep_count:]
            logger.info(f"用户 {self.user_id} 历史记录已清理，保留最新 {keep_count} 条消息")
    
    def update_activity(self):
        """更新活动时间"""
        self.last_activity = datetime.now()
        
    def get_recent_history(self, limit: int = 50) -> List[ChatMessage]:
        """获取最近的历史记录"""
        return self.chat_history[-limit:] if len(self.chat_history) > limit else self.chat_history

# ========== 应用初始化 ==========

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化
    await initialize_components()
    yield
    # 关闭时清理（如果需要）

app = FastAPI(
    title="Manus AI System", 
    description="类Manus AI智能代理系统",
    lifespan=lifespan
)

# 静态文件和模板
frontend_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=str(frontend_dir / "static")), name="static")
templates = Jinja2Templates(directory=str(frontend_dir / "templates"))

# 全局组件
llm_client = None
tool_manager = None
task_planner = None
task_executor = None
result_collector = None
file_manager = None

# 用户会话管理
user_sessions: Dict[str, UserSession] = {}
active_connections: Dict[str, WebSocket] = {}

# ========== 初始化函数 ==========

async def initialize_components():
    """初始化系统组件"""
    global llm_client, tool_manager, task_planner, task_executor, result_collector, file_manager
    
    try:
        # 初始化LLM客户端
        llm_client = OpenAI(
            api_key="sk-proj-1234567890", 
            base_url="http://180.153.21.76:17009/v1"
        )
        
        # 初始化MCP客户端和工具管理器
        mcp_client = MultiMCPClient()
        tool_manager = ToolManager(mcp_client)
        await tool_manager.load_all_tools()
        
        # 初始化文件管理器
        file_manager = FileManager()
        
        # 初始化事件发射器
        from core.event_emitter import ExecutionEventEmitter
        from core.stream_logger import stream_logger_manager
        event_emitter = ExecutionEventEmitter()
        
        # 初始化任务规划器和执行器
        task_planner = TaskPlanner(llm_client, tool_manager, event_emitter=event_emitter)
        task_executor = TaskExecutor(tool_manager, file_manager, event_emitter)
        
        # 初始化结果收集器，传入file_manager
        result_collector = ResultCollector(file_manager=file_manager)
        
        logger.info("所有组件初始化完成")
        
    except Exception as e:
        logger.error(f"组件初始化失败: {e}")
        raise

# ========== 用户会话管理 ==========

def get_or_create_user_session(user_id: str) -> UserSession:
    """获取或创建用户会话"""
    if user_id not in user_sessions:
        user_sessions[user_id] = UserSession(user_id)
        logger.info(f"创建新用户会话: {user_id}")
    else:
        user_sessions[user_id].update_activity()
    
    return user_sessions[user_id]

def cleanup_inactive_sessions():
    """清理不活跃的会话"""
    current_time = datetime.now()
    inactive_sessions = []
    
    for user_id, session in user_sessions.items():
        # 超过1小时不活跃的会话
        if (current_time - session.last_activity).total_seconds() > 3600:
            inactive_sessions.append(user_id)
    
    for user_id in inactive_sessions:
        if user_id in user_sessions:
            del user_sessions[user_id]
        if user_id in active_connections:
            del active_connections[user_id]
        logger.info(f"清理不活跃会话: {user_id}")

# ========== WebSocket管理 ==========

class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """建立WebSocket连接"""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        
        # 更新用户会话
        session = get_or_create_user_session(user_id)
        session.websocket = websocket
        
        # 创建用户的流式日志处理器
        from core.stream_logger import create_user_log_stream
        
        async def log_callback(log_data):
            """日志回调函数"""
            try:
                await self.send_personal_message(log_data, user_id)
            except Exception as e:
                logger.error(f"发送日志到用户 {user_id} 失败: {e}")
        
        create_user_log_stream(user_id, log_callback)
        
        logger.info(f"用户 {user_id} 建立WebSocket连接")
    
    def disconnect(self, user_id: str):
        """断开WebSocket连接"""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        
        if user_id in user_sessions:
            user_sessions[user_id].websocket = None
        
        # 移除用户的流式日志处理器
        from core.stream_logger import remove_user_log_stream
        remove_user_log_stream(user_id)
        
        logger.info(f"用户 {user_id} 断开WebSocket连接")
    
    async def send_personal_message(self, message: dict, user_id: str):
        """发送个人消息"""
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_text(json.dumps(message, ensure_ascii=False, default=str))
            except Exception as e:
                logger.error(f"发送消息失败 {user_id}: {e}")
                self.disconnect(user_id)
    
    async def broadcast_to_user(self, message: dict, user_id: str):
        """向指定用户广播消息"""
        await self.send_personal_message(message, user_id)

manager = ConnectionManager()

# ========== 路由定义 ==========

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """主页"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/chat/{user_id}", response_class=HTMLResponse)
async def chat_page(request: Request, user_id: str):
    """聊天页面"""
    session = get_or_create_user_session(user_id)
    return templates.TemplateResponse("chat.html", {
        "request": request,
        "user_id": user_id,
        "session_id": session.session_id
    })

@app.get("/cyber/{user_id}", response_class=HTMLResponse)
async def cyber_chat_page(request: Request, user_id: str):
    """赛博朋克风格聊天页面"""
    session = get_or_create_user_session(user_id)
    return templates.TemplateResponse("chat_cyber.html", {
        "request": request,
        "user_id": user_id,
        "session_id": session.session_id
    })

@app.get("/monitor/{user_id}", response_class=HTMLResponse)
async def monitor_page(request: Request, user_id: str):
    """任务监控页面"""
    session = get_or_create_user_session(user_id)
    return templates.TemplateResponse("monitor.html", {
        "request": request,
        "user_id": user_id,
        "session_id": session.session_id
    })

# ========== API端点 ==========

@app.get("/api/users")
async def get_active_users():
    """获取活跃用户列表"""
    cleanup_inactive_sessions()
    return {
        "active_users": len(user_sessions),
        "users": [
            {
                "user_id": session.user_id,
                "session_id": session.session_id,
                "created_at": session.created_at,
                "last_activity": session.last_activity,
                "has_current_task": session.current_task is not None,
                "message_count": len(session.chat_history)
            }
            for session in user_sessions.values()
        ]
    }

@app.get("/api/download/{file_path:path}")
async def download_file(file_path: str):
    """文件下载端点"""
    try:
        logger.info(f"文件下载请求: {file_path}")
        
        # 检查文件路径是否为空
        if not file_path or file_path.strip() == "":
            logger.error("文件路径为空")
            raise HTTPException(status_code=400, detail="文件路径不能为空")
        
        # 清理文件路径，移除多余的前缀
        clean_file_path = file_path.replace('./generated_files', 'generated_files')
        clean_file_path = clean_file_path.replace('generated_files/', '')
        clean_file_path = clean_file_path.lstrip('./')
        
        # 如果文件名重复扩展名，修复它
        if clean_file_path.endswith('.py.py'):
            clean_file_path = clean_file_path[:-3]
        
        logger.info(f"清理后的文件路径: {clean_file_path}")
        
        # 再次检查清理后的路径是否有效
        if not clean_file_path or clean_file_path.strip() == "":
            logger.error("清理后的文件路径为空")
            raise HTTPException(status_code=400, detail="无效的文件路径")
        
        # 安全检查：确保文件路径在允许的目录内
        allowed_base_dirs = ["generated_files", "execution_results"]
        
        # 尝试多个可能的文件位置
        possible_paths = [
            Path("generated_files") / clean_file_path,
            Path("execution_results/reports") / clean_file_path,
            Path("execution_results/raw_data") / clean_file_path,
            Path(clean_file_path),  # 直接路径
            Path("generated_files") / Path(clean_file_path).name,  # 只使用文件名
        ]
        
        found_file_path = None
        for test_path in possible_paths:
            logger.info(f"测试路径: {test_path}")
            if test_path.exists() and test_path.is_file():  # 确保是文件而不是目录
                # 安全检查：确保文件在允许的目录中
                try:
                    resolved_path = test_path.resolve()
                    current_dir = Path.cwd().resolve()
                    
                    # 检查是否在允许的目录中
                    is_allowed = False
                    for base_dir in allowed_base_dirs:
                        allowed_dir = (current_dir / base_dir).resolve()
                        try:
                            resolved_path.relative_to(allowed_dir)
                            is_allowed = True
                            break
                        except ValueError:
                            continue
                    
                    if is_allowed:
                        found_file_path = test_path
                        break
                        
                except Exception as e:
                    logger.warning(f"路径安全检查失败: {e}")
                    continue
        
        if not found_file_path:
            logger.error(f"未找到文件或文件不在安全目录中: {file_path}")
            raise HTTPException(status_code=404, detail="文件不存在或无法访问")
        
        # 返回文件
        logger.info(f"返回文件: {found_file_path}")
        return FileResponse(
            path=str(found_file_path),
            filename=found_file_path.name,
            media_type='application/octet-stream'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件下载失败: {e}")
        raise HTTPException(status_code=500, detail=f"文件下载失败: {str(e)}")

@app.get("/api/download_by_task/{task_id}/{file_name}")
async def download_file_by_task(task_id: str, file_name: str):
    """通过任务ID和文件名下载文件"""
    try:
        logger.info(f"通过任务下载文件: task_id={task_id}, file_name={file_name}")
        
        # 从FileManager获取任务文件
        task_files = file_manager.get_task_files(task_id)
        
        # 查找匹配的文件
        found_file = None
        for file_info in task_files:
            if file_info["file_name"] == file_name:
                found_file = file_info
                break
        
        if not found_file:
            logger.error(f"任务 {task_id} 中未找到文件: {file_name}")
            raise HTTPException(status_code=404, detail="文件不存在")
        
        file_path = found_file["file_path"]
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 返回文件
        logger.info(f"返回文件: {file_path}")
        return FileResponse(
            path=file_path,
            filename=file_name,
            media_type='application/octet-stream'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"通过任务下载文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"下载失败: {str(e)}")

@app.get("/api/files/{user_id}")
async def get_user_files(user_id: str):
    """获取用户生成的文件列表"""
    try:
        session = get_or_create_user_session(user_id)
        
        # 从用户会话的当前任务或最近任务中获取文件
        files = []
        
        if session.current_task:
            # 获取当前任务的文件
            task_files = file_manager.get_task_files(session.current_task.task_id)
            for file_info in task_files:
                files.append({
                    "name": file_info["file_name"],
                    "path": file_info["file_path"],
                    "size": file_info["file_size"],
                    "type": file_info["file_type"],
                    "task_id": session.current_task.task_id,
                    "step_id": file_info.get("step_id"),
                    "description": file_info.get("description", ""),
                    "created_at": file_info.get("registered_at")
                })
        
        # 从聊天历史中查找已完成任务的文件
        for message in reversed(session.chat_history):
            if message.message_type == "task_complete" and hasattr(message, 'task_id'):
                # 如果消息包含task_id，获取该任务的文件
                task_files = file_manager.get_task_files(message.task_id)
                for file_info in task_files:
                    # 避免重复添加当前任务的文件
                    if not any(f["path"] == file_info["file_path"] for f in files):
                        files.append({
                            "name": file_info["file_name"],
                            "path": file_info["file_path"],
                            "size": file_info["file_size"],
                            "type": file_info["file_type"],
                            "task_id": message.task_id,
                            "step_id": file_info.get("step_id"),
                            "description": file_info.get("description", ""),
                            "created_at": file_info.get("registered_at")
                        })
        
        return {"files": files}
        
    except Exception as e:
        logger.error(f"获取用户文件失败: {e}")
        return {"files": []}

@app.get("/api/files/summary/{task_id}")
async def get_task_files_summary(task_id: str):
    """获取指定任务的文件摘要"""
    try:
        summary = file_manager.get_task_summary(task_id)
        return summary
    except Exception as e:
        logger.error(f"获取任务文件摘要失败: {e}")
        return {"error": str(e)}

@app.get("/api/files/download_package/{task_id}")
async def get_task_download_package(task_id: str, user_id: str = "default"):
    """获取任务文件下载包"""
    try:
        zip_path = file_manager.create_download_package(task_id, user_id)
        if zip_path and os.path.exists(zip_path):
            return FileResponse(
                zip_path,
                media_type='application/zip',
                filename=f"task_{task_id}_files.zip"
            )
        else:
            raise HTTPException(status_code=404, detail="下载包不存在或创建失败")
    except Exception as e:
        logger.error(f"创建下载包失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建下载包失败: {str(e)}")

@app.post("/api/files/cleanup/{task_id}")
async def cleanup_task_files(task_id: str, user_id: str = "default"):
    """清理指定任务的文件"""
    try:
        success = file_manager.cleanup_task_files(task_id, user_id)
        return {"success": success, "message": "文件清理完成" if success else "文件清理失败"}
    except Exception as e:
        logger.error(f"清理任务文件失败: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/chat_history/{user_id}")
async def get_chat_history(user_id: str, limit: int = 50, offset: int = 0):
    """获取用户聊天历史（支持分页）"""
    session = get_or_create_user_session(user_id)
    
    # 获取总消息数
    total_messages = len(session.chat_history)
    
    # 计算分页
    start_index = max(0, total_messages - offset - limit)
    end_index = total_messages - offset
    
    # 确保不越界
    if end_index <= 0:
        messages = []
    else:
        messages = session.chat_history[start_index:end_index]
    
    return {
        "user_id": user_id,
        "total_messages": total_messages,
        "offset": offset,
        "limit": limit,
        "messages": [
            {
                "sender": msg.sender,
                "content": msg.content,
                "timestamp": msg.timestamp,
                "message_type": msg.message_type
            }
            for msg in messages
        ]
    }

@app.post("/api/task/submit")
async def submit_task(task_request: TaskRequest):
    """提交任务请求"""
    try:
        session = get_or_create_user_session(task_request.user_id)
        
        # 添加用户消息到聊天历史
        user_message = ChatMessage(
            sender="user",
            content=task_request.user_input,
            message_type="text"
        )
        session.add_message(user_message)
        
        # 向用户发送任务开始通知
        await manager.send_personal_message({
            "type": "task_start",
            "message": "正在分析您的任务..."
        }, task_request.user_id)
        
        # 异步执行任务
        asyncio.create_task(execute_task_for_user(task_request.user_id, task_request.user_input))
        
        return {"status": "success", "message": "任务已提交，正在处理..."}
        
    except Exception as e:
        logger.error(f"提交任务失败: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/api/task/status/{user_id}")
async def get_task_status(user_id: str):
    """获取用户当前任务状态"""
    session = get_or_create_user_session(user_id)
    
    if not session.current_task:
        return {"status": "no_task", "message": "当前没有执行中的任务"}
    
    # 获取任务执行状态
    execution_status = task_executor.get_execution_status()
    
    return {
        "status": "running" if session.current_task.status == TaskStatus.EXECUTING else session.current_task.status.value,
        "task_id": session.current_task.task_id,
        "task_type": session.current_task.task_type,
        "complexity_level": session.current_task.complexity_level,
        "execution_status": execution_status
    }

# ========== WebSocket端点 ==========

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket连接端点"""
    await manager.connect(websocket, user_id)
    
    try:
        # 发送欢迎消息
        await manager.send_personal_message({
            "type": "system",
            "message": f"欢迎使用Manus AI系统！用户ID: {user_id}"
        }, user_id)
        
        # 发送聊天历史
        session = get_or_create_user_session(user_id)
        if session.chat_history:
            # 只发送最近的50条消息，避免一次性发送过多历史记录
            recent_messages = session.get_recent_history(50)
            await manager.send_personal_message({
                "type": "chat_history",
                "total_messages": len(session.chat_history),
                "showing_recent": len(recent_messages),
                "messages": [
                    {
                        "sender": msg.sender,
                        "content": msg.content,
                        "timestamp": msg.timestamp.isoformat(),
                        "message_type": msg.message_type
                    }
                    for msg in recent_messages
                ]
            }, user_id)
        
        # 保持连接
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # 处理不同类型的消息
            if message_data.get("type") == "ping":
                await manager.send_personal_message({"type": "pong"}, user_id)
            elif message_data.get("type") == "task_submit":
                # 通过WebSocket提交任务
                user_input = message_data.get("content", "")
                if user_input.strip():
                    await submit_task_via_websocket(user_id, user_input)
            
    except WebSocketDisconnect:
        manager.disconnect(user_id)
    except Exception as e:
        logger.error(f"WebSocket错误 {user_id}: {e}")
        manager.disconnect(user_id)

# ========== 任务执行函数 ==========

async def submit_task_via_websocket(user_id: str, user_input: str):
    """通过WebSocket提交任务"""
    try:
        session = get_or_create_user_session(user_id)
        
        # 添加用户消息到历史记录
        user_message = ChatMessage(
            sender="user",
            content=user_input,
            message_type="text"
        )
        session.add_message(user_message)
        
        # 广播用户消息到前端（确保前端能看到用户输入）
        await manager.send_personal_message({
            "type": "new_message",
            "message": {
                "sender": "user",
                "content": user_input,
                "timestamp": user_message.timestamp.isoformat(),
                "message_type": "text"
            }
        }, user_id)
        
        # 执行任务
        await execute_task_for_user(user_id, user_input)
        
    except Exception as e:
        logger.error(f"WebSocket任务提交失败: {e}")
        await manager.send_personal_message({
            "type": "error",
            "message": f"任务提交失败: {str(e)}"
        }, user_id)

async def execute_task_for_user(user_id: str, user_input: str):
    """为用户执行任务"""
    session = get_or_create_user_session(user_id)
    
    # 创建流式输出回调函数
    async def stream_output_callback(message: str):
        """将流式输出发送到前端"""
        try:
            await manager.send_personal_message({
                "type": "stream_output",
                "message": message,
                "timestamp": datetime.now().isoformat()
            }, user_id)
        except Exception as e:
            logger.error(f"发送流式输出失败: {e}")
    
    # 创建任务特定的事件监听器
    async def task_event_listener(event):
        """任务事件监听器，将事件转发给前端"""
        try:
            # 根据事件类型格式化消息
            event_type = event.get("type")
            data = event.get("data", {})
            message = data.get("message", "")
            
            # 发送详细进度到前端
            await manager.send_personal_message({
                "type": "detailed_progress",
                "event_type": event_type,
                "stage": data.get("stage", event_type),
                "message": message,
                "data": data,
                "timestamp": event.get("timestamp")
            }, user_id)
            
            # 特殊处理工具调用完成事件，检查是否有图表结果
            if event_type == "tool_call_complete":
                result = data.get("result", {})
                tool_name = data.get("tool_name", "")
                
                # 检查是否是图表生成工具的结果
                if tool_name == "data_chart_tool" and isinstance(result, dict):
                    if result.get("type") == "chart" and result.get("success", False):
                        # 发送图表HTML内容到前端
                        html_content = result.get("html_content", "")
                        if html_content:
                            await manager.send_personal_message({
                                "type": "stream_output",
                                "message": html_content,
                                "timestamp": datetime.now().isoformat()
                            }, user_id)
                    elif isinstance(result, str) and (result.strip().startswith('<!DOCTYPE html>') or result.strip().startswith('<html')):
                        # 处理旧格式的HTML返回
                        await manager.send_personal_message({
                            "type": "stream_output",
                            "message": result,
                            "timestamp": datetime.now().isoformat()
                        }, user_id)
            
            # 特殊处理一些重要事件，发送额外的UI更新
            if event_type == "task_analysis_start":
                await manager.send_personal_message({
                    "type": "task_progress",
                    "message": "开始分析任务需求...",
                    "stage": "analyzing"
                }, user_id)
            
            elif event_type == "task_type_detected":
                await manager.send_personal_message({
                    "type": "task_progress", 
                    "message": f"检测到任务类型: {data.get('task_type')}",
                    "stage": "analyzing"
                }, user_id)
                
            elif event_type == "clarity_score":
                score = data.get('score', 0) * 100
                needs_clarification = data.get('needs_clarification', False)
                if needs_clarification:
                    await manager.send_personal_message({
                        "type": "task_progress",
                        "message": f"任务明确度: {score:.0f}% (需要澄清)",
                        "stage": "analyzing"
                    }, user_id)
                else:
                    await manager.send_personal_message({
                        "type": "task_progress",
                        "message": f"任务明确度: {score:.0f}% (足够明确)",
                        "stage": "analyzing"
                    }, user_id)
            
            elif event_type == "plan_generation_start":
                await manager.send_personal_message({
                    "type": "task_progress",
                    "message": "开始生成执行计划...",
                    "stage": "planning"
                }, user_id)
            
            elif event_type == "plan_step_generated":
                step_index = data.get('step_index', 0)
                total_steps = data.get('total_steps', 0)
                step_desc = data.get('step_description', '')
                await manager.send_personal_message({
                    "type": "task_progress",
                    "message": f"生成步骤 {step_index + 1}/{total_steps}: {step_desc}",
                    "stage": "planning"
                }, user_id)
            
            elif event_type == "plan_generated":
                total_steps = data.get('total_steps', 0)
                await manager.send_personal_message({
                    "type": "task_progress",
                    "message": f"执行计划生成完成，共 {total_steps} 个步骤",
                    "stage": "planning"
                }, user_id)
                
            elif event_type == "task_start":
                await manager.send_personal_message({
                    "type": "task_progress",
                    "message": "开始执行任务...",
                    "stage": "executing"
                }, user_id)
            
            elif event_type == "step_start":
                step_desc = data.get('description', '')
                tool_name = data.get('tool_name', '')
                await manager.send_personal_message({
                    "type": "task_progress",
                    "message": f"执行步骤: {step_desc} (工具: {tool_name})",
                    "stage": "executing"
                }, user_id)
            
            elif event_type == "step_complete":
                status = data.get('status', 'unknown')
                status_text = "完成" if status == "completed" else "失败"
                await manager.send_personal_message({
                    "type": "task_progress",
                    "message": f"步骤执行{status_text}",
                    "stage": "executing"
                }, user_id)
            
            elif event_type == "result_collection_start":
                await manager.send_personal_message({
                    "type": "task_progress",
                    "message": "开始收集执行结果...",
                    "stage": "collecting"
                }, user_id)
            
            elif event_type == "report_generation_start":
                formats = data.get('formats', [])
                await manager.send_personal_message({
                    "type": "task_progress",
                    "message": f"开始生成执行报告 ({', '.join(formats)} 格式)...",
                    "stage": "collecting"
                }, user_id)
            
            elif event_type == "report_saved":
                format_type = data.get('format', '')
                await manager.send_personal_message({
                    "type": "task_progress",
                    "message": f"保存 {format_type.upper()} 报告完成",
                    "stage": "collecting"
                }, user_id)
                
        except Exception as e:
            logger.error(f"事件监听器错误: {e}")
    
    try:
        # 设置流式输出回调
        if task_planner:
            task_planner.set_stream_callback(stream_output_callback)
        
        # 清除之前的事件监听器（避免重复注册）
        if task_planner and hasattr(task_planner, 'event_emitter') and task_planner.event_emitter:
            # 清除之前的监听器
            task_planner.event_emitter.listeners = []
            task_planner.event_emitter.add_listener(task_event_listener)
        
        if task_executor and hasattr(task_executor, 'event_emitter') and task_executor.event_emitter:
            # 清除之前的监听器 
            task_executor.event_emitter.listeners = []
            task_executor.event_emitter.add_listener(task_event_listener)
        
        # 任务分析阶段
        await manager.send_personal_message({
            "type": "task_progress",
            "message": "正在分析任务需求...",
            "stage": "analyzing"
        }, user_id)
        
        task_plan = await task_planner.analyze_task(user_input)
        session.current_task = task_plan
        
        # 检查是否需要澄清
        if task_plan.requires_clarification:
            clarification_message = "需要您澄清以下问题：\n" + "\n".join([f"• {q}" for q in task_plan.clarification_questions])
            
            assistant_message = ChatMessage(
                sender="assistant",
                content=clarification_message,
                message_type="clarification"
            )
            session.add_message(assistant_message)
            
            await manager.send_personal_message({
                "type": "new_message",
                "message": {
                    "sender": "assistant",
                    "content": clarification_message,
                    "timestamp": assistant_message.timestamp.isoformat(),
                    "message_type": "clarification"
                }
            }, user_id)
            
            return
        
        # 任务规划完成
        plan_message = f"任务分析完成！\n类型：{task_plan.task_type}\n复杂度：{task_plan.complexity_level}\n步骤数：{len(task_plan.plan.steps)}"
        
        assistant_message = ChatMessage(
            sender="assistant",
            content=plan_message,
            message_type="task_plan"
        )
        session.add_message(assistant_message)
        
        await manager.send_personal_message({
            "type": "new_message",
            "message": {
                "sender": "assistant",
                "content": plan_message,
                "timestamp": assistant_message.timestamp.isoformat(),
                "message_type": "task_plan"
            }
        }, user_id)
        
        # 执行阶段
        await manager.send_personal_message({
            "type": "task_progress",
            "message": "开始执行任务...",
            "stage": "executing"
        }, user_id)
        
        execution_result = await task_executor.execute_plan(task_plan, user_id)
        
        # 检查是否为对话类型，如果是则直接处理回复
        if getattr(task_plan, 'is_conversation', False):
            logger.info("💬 对话类型任务，直接发送回复")
            
            # 从执行结果中获取对话回复
            if execution_result.success and execution_result.results:
                for result in execution_result.results:
                    if result.get("function_name") == "chat_response":
                        response_content = result.get("result", {}).get("response", "")
                        
                        # 创建对话回复消息
                        assistant_message = ChatMessage(
                            sender="assistant",
                            content=response_content,
                            message_type="conversation"
                        )
                        session.add_message(assistant_message)
                        
                        # 发送对话回复
                        await manager.send_personal_message({
                            "type": "new_message",
                            "message": {
                                "sender": "assistant",
                                "content": response_content,
                                "timestamp": assistant_message.timestamp.isoformat(),
                                "message_type": "conversation"
                            }
                        }, user_id)
                        
                        # 清除当前任务并返回，不生成报告
                        session.current_task = None
                        return
        
        # 收集结果阶段（仅针对真正的任务）
        await manager.send_personal_message({
            "type": "task_progress",
            "message": "收集执行结果...",
            "stage": "collecting"
        }, user_id)
        
        # 发射结果收集开始事件
        if result_collector and hasattr(result_collector, 'file_manager') and result_collector.file_manager:
            if hasattr(result_collector.file_manager, 'event_emitter'):
                result_collector.file_manager.event_emitter = task_executor.event_emitter
        
        report = await result_collector.collect_and_format_result(execution_result, task_plan)
        
        # 保存报告，传递file_manager参数 
        await manager.send_personal_message({
            "type": "task_progress",
            "message": "生成执行报告...",
            "stage": "collecting"
        }, user_id)
        
        # 发射报告生成事件
        if task_executor and hasattr(task_executor, 'event_emitter'):
            await task_executor.event_emitter.emit_report_generation_start(['json', 'markdown'])
        
        saved_files = await result_collector.save_report(report, ['json'], file_manager)
        
        # 获取任务文件摘要
        task_files_summary = file_manager.get_task_summary(task_plan.task_id)
        
        # 生成结果消息
        if execution_result.success:
            result_message = f"✅ 任务执行成功！\n"
            result_message += f"执行时间：{execution_result.execution_time:.2f}秒\n"
            
            # 显示FileManager管理的文件
            if task_files_summary.get("file_count", 0) > 0:
                result_message += f"生成文件：{task_files_summary['file_count']}个\n"
                for file_info in task_files_summary.get("files", []):
                    result_message += f"• {file_info['name']} ({file_info['type']}, {file_info['size']} bytes)\n"
                result_message += f"\n📁 下载包：/api/files/download_package/{task_plan.task_id}?user_id={user_id}\n"
            elif execution_result.files_generated:
                # 备用：显示执行结果中的文件
                result_message += f"生成文件：{len(execution_result.files_generated)}个\n"
                for file_path in execution_result.files_generated:
                    result_message += f"• {file_path}\n"
            
            if saved_files:
                result_message += f"\n📋 执行报告已保存：\n"
                for format_type, file_path in saved_files.items():
                    result_message += f"• {format_type}: {file_path}\n"
        else:
            result_message = f"❌ 任务执行失败\n"
            if execution_result.error_message:
                result_message += f"错误信息：{execution_result.error_message}\n"
        
        # 添加结果消息，包含task_id
        result_assistant_message = ChatMessage(
            sender="assistant",
            content=result_message,
            message_type="task_complete"
        )
        # 添加task_id属性到消息对象
        result_assistant_message.task_id = task_plan.task_id
        session.add_message(result_assistant_message)
        
        await manager.send_personal_message({
            "type": "new_message",
            "message": {
                "sender": "assistant",
                "content": result_message,
                "timestamp": result_assistant_message.timestamp.isoformat(),
                "message_type": "task_complete",
                "task_id": task_plan.task_id
            }
        }, user_id)
        
        # 任务完成通知
        await manager.send_personal_message({
            "type": "task_complete",
            "success": execution_result.success,
            "execution_time": execution_result.execution_time,
            "files_generated": execution_result.files_generated,
            "task_id": task_plan.task_id,
            "files_summary": task_files_summary
        }, user_id)
        
        # 如果任务成功完成，设置为最后完成的任务以便检测改进请求
        if execution_result.success and task_planner:
            # 将生成的文件信息添加到task_plan中
            task_plan.generated_files = execution_result.files_generated
            task_planner.set_last_completed_task(task_plan)
            logger.info(f"✅ 已设置最后完成的任务: {task_plan.task_id}")
        
        # 清除当前任务
        session.current_task = None
        
    except Exception as e:
        logger.error(f"执行任务失败: {e}")
        
        # 发送错误消息
        error_message = f"❌ 任务执行失败\n错误信息：{str(e)}"
        
        assistant_message = ChatMessage(
            sender="assistant",
            content=error_message,
            message_type="error"
        )
        session.add_message(assistant_message)
        
        await manager.send_personal_message({
            "type": "new_message",
            "message": {
                "sender": "assistant",
                "content": error_message,
                "timestamp": assistant_message.timestamp.isoformat(),
                "message_type": "error"
            }
        }, user_id)
        
        await manager.send_personal_message({
            "type": "error",
            "message": str(e)
        }, user_id)
        
        import traceback
        logger.error(traceback.format_exc())
    
    finally:
        # 清理流式输出回调和事件监听器
        if task_planner:
            task_planner.set_stream_callback(None)
            if hasattr(task_planner, 'event_emitter') and task_planner.event_emitter:
                task_planner.event_emitter.listeners = []
        
        if task_executor:
            if hasattr(task_executor, 'event_emitter') and task_executor.event_emitter:
                task_executor.event_emitter.listeners = []

# ========== 运行应用 ==========

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False) 