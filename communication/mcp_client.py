from langchain_mcp_adapters.client import MultiServerMCPClient
import json
import asyncio
import os


class MultiMCPClient:

    def __init__(self, mcp_config_path: str = "D:\\Dev\\合作项目\\05.数字员工\\communication\\mcp_config.json"):
        with open(mcp_config_path, "r") as f:
            self.mcp_config = json.load(f)

    async def get_mcp_tools(self, mcp_name: str):
        client = MultiServerMCPClient(self.mcp_config)
        try:
            async with client.session(mcp_name) as session:
                res = await session.list_tools()
            return res
        finally:
            if hasattr(client, 'close'):
                await client.close()
    
    async def get_all_mcp_tools(self):
        client = MultiServerMCPClient(self.mcp_config)
        try:
            res = await client.get_tools()
            return res
        finally:
            if hasattr(client, 'close'):
                await client.close()

    async def call_mcp_tool(self, mcp_name: str, tool_name: str, args: dict):
        client = MultiServerMCPClient(self.mcp_config)
        try:
            async with client.session(mcp_name) as session:
                res = await session.call_tool(tool_name, args)
            return res
        finally:
            # 确保客户端被正确关闭
            if hasattr(client, 'close'):
                await client.close()

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
            # 获取所有工具（注释掉的代码示例）
            # res = await client.get_all_mcp_tools()
            # for r in res:
            #     print(r)
            
            # 调用工具
            test = await client.call_mcp_tool(
                "fetch", 
                "fetch", 
                {"url": "https://www.microsoft.com/en-us/research/articles/tsrformer/"}
            )
            print(test)
        except Exception as e:
            print(f"错误: {e}")


if __name__ == "__main__":
    asyncio.run(main())
