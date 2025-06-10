import sys
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import json
import time

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mcp.server.fastmcp import FastMCP
from tools.local_tools import web_search, read_file, file_generation, image_generation, data_chart
from openai import OpenAI
import pandas as pd

# 统一路径处理函数
def resolve_project_path(relative_path: str) -> str:
    """
    将相对路径转换为基于项目根目录的绝对路径
    
    Args:
        relative_path: 相对路径，可以以./开头或直接是目录名
        
    Returns:
        绝对路径字符串
    """
    if os.path.isabs(relative_path):
        return relative_path
    
    # 规范化路径分隔符，将反斜杠统一为正斜杠
    relative_path = relative_path.replace('\\', '/')
    
    # 移除./前缀
    if relative_path.startswith('./'):
        relative_path = relative_path[2:]
    
    # 基于项目根目录构建绝对路径
    return str(project_root / relative_path)

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
def web_search_tool(query: str) -> Dict[str, Any]:
    """
    使用searxng搜索网络信息，获取最新资讯和相关页面
    
    Args:
        query: 搜索关键词或问题
        
    Returns:
        包含搜索结果的字典，包含pages、suggestions等信息
    """
    try:
        result = web_search(query)
        if isinstance(result, dict) and "error" in result:
            return {"success": False, "error": result["error"], "results": []}
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e), "results": []}

@mcp.tool()
def read_file_tool(file_path: str) -> Dict[str, Any]:
    """
    读取各种类型的文件内容，支持txt、pdf、docx、xlsx、图片等格式
    
    Args:
        file_path: 文件路径（绝对路径或相对路径）
        
    Returns:
        包含文件内容的字典
    """
    try:
        result = read_file(file_path)
        if isinstance(result, dict) and "error" in result:
            return {"success": False, "error": result["error"], "content": ""}
        return {"success": True, "content": result, "file_path": file_path}
    except Exception as e:
        return {"success": False, "error": f"读取文件失败: {str(e)}", "content": ""}

@mcp.tool()
def file_generation_tool(
    prompt: str, 
    file_type: str = "txt", 
    file_name: str = "", 
    output_dir: str = "generated_files"
) -> Dict[str, Any]:
    """
    根据提示词生成各种类型的文件
    
    Args:
        prompt: 生成文件内容的提示词
        file_type: 文件类型（如txt、py、html、md、json等）
        file_name: 文件名，如果为空则自动生成
        output_dir: 输出目录路径
        
    Returns:
        包含生成结果的字典
    """
    try:
        # 统一路径处理
        resolved_output_dir = resolve_project_path(output_dir)
        result = file_generation(prompt, file_type, file_name, resolved_output_dir)
        return result
    except Exception as e:
        return {"success": False, "error": f"文件生成失败: {str(e)}"}

@mcp.tool()
def image_generation_tool(
    prompt: str, 
    negative_prompt: str = "", 
    size: str = "1024x1024", 
    n: int = 1
) -> Dict[str, Any]:
    """
    根据文本描述生成图片
    
    Args:
        prompt: 图片描述提示词
        negative_prompt: 负面提示词（可选）
        size: 图片尺寸（如1024x1024、512x512等）
        n: 生成图片数量
        
    Returns:
        包含生成图片信息的字典
    """
    try:
        result = image_generation(prompt, negative_prompt, size, n)
        if isinstance(result, dict) and "error" in result:
            return {"success": False, "error": result["error"], "images": []}
        return {"success": True, "images": result}
    except Exception as e:
        return {"success": False, "error": f"图片生成失败: {str(e)}", "images": []}

@mcp.tool()
def data_chart_tool(
    data_source: str, 
    user_requirement: str, 
    file_path: str = "charts/chart_output.png"
) -> Dict[str, Any]:
    """
    根据数据生成图表
    
    Args:
        data_source: 数据源，可以是JSON格式的数据字符串、CSV/Excel文件路径、JSON文件路径，或前一步工具调用的结果
        user_requirement: 用户对图表的要求描述
        file_path: 图表保存路径
        
    Returns:
        包含图表生成结果的字典
    """
    try:
        df = None
        actual_data_source = data_source
        
        print(f"🔍 接收到的data_source类型: {type(data_source)}")
        print(f"🔍 data_source内容预览: {str(data_source)[:300]}...")
        
        # 智能解析数据源
        # 1. 如果是复杂的嵌套结构，尝试提取文件路径
        if isinstance(data_source, str):
            # 尝试解析为JSON（可能是前一步的工具调用结果）
            try:
                parsed_source = json.loads(data_source)
                
                # 从工具调用结果中提取文件路径
                if isinstance(parsed_source, dict):
                    # 检查常见的文件路径字段
                    file_path_candidates = [
                        parsed_source.get("file_path"),
                        parsed_source.get("data", {}).get("file_path") if isinstance(parsed_source.get("data"), dict) else None,
                        parsed_source.get("result", {}).get("file_path") if isinstance(parsed_source.get("result"), dict) else None,
                        # 处理嵌套的MCP工具调用结果格式
                        parsed_source.get("result", {}).get("content", [{}])[0].get("text") if 
                            isinstance(parsed_source.get("result", {}).get("content"), list) and 
                            len(parsed_source.get("result", {}).get("content", [])) > 0 else None
                    ]
                    
                    for candidate in file_path_candidates:
                        if candidate:
                            # 如果候选项是字符串且包含file_path信息，进一步解析
                            if isinstance(candidate, str) and "file_path" in candidate:
                                try:
                                    nested_data = json.loads(candidate)
                                    if isinstance(nested_data, dict) and "file_path" in nested_data:
                                        actual_data_source = nested_data["file_path"]
                                        print(f"✅ 从嵌套结果中提取文件路径: {actual_data_source}")
                                        break
                                except json.JSONDecodeError:
                                    continue
                            elif isinstance(candidate, str) and os.path.exists(candidate):
                                actual_data_source = candidate
                                print(f"✅ 直接提取文件路径: {actual_data_source}")
                                break
                    
                    # 如果没有找到文件路径，但有直接的数据，使用数据
                    if actual_data_source == data_source and not os.path.exists(actual_data_source):
                        if isinstance(parsed_source, (list, dict)):
                            print("📊 使用解析后的JSON数据直接创建DataFrame")
                            df = pd.DataFrame(parsed_source)
                        
            except json.JSONDecodeError:
                print("⚠️ 不是有效的JSON，尝试作为文件路径处理")
        
        # 2. 如果找到了文件路径，读取文件
        if df is None and actual_data_source != data_source:
            print(f"📁 尝试读取文件: {actual_data_source}")
            
        if df is None:
            # 检查是否是文件路径
            if os.path.exists(actual_data_source):
                file_ext = os.path.splitext(actual_data_source)[1].lower()
                print(f"📄 检测到文件扩展名: {file_ext}")
                
                if file_ext == '.json':
                    with open(actual_data_source, 'r', encoding='utf-8') as f:
                        data_dict = json.load(f)
                    df = pd.DataFrame(data_dict)
                    print(f"✅ 成功从JSON文件读取数据，形状: {df.shape}")
                    
                elif file_ext == '.csv':
                    df = pd.read_csv(actual_data_source, encoding='utf-8')
                    print(f"✅ 成功从CSV文件读取数据，形状: {df.shape}")
                    
                elif file_ext in ['.xlsx', '.xls']:
                    df = pd.read_excel(actual_data_source)
                    print(f"✅ 成功从Excel文件读取数据，形状: {df.shape}")
                    
                else:
                    return {"success": False, "error": f"不支持的文件格式: {file_ext}"}
                    
            else:
                # 最后尝试：直接作为JSON字符串解析
                try:
                    data_dict = json.loads(actual_data_source)
                    df = pd.DataFrame(data_dict)
                    print(f"✅ 成功从JSON字符串创建数据，形状: {df.shape}")
                except json.JSONDecodeError as e:
                    return {
                        "success": False, 
                        "error": f"无法解析数据源。\n原始数据源: {data_source[:200]}...\n解析后数据源: {actual_data_source[:200]}...\nJSON错误: {str(e)}"
                    }
        
        # 验证DataFrame
        if df is None or df.empty:
            return {"success": False, "error": "数据为空或无法解析"}
        
        # 显示数据信息用于调试
        print(f"📊 最终数据形状: {df.shape}")
        print(f"📊 数据列: {list(df.columns)}")
        print(f"📊 数据预览:\n{df.head()}")
        
        # 统一路径处理
        resolved_file_path = resolve_project_path(file_path)
        
        # 调用图表生成函数
        result = data_chart(df, user_requirement, resolved_file_path)
        
        # 确保返回格式一致
        if isinstance(result, dict) and result.get("success", False):
            return {
                "success": True, 
                "chart_path": resolved_file_path, 
                "result": result,
                "data_info": {
                    "shape": df.shape,
                    "columns": list(df.columns),
                    "source_type": "file" if os.path.exists(actual_data_source) else "direct_data"
                }
            }
        else:
            return result
            
    except FileNotFoundError:
        return {"success": False, "error": f"文件不存在: {actual_data_source}"}
    except pd.errors.EmptyDataError:
        return {"success": False, "error": "文件为空或格式错误"}
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"JSON数据格式错误: {str(e)}"}
    except Exception as e:
        error_msg = f"图表生成失败: {str(e)}"
        print(f"❌ 错误详情: {error_msg}")
        import traceback
        print(f"🔍 错误堆栈: {traceback.format_exc()}")
        return {"success": False, "error": error_msg}

# 为了向后兼容，保留原来的data_chart_tool
@mcp.tool()
def data_chart_tool_legacy(
    data_json: str, 
    user_requirement: str, 
    file_path: str = "charts/chart_output.png"
) -> Dict[str, Any]:
    """
    根据JSON数据生成图表（遗留版本，建议使用data_chart_tool）
    
    Args:
        data_json: JSON格式的数据字符串
        user_requirement: 用户对图表的要求描述
        file_path: 图表保存路径
        
    Returns:
        包含图表生成结果的字典
    """
    return data_chart_tool(data_json, user_requirement, file_path)

@mcp.tool()
def smart_chart_tool(
    file_generation_result: str,
    user_requirement: str,
    chart_output_dir: str = "charts"
) -> Dict[str, Any]:
    """
    智能图表生成工具 - 从文件生成结果中自动提取数据文件路径并生成图表
    
    Args:
        file_generation_result: 文件生成工具的结果（JSON字符串）
        user_requirement: 用户对图表的要求描述
        chart_output_dir: 图表输出目录
        
    Returns:
        包含图表生成结果的字典
    """
    try:
        # 解析文件生成结果
        if isinstance(file_generation_result, str):
            try:
                file_result = json.loads(file_generation_result)
            except json.JSONDecodeError:
                file_result = {"file_path": file_generation_result}  # 假设直接传递了文件路径
        else:
            file_result = file_generation_result
        
        # 提取文件路径
        data_file_path = None
        if isinstance(file_result, dict):
            data_file_path = file_result.get("file_path") or file_result.get("data", {}).get("file_path")
        
        if not data_file_path:
            return {"success": False, "error": "无法从文件生成结果中提取文件路径"}
        
        if not os.path.exists(data_file_path):
            return {"success": False, "error": f"数据文件不存在: {data_file_path}"}
        
        # 统一路径处理
        resolved_chart_output_dir = resolve_project_path(chart_output_dir)
        
        # 生成图表输出路径
        os.makedirs(resolved_chart_output_dir, exist_ok=True)
        chart_filename = f"chart_{int(time.time())}.html"
        chart_path = os.path.join(resolved_chart_output_dir, chart_filename)
        
        # 调用data_chart_tool
        result = data_chart_tool(data_file_path, user_requirement, chart_path)
        
        return result
        
    except Exception as e:
        return {"success": False, "error": f"智能图表生成失败: {str(e)}"}

@mcp.tool()
def generate_answer_tool(query: str, temperature: float = 0.5) -> Dict[str, Any]:
    """
    使用AI大模型回答用户问题，进行文本分析、总结、翻译、解释等
    
    Args:
        query: 用户问题或需要处理的文本
        temperature: 回答的随机性（0-1，越高越随机）
        
    Returns:
        包含AI回答的字典
    """
    client = OpenAI(api_key="sk-proj-1234567890", base_url="http://180.153.21.76:17009/v1")
    try:
        print(f"🤖 AI正在思考: {query[:50]}...")
        response = client.chat.completions.create(
            model="Qwen-72B",
            messages=[
                {"role": "system", "content": "你是一个有用的AI助手，请直接回答用户的问题。"}, 
                {"role": "user", "content": query}
            ],
            temperature=temperature,
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
        
        return {"success": True, "answer": full_response, "query": query}
    except Exception as e:
        return {"success": False, "error": f"AI回答失败: {str(e)}", "answer": ""}

@mcp.tool()
def rhetorical_reason_tool(user_query: str) -> Dict[str, Any]:
    """
    分析用户问题并生成相关的追问，以便更好地理解用户需求
    
    Args:
        user_query: 用户的原始问题
        
    Returns:
        包含追问建议的字典
    """
    REASON_SYSTEM_PROMPT = """
# 角色：

你是一名专业的规划专家，你很擅长洞悉用户需求。
你需要追问用户一些问题，方便后面你更好的为用户解决问题，制定解决方案。

# 任务：

1. 现在你需要根据用户问题，追问一些相关的问题，方便后面你更好的为用户解决问题，制定解决方案。
2. 追问的问题要契合用户原始问题，不要追问无关问题。
3. 请以JSON格式返回追问的问题列表。
"""
    
    client = OpenAI(api_key="sk-proj-1234567890", base_url="http://180.153.21.76:17009/v1")
    
    try:
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
    
        return {"success": True, "questions": full_response, "original_query": user_query}
    except Exception as e:
        return {"success": False, "error": f"分析失败: {str(e)}", "questions": ""}

if __name__ == "__main__":
    mcp.run(transport="streamable-http")


# sk-8c40f79ea2044d0cbb9f7056aa5ec298