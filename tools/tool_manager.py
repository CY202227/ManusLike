#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ToolManager - 工具管理器（简化版）
统一从MCP服务器获取所有工具，提供简单的工具调用接口
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
import os
import json
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from communication.mcp_client import MultiMCPClient

# 配置日志
logger = logging.getLogger(__name__)

class ToolManager:
    """工具管理器 - 统一从MCP获取所有工具"""
    
    def __init__(self, mcp_client: MultiMCPClient):
        """
        初始化工具管理器
        
        Args:
            mcp_client: MCP客户端
        """
        self.mcp_client = mcp_client
        self.available_tools = []
        self._tools_loaded = False
        
        logger.info("ToolManager初始化完成")
    
    async def load_all_tools(self) -> None:
        """从MCP服务器加载所有可用工具"""
        if self._tools_loaded:
            return
            
        try:
            logger.info("正在从MCP服务器加载所有工具...")
            
            # 从MCP获取所有工具
            self.available_tools = await self.mcp_client.get_all_mcp_tools()
            
            self._tools_loaded = True
            logger.info(f"工具加载完成，共加载{len(self.available_tools)}个工具")
            
            # 打印工具清单
            self._log_available_tools()
            
        except Exception as e:
            logger.error(f"加载MCP工具时发生错误: {e}")
            raise
    
    def _log_available_tools(self):
        """记录可用工具清单"""
        logger.info("可用工具清单:")
        for tool in self.available_tools:
            logger.info(f"  • {tool.name}: {tool.description}")
    
    def get_available_tool_names(self) -> List[str]:
        """获取所有可用工具名称"""
        return [tool.name for tool in self.available_tools]
    
    def is_tool_available(self, tool_name: str) -> bool:
        """检查工具是否可用"""
        return any(tool.name == tool_name for tool in self.available_tools)
    
    def get_tool_info(self, tool_name: str) -> Optional[Any]:
        """获取指定工具的信息"""
        for tool in self.available_tools:
            if tool.name == tool_name:
                return tool
        return None
    
    def validate_tool_call(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证工具调用的合法性
        
        Args:
            tool_name: 工具名称
            args: 调用参数
            
        Returns:
            Dict: 验证结果，包含is_valid和error_message
        """
        if not self.is_tool_available(tool_name):
            return {
                "is_valid": False,
                "error_message": f"工具 '{tool_name}' 不存在或不可用",
                "available_tools": self.get_available_tool_names()
            }
        
        return {"is_valid": True}

    
    async def call_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        """
        统一工具调用接口
        
        Args:
            tool_name: 工具名称
            args: 调用参数
            
        Returns:
            Any: 工具执行结果
        """
        # 验证工具调用
        validation_result = self.validate_tool_call(tool_name, args)
        if not validation_result["is_valid"]:
                raise ValueError(f"工具调用验证失败: {validation_result['error_message']}")
        
        try:
            # 统一通过MCP调用工具
            result = await self.mcp_client.call_mcp_tool(
                mcp_name="marix",
                tool_name=tool_name,
                args=args
            )
            
            # 处理CallToolResult对象
            if hasattr(result, 'content'):
                if hasattr(result.content, 'text'):
                    # 尝试解析JSON格式的返回值
                    result_text = result.content.text
                    try:
                        # 如果是JSON格式，解析为字典返回
                        parsed_result = json.loads(result_text)
                        return parsed_result
                    except (json.JSONDecodeError, ValueError):
                        # 如果不是JSON格式，直接返回文本
                        return result_text
                elif isinstance(result.content, list) and len(result.content) > 0:
                    content_item = result.content[0]
                    if hasattr(content_item, 'text'):
                        # 同样尝试解析JSON
                        result_text = content_item.text
                        try:
                            parsed_result = json.loads(result_text)
                            return parsed_result
                        except (json.JSONDecodeError, ValueError):
                            return result_text
                    else:
                        return str(content_item)
                else:
                    return str(result.content)
            else:
                return result
                
        except Exception as e:
            logger.error(f"工具调用失败: {tool_name} - {str(e)}")
            raise
    
    def get_tools_for_planning(self) -> List[Dict[str, Any]]:
        """获取用于任务规划的工具信息"""
        tools_info = []
        for tool in self.available_tools:
            tools_info.append({
                "name": tool.name,
                "description": tool.description,
                "args": tool.args
            })
        return tools_info
    
    def generate_tool_constraint_prompt(self) -> str:
        """生成工具约束提示词"""
        available_tools = self.get_available_tool_names()
        return f"""
重要约束：你只能使用以下可用工具，不得创造或使用不存在的工具：

可用工具列表：
{', '.join(available_tools)}

如果任务需要的功能不在上述工具中，请选择最接近的工具或使用chatgpt_tool。
绝对不要使用列表之外的工具名称。
"""


# ========== 测试函数 ==========

async def test_tool_manager():
    """测试简化后的ToolManager功能"""
    
    # 创建ToolManager
    mcp_client = MultiMCPClient()
    tool_manager = ToolManager(mcp_client)
    
    # 加载工具
    await tool_manager.load_all_tools()
    
    print("=== 简化版工具管理器测试 ===")
    print(f"可用工具数量: {len(tool_manager.available_tools)}")
    print(f"可用工具名称: {tool_manager.get_available_tool_names()}")
    
    # 测试工具验证
    print("\n=== 工具验证测试 ===")
    
    # 测试有效工具
    valid_result = tool_manager.validate_tool_call("web_search_tool", {"query": "测试"})
    print(f"有效工具验证: {valid_result}")
    
    # 测试工具调用
    print("\n=== 工具调用测试 ===")
    try:
        # 测试搜索工具
        search_result = await tool_manager.call_tool("web_search_tool", {"query": "Python编程"})
        print(f"搜索结果: {str(search_result)[:200]}...")
        
        # 测试Generate answer工具
        chat_result = await tool_manager.call_tool("generate_answer_tool", {"query": "什么是Python？"})
        print(f"Generate answer结果: {chat_result[:100]}...")
        
        
    except Exception as e:
        print(f"工具调用测试失败: {e}")

if __name__ == "__main__":
    asyncio.run(test_tool_manager()) 