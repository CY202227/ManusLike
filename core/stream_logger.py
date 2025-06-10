"""
流式日志处理器
将系统日志信息实时流式传输到前端显示
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Optional, Callable, Any, Dict
from io import StringIO


class StreamLogHandler(logging.Handler):
    """流式日志处理器 - 将日志发送到WebSocket"""
    
    def __init__(self, websocket_callback: Optional[Callable] = None):
        super().__init__()
        self.websocket_callback = websocket_callback
        self.buffer = StringIO()
        
    def set_callback(self, callback: Callable):
        """设置WebSocket回调函数"""
        self.websocket_callback = callback
        
    def emit(self, record):
        """发射日志记录"""
        if self.websocket_callback:
            try:
                # 格式化日志消息
                formatted_message = self.format_log_message(record)
                
                # 异步发送到前端
                if asyncio.iscoroutinefunction(self.websocket_callback):
                    asyncio.create_task(self.websocket_callback({
                        "type": "log_stream",
                        "level": record.levelname,
                        "logger": record.name,
                        "message": formatted_message,
                        "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                        "module": record.module,
                        "function": record.funcName,
                        "line": record.lineno
                    }))
                else:
                    self.websocket_callback({
                        "type": "log_stream",
                        "level": record.levelname,
                        "logger": record.name,
                        "message": formatted_message,
                        "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                        "module": record.module,
                        "function": record.funcName,
                        "line": record.lineno
                    })
            except Exception as e:
                # 避免日志处理本身出错
                print(f"流式日志发送失败: {e}")
    
    def format_log_message(self, record) -> str:
        """格式化日志消息"""
        # 基础格式化
        message = record.getMessage()
        
        # 添加颜色和图标
        level_icons = {
            'DEBUG': '🔍',
            'INFO': 'ℹ️',
            'WARNING': '⚠️',
            'ERROR': '❌',
            'CRITICAL': '🚨'
        }
        
        icon = level_icons.get(record.levelname, '📝')
        
        # 格式化时间
        timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S.%f')[:-3]
        
        # 构建完整消息
        formatted = f"[{timestamp}] {icon} {record.name}:{record.lineno} - {message}"
        
        return formatted


class StreamLogger:
    """流式日志管理器"""
    
    def __init__(self):
        self.handlers = {}
        self.active_loggers = set()
        
    def create_stream_handler(self, user_id: str, websocket_callback: Callable) -> StreamLogHandler:
        """为用户创建流式日志处理器"""
        handler = StreamLogHandler(websocket_callback)
        handler.setLevel(logging.DEBUG)
        
        # 设置格式化器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        
        self.handlers[user_id] = handler
        return handler
    
    def attach_to_loggers(self, user_id: str, logger_names: list = None):
        """将流式处理器附加到指定的logger"""
        if user_id not in self.handlers:
            return
            
        handler = self.handlers[user_id]
        
        # 默认要监听的logger
        if logger_names is None:
            logger_names = [
                'core.task_planner',
                'core.task_executor', 
                'core.result_collector',
                'tools.tool_manager',
                'tools.local_tools',
                'communication.mcp_client',
                'communication.mcp_server',
                '__main__'
            ]
        
        for logger_name in logger_names:
            logger = logging.getLogger(logger_name)
            logger.addHandler(handler)
            self.active_loggers.add((user_id, logger_name))
    
    def detach_from_loggers(self, user_id: str):
        """从所有logger中移除用户的处理器"""
        if user_id not in self.handlers:
            return
            
        handler = self.handlers[user_id]
        
        # 移除处理器
        loggers_to_remove = [(uid, ln) for uid, ln in self.active_loggers if uid == user_id]
        for uid, logger_name in loggers_to_remove:
            logger = logging.getLogger(logger_name)
            logger.removeHandler(handler)
            self.active_loggers.discard((uid, logger_name))
        
        # 删除处理器
        del self.handlers[user_id]
    
    def get_handler(self, user_id: str) -> Optional[StreamLogHandler]:
        """获取用户的流式处理器"""
        return self.handlers.get(user_id)


# 全局流式日志管理器实例
stream_logger_manager = StreamLogger()


def create_user_log_stream(user_id: str, websocket_callback: Callable) -> StreamLogHandler:
    """为用户创建日志流"""
    handler = stream_logger_manager.create_stream_handler(user_id, websocket_callback)
    stream_logger_manager.attach_to_loggers(user_id)
    return handler


def remove_user_log_stream(user_id: str):
    """移除用户的日志流"""
    stream_logger_manager.detach_from_loggers(user_id)


def get_user_log_handler(user_id: str) -> Optional[StreamLogHandler]:
    """获取用户的日志处理器"""
    return stream_logger_manager.get_handler(user_id) 