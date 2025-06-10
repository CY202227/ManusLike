import requests
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import json
from pandas import DataFrame
from tools.functions.read_file_function import ReadFileFunction
from tools.functions.generate_file import Generate_file
from tools.functions.generate_chart import Generate_chart

# 网络检索
class SearxngSearch:
    def __init__(self) -> None:
        self.searxng_url = "http://47.100.251.249:8888/search"

    def searxng_search(self, q: str, 
               categories: Optional[List[str]] = None, 
               engines: Optional[str] = None, 
               language: str = "zh-CN",
               pageno: int = 1,
               time_range: Optional[str] = None,
               format: str = "json",
               **kwargs: Optional[Any]) -> Dict[str, Any]:
        params = {
            "q": q,
            "categories": categories,
            "engines": engines,
            "language": language,
            "pageno": pageno,
            "time_range": time_range,
            "format": format,
            **kwargs
        }
        # 移除None值参数
        params = {k: v for k, v in params.items() if v is not None}
        
        try:
            response = requests.post(self.searxng_url, data=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            pages = [
                {"title": page.get("title", ""), "url": page.get("url", ""), "content": page.get("content", "")} 
                for page in data.get("results", [])
            ]
            suggestions = data.get("suggestions", [])
            infoboxes = data.get("infoboxes", [])
            
            return {
                "query": q, 
                "pages": pages, 
                "pages_count": len(pages), 
                "suggestions": suggestions, 
                "infoboxes": infoboxes,
                "success": True
            }
        except requests.exceptions.RequestException as e:
            return {"error": f"网络请求失败: {str(e)}", "success": False}
        except json.JSONDecodeError as e:
            return {"error": f"JSON解析失败: {str(e)}", "success": False}
        except Exception as e:
            return {"error": str(e), "success": False}
        


def web_search(query: str) -> Dict[str, Any]:
    """
    使用searxng搜索网络信息
    
    Args:
        query: 搜索关键词
        
    Returns:
        搜索结果字典
    """
    if not query or not query.strip():
        return {"error": "搜索关键词不能为空", "success": False}
    
    searxng_search = SearxngSearch()
    result = searxng_search.searxng_search(query.strip())
    return result


def image_generation(prompt: str, negative_prompt: Optional[str] = None, size: str = "1024x1024", n: int = 1) -> Dict[str, Any]:
    """
    生成图片
    
    Args:
        prompt: 图片描述
        negative_prompt: 负面描述
        size: 图片尺寸
        n: 生成数量
        
    Returns:
        生成结果字典
    """
    if not prompt or not prompt.strip():
        return {"error": "图片描述不能为空", "success": False}

    url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis"
    image_url = "https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"

    headers = {
        "X-DashScope-Async": "enable",
        "Authorization": "Bearer sk-8c40f79ea2044d0cbb9f7056aa5ec298", 
        "Content-Type": "application/json"
    }
    img_headers = {
        "Authorization": "Bearer sk-8c40f79ea2044d0cbb9f7056aa5ec298", 
        "Content-Type": "application/json"
    }
    json_data = {
        "model": "wanx2.1-t2i-plus",
        "input": {
            "prompt": prompt.strip(),
            "negative_prompt": negative_prompt or "",
        },
        "parameters": {
            "size": size,
            "n": n,
        }
    }
    try:
        response = requests.post(url, json=json_data, headers=headers, timeout=60)
        response.raise_for_status()
        data = response.json()
        
        if "output" not in data or "task_id" not in data["output"]:
            return {"error": "API响应格式错误", "success": False}
            
        task_id = data["output"]["task_id"]
        
        # 轮询任务状态
        max_attempts = 60  # 最多等待60秒
        for attempt in range(max_attempts):
            img_response = requests.get(image_url.format(task_id=task_id), headers=img_headers, timeout=30)
            img_response.raise_for_status()
            img_data = img_response.json()
            
            if "output" not in img_data:
                return {"error": "任务状态查询响应格式错误", "success": False}
                
            task_status = img_data["output"].get("task_status")
            
            if task_status == "SUCCEEDED":
                return {
                    "success": True,
                    "results": img_data["output"].get("results", []),
                    "task_id": task_id
                }
            elif task_status == "FAILED":
                return {"error": "图片生成失败", "success": False, "task_id": task_id}
            
            time.sleep(1)
            
        return {"error": "图片生成超时", "success": False, "task_id": task_id}
        
    except requests.exceptions.RequestException as e:
        return {"error": f"网络请求失败: {str(e)}", "success": False}
    except json.JSONDecodeError as e:
        return {"error": f"JSON解析失败: {str(e)}", "success": False}
    except Exception as e:
        return {"error": str(e), "success": False}
    

def speech_to_text(audio_file_path: str):
    """
    语音转文字
    
    Args:
        audio_file_path: 音频文件路径
        
    Yields:
        转换结果
    """
    if not os.path.exists(audio_file_path):
        yield json.dumps({"error": "音频文件不存在", "success": False}, ensure_ascii=False)
        return
        
    try:
        url = "http://180.153.21.76:12119/custom_audio_to_text?spilit_time=3"
        with open(audio_file_path, "rb") as f:
            response = requests.post(url, files={"file": f}, stream=True, timeout=300)
            response.raise_for_status()
            
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                try:
                    json_data = json.loads(chunk.decode("utf-8"))
                    result = json.dumps({
                        "answer": json_data.get("text", ""),
                        "success": True
                    }, ensure_ascii=False)
                    yield result
                except json.JSONDecodeError:
                    continue
                        
    except requests.exceptions.RequestException as e:
        yield json.dumps({"error": f"网络请求失败: {str(e)}", "success": False}, ensure_ascii=False)
    except Exception as e:
        yield json.dumps({"error": str(e), "success": False}, ensure_ascii=False)


def read_file(file_path: str) -> Dict[str, Any]:
    """
    读取各种类型的文件内容
    支持的文件类型：
    - 文本文件：.txt, .md, .rst, .log, .csv, .py, .js, .html, .css, .java, .cpp, .c, .h, .php, .rb, .go, .rs, .ts, .jsx, .tsx, .vue, .xml, .ini, .cfg, .conf, .yml, .yaml
    - JSON文件：.json
    - PDF文件：.pdf
    - Word文档：.docx, .doc
    - Excel文件：.xlsx, .xls
    - 图片文件：.jpg, .jpeg, .png
    
    Args:
        file_path: 文件路径
        
    Returns:
        文件内容字典
    """
    if not file_path or not file_path.strip():
        return {"error": "文件路径不能为空", "success": False}
        
    file_path = file_path.strip()
    
    if not os.path.exists(file_path):
        return {"error": "文件不存在", "success": False, "file_path": file_path}
    
    try:
        read_file_function = ReadFileFunction(file_path)
        file_extension = file_path.lower().split('.')[-1]
        
        # 文本文件类型
        text_extensions = {
            'txt', 'md', 'rst', 'log', 'csv', 'py', 'js', 'html', 'css', 'java', 
            'cpp', 'c', 'h', 'php', 'rb', 'go', 'rs', 'ts', 'jsx', 'tsx', 'vue',
            'xml', 'ini', 'cfg', 'conf', 'sh', 'bat', 'ps1', 'sql', 'r', 'scala',
            'swift', 'kt', 'dart', 'pl', 'lua', 'tcl', 'vb', 'asm', 's'
        }
        
        if file_extension in text_extensions:
            content = read_file_function.read_file(file_extension)
        elif file_extension == 'json':
            content = read_file_function.read_json_file(file_extension)
        elif file_extension in ['yml', 'yaml']:
            content = read_file_function.read_yaml_file(file_extension)
        elif file_extension == 'pdf':
            content = read_file_function.read_pdf_file(file_extension)
        elif file_extension in ['docx', 'doc']:
            content = read_file_function.read_docx_file(file_extension)
        elif file_extension in ['xlsx', 'xls']:
            content = read_file_function.read_xlsx_file(file_extension)
        elif file_extension in ['jpg', 'jpeg', 'png']:
            content = read_file_function.read_image_file(file_extension)
        else:
            # 未知类型，以文本读取
            content = read_file_function.read_file(file_extension)
            
        return {
            "success": True,
            "content": content,
            "file_path": file_path,
            "file_type": file_extension
        }
        
    except Exception as e:
        return {"error": f"读取文件时发生错误: {str(e)}", "success": False, "file_path": file_path}


def data_chart(data: DataFrame, user_requirement: str, file_path: str) -> Dict[str, Any]:
    """
    数据图表绘制
    
    Args:
        data: 数据DataFrame
        user_requirement: 用户需求描述
        file_path: 保存路径
        
    Returns:
        图表生成结果
    """
    if data is None or data.empty:
        return {"error": "数据不能为空", "success": False}
        
    if not user_requirement or not user_requirement.strip():
        return {"error": "用户需求描述不能为空", "success": False}
        
    try:
        generate_chart = Generate_chart(data, file_path)
        result = generate_chart.generate_chart(user_requirement.strip())

        return {
            "success": True,
            "result": result,
            "file_path": file_path,
            "data_shape": data.shape
        }
    except Exception as e:
        return {"error": f"图表生成失败: {str(e)}", "success": False}


def file_generation(prompt: str, file_type: str = "txt", file_name: str = "", output_dir: str = "./generated_files") -> Dict[str, Any]:
    """
    根据提示词生成各种类型的文件
    
    参数:
    - prompt: 生成文件内容的提示词
    - file_type: 文件类型 (txt, py, js, html, css, md, json, xml, csv等)
    - file_name: 文件名，如果为空则自动生成
    - output_dir: 输出目录
    
    返回:
    - dict: 包含生成结果的字典
    """
    if not prompt or not prompt.strip():
        return {"success": False, "error": "提示词不能为空"}
    
    try:
        # 确保使用绝对路径，基于项目根目录
        project_root = Path(__file__).parent.parent
        
        # 如果output_dir是相对路径，转换为基于项目根目录的绝对路径
        if not os.path.isabs(output_dir):
            if output_dir.startswith('./'):
                output_dir = output_dir[2:]  # 移除 './'
            output_dir = str(project_root / output_dir)
        
        # 确保输出目录存在
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"创建目录: {output_dir}")
        
        # 自动生成文件名
        if not file_name or not file_name.strip():
            timestamp = int(time.time())
            file_name = f"generated_{timestamp}"
        
        # 清理文件名，移除可能的路径分隔符和扩展名
        file_name = file_name.strip().replace('/', '_').replace('\\', '_')
        if '.' in file_name and file_name.split('.')[-1].lower() == file_type.lower():
            # 如果文件名已包含正确的扩展名，则使用原文件名
            full_file_name = file_name
        else:
            # 否则添加扩展名
            full_file_name = f"{file_name}.{file_type}"
            
        file_path = os.path.join(output_dir, full_file_name)
        
        print(f"准备生成文件: {file_path}")
        
        # 根据文件类型生成不同的内容
        content = Generate_file(prompt.strip(), file_type)
        
        if not content:
            return {"success": False, "error": "生成的内容为空"}
        
        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"文件生成成功: {file_path}")
        
        return {
            "success": True,
            "file_path": file_path,
            "file_name": full_file_name,
            "file_type": file_type,
            "file_size": len(content),
            "output_dir": output_dir
        }
        
    except Exception as e:
        error_msg = f"生成文件时发生错误: {str(e)}"
        print(error_msg)
        return {
            "success": False,
            "error": error_msg
        }


if __name__ == "__main__":
    # print(image_generation("一个穿着红色衣服的女孩，站在海边，海浪拍打着沙滩，背景是蓝色的天空和白色的云朵"))
    # res = speech_to_text("/home/qichen/zh/data/daiyu.mp4")
    # for r in res:
    #     print(r)
    # res = read_file("C:\\Users\\CHENQIMING\\Desktop\\工作数据\\测试文件\\深入理解高并发编程（第1版）.pdf")
    # print(res)
    res = file_generation("生成一个简单的python程序，计算1到100的和", "py", "", "./generated_files")
    print(res)