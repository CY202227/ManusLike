import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mcp.server.fastmcp import FastMCP
from tools.local_tools import web_search, read_file, file_generation, image_generation, data_chart
from openai import OpenAI
import mcp_server_fetch


# 创建 FastMCP 服务器
mcp = FastMCP(
    "marix", 
    debug=True,
    log_level="DEBUG",
    host="0.0.0.0",
    port=8001,
)

# 注册所有工具到MCP服务器
@mcp.tool()
def web_search_tool(query: str) -> dict:
    """使用searxng搜索网络信息，获取最新资讯和相关页面"""
    return web_search(query)

@mcp.tool()
def read_file_tool(file_path: str) -> str:
    """读取各种类型的文件内容，支持txt、pdf、docx、xlsx、图片等格式"""
    return read_file(file_path)

@mcp.tool()
def file_generation_tool(prompt: str, file_type: str, file_name: str, output_dir: str = "./generated_files") -> dict:
    """根据提示词生成各种类型的文件，如txt、py、html、md、json等"""
    return file_generation(prompt, file_type, file_name, output_dir)

@mcp.tool()
def image_generation_tool(prompt: str, negative_prompt: str = "", size: str = "1024x1024", n: int = 1) -> dict:
    """根据文本描述生成图片，支持各种尺寸和风格"""
    return image_generation(prompt, negative_prompt, size, n)

@mcp.tool()
def data_chart_tool(data_description: str, chart_type: str = "bar") -> dict:
    """根据数据描述生成图表"""
    return data_chart(data_description, chart_type)

@mcp.tool()
def generate_answer_tool(query: str) -> str:
    """使用AI大模型回答用户问题，进行文本分析、总结、翻译、解释等"""
    client = OpenAI(api_key="sk-proj-1234567890", base_url="http://180.153.21.76:17009/v1")
    try:
        print(f"🤖 AI正在思考: {query[:50]}...")
        response = client.chat.completions.create(
            model="Qwen-72B",
            messages=[
                {"role": "system", "content": "你是一个有用的AI助手，请直接回答用户的问题。"}, 
                {"role": "user", "content": query}
            ],
            temperature=0.5,
            stream=True
        )
        
        # 处理流式响应
        full_response = ""
        for chunk in response:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                print(content, end="", flush=True)
                full_response += content
        print()  # 换行
        
        return full_response
    except Exception as e:
        return f"AI回答失败: {str(e)}"

@mcp.tool()
def rhetorical_reason(user_query: str) -> str:
    """如果用户问题需要追问，才可以更好的解决用户问题，则调用该工具"""
    REASON_SYSTEM_PROMPT = """
# 角色：

你是一名专业的规划专家，你很擅长洞悉用户需求。
你需要追问用户一些问题，方便后面你更好的为用户解决问题，制定解决方案。

# 任务：

1. 现在你需要根据用户问题，追问一些相关的问题，方便后面你更好的为用户解决问题，制定解决方案。
2. 追问的问题要契合用户原始问题，不要追问无关问题。
"""
    client = OpenAI(api_key="sk-proj-1234567890", base_url="http://180.153.21.76:17009/v1")
    
    print(f"🤔 分析用户需求: {user_query[:50]}...")
    response = client.chat.completions.create(
        model="Qwen-72B",
        messages=[
            {"role": "system", "content": REASON_SYSTEM_PROMPT}, 
            {"role": "user", "content": user_query}
        ],
        stream=True
    )
    
    # 处理流式响应
    full_response = ""
    for chunk in response:
        if chunk.choices[0].delta.content:
            content = chunk.choices[0].delta.content
            print(content, end="", flush=True)
            full_response += content
    print()  # 换行
    
    return full_response

if __name__ == "__main__":
    mcp.run(transport="streamable-http")


# sk-8c40f79ea2044d0cbb9f7056aa5ec298