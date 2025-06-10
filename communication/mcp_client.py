from langchain_mcp_adapters.client import MultiServerMCPClient
import json
import asyncio
import os
from typing import Dict, Any, List, Optional
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MultiMCPClient:
    """
    多服务器MCP客户端
    支持连接多个MCP服务器并调用相应的工具
    """

    def __init__(self, mcp_config_path: str = "communication/mcp_config.json"):
        """
        初始化MCP客户端
        
        Args:
            mcp_config_path: MCP配置文件路径
        """
        if not os.path.exists(mcp_config_path):
            raise FileNotFoundError(f"MCP配置文件不存在: {mcp_config_path}")
            
        try:
            with open(mcp_config_path, "r", encoding='utf-8') as f:
                self.mcp_config = json.load(f)
                logger.info(f"成功加载MCP配置: {list(self.mcp_config.keys())}")
        except json.JSONDecodeError as e:
            raise ValueError(f"MCP配置文件格式错误: {e}")
        except Exception as e:
            raise Exception(f"读取MCP配置文件失败: {e}")

    async def get_mcp_tools(self, mcp_name: str) -> List[Any]:
        """
        获取指定MCP服务器的工具列表
        
        Args:
            mcp_name: MCP服务器名称
            
        Returns:
            工具列表
        """
        if mcp_name not in self.mcp_config:
            raise ValueError(f"MCP服务器 '{mcp_name}' 不存在于配置中")
            
        client = MultiServerMCPClient(self.mcp_config)
        try:
            async with client.session(mcp_name) as session:
                res = await session.list_tools()
                logger.info(f"获取到 {mcp_name} 的 {len(res)} 个工具")
                return res
        except Exception as e:
            logger.error(f"获取 {mcp_name} 工具列表失败: {e}")
            raise
        finally:
            if hasattr(client, 'close'):
                await client.close()
    
    async def get_all_mcp_tools(self) -> List[Any]:
        """
        获取所有MCP服务器的工具列表
        
        Returns:
            所有工具的列表
        """
        client = MultiServerMCPClient(self.mcp_config)
        try:
            res = await client.get_tools()
            logger.info(f"获取到全部 {len(res)} 个工具")
            return res
        except Exception as e:
            logger.error(f"获取所有工具列表失败: {e}")
            raise
        finally:
            if hasattr(client, 'close'):
                await client.close()

    async def call_mcp_tool(self, mcp_name: str, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用指定MCP服务器的工具
        
        Args:
            mcp_name: MCP服务器名称
            tool_name: 工具名称
            args: 工具参数
            
        Returns:
            工具执行结果
        """
        if mcp_name not in self.mcp_config:
            return {
                "success": False,
                "error": f"MCP服务器 '{mcp_name}' 不存在于配置中",
                "available_servers": list(self.mcp_config.keys())
            }
            
        if not isinstance(args, dict):
            return {
                "success": False,
                "error": "工具参数必须是字典格式",
                "provided_args_type": type(args).__name__
            }
            
        client = MultiServerMCPClient(self.mcp_config)
        try:
            logger.info(f"调用工具: {mcp_name}.{tool_name} 参数: {args}")
            
            async with client.session(mcp_name) as session:
                res = await session.call_tool(tool_name, args)
                
                # 确保返回标准格式
                if isinstance(res, dict):
                    if "success" not in res:
                        res["success"] = True
                    return res
                else:
                    return {
                        "success": True,
                        "result": res,
                        "tool_name": tool_name,
                        "mcp_name": mcp_name
                    }
                    
        except Exception as e:
            error_msg = f"调用 {mcp_name}.{tool_name} 失败: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "tool_name": tool_name,
                "mcp_name": mcp_name,
                "args": args
            }
        finally:
            # 确保客户端被正确关闭
            if hasattr(client, 'close'):
                await client.close()

    async def list_servers(self) -> Dict[str, Any]:
        """
        列出所有配置的MCP服务器
        
        Returns:
            服务器信息字典
        """
        servers_info = {}
        for server_name, config in self.mcp_config.items():
            servers_info[server_name] = {
                "config": config,
                "status": "未知"
            }
            
            try:
                # 尝试获取工具列表来验证服务器状态
                tools = await self.get_mcp_tools(server_name)
                servers_info[server_name]["status"] = "在线"
                servers_info[server_name]["tools_count"] = len(tools)
            except Exception as e:
                servers_info[server_name]["status"] = f"离线: {str(e)}"
                servers_info[server_name]["tools_count"] = 0
                
        return {
            "success": True,
            "servers": servers_info,
            "total_servers": len(servers_info)
        }

    async def __aenter__(self):
        """支持异步上下文管理器"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出时清理资源"""
        pass


async def main():
    """主函数，演示正确的使用方式"""
    async with MultiMCPClient() as client:
        try:
            # 列出所有服务器
            servers = await client.list_servers()
            print("🖥️ MCP服务器状态:")
            print(json.dumps(servers, ensure_ascii=False, indent=2))
            
            # 获取所有工具（注释掉的代码示例）
            # res = await client.get_all_mcp_tools()
            # for r in res:
            #     print(r)
            
            # 调用工具示例
            if "fetch" in client.mcp_config:
                print("\n🌐 测试fetch工具:")
                test = await client.call_mcp_tool(
                    "fetch", 
                    "fetch", 
                    {"url": "https://www.microsoft.com/en-us/research/articles/tsrformer/"}
                )
                print(json.dumps(test, ensure_ascii=False, indent=2))
                
        except Exception as e:
            print(f"❌ 错误: {e}")


if __name__ == "__main__":
    asyncio.run(main())
