import requests
import os
import time
from typing import Dict, Any, Optional, List
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
        try:
            response = requests.post(self.searxng_url, data=params)
            response.raise_for_status()
            data = response.json()
            pages = [{"title": page["title"], "url": page["url"], "content": page["content"]} for page in data.get("results", [])]
            suggestions = data.get("suggestions", [])
            infoboxes = data.get("infoboxes", [])
            return {"query": q, "pages": pages, "pages_count": len(pages), "suggestions": suggestions, "infoboxes": infoboxes}
        except Exception as e:
            return {"error": str(e)}
        


def web_search(query:str):
    """
    使用searxng搜索网络信息
    """
    searxng_search = SearxngSearch()
    result = searxng_search.searxng_search(query)
    return result


# url爬取

# def fetch_url(url:str):
#     pass


# 图片生成
def image_generation(prompt:str, negative_prompt: str = None, size:str = "1024x1024", n:int = 1):

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
            "prompt": prompt,
            "negative_prompt": negative_prompt,
        },
        "parameters":{
            "size": size,
            "n": n,
        }
    }
    try:
        response = requests.post(url, json=json_data, headers=headers)
        response.raise_for_status()
        data = response.json()
        task_id = data.get("output").get("task_id")
        while True:
            img_response = requests.get(image_url.format(task_id=task_id), headers=img_headers)
            img_data = img_response.json()
            if img_data.get("output").get("task_status") == "SUCCEEDED":
                return img_data.get("output").get("results")
            time.sleep(1)
    except Exception as e:
        return {"error": str(e)}
    


# 语音转文字

def speech_to_text(audio_file_path:str):
    try:
        url = "http://180.153.21.76:12119/custom_audio_to_text?spilit_time=3"
        response = requests.post(url, files={"file": open(audio_file_path, "rb")},stream=True)
        for chunk in response.iter_content(chunk_size=1024):

            json_data = json.loads(chunk.decode("utf-8"))
            result = json.dumps(
                {
                    "answer": json_data.get("text"),
                },
                ensure_ascii=False
            )
            yield result
    except Exception as e:
        return {"error": str(e)}


# 文字转语音

def text_to_speech(text:str):
    pass

# 文件读取

def read_file(file_path: str):
    """
    读取各种类型的文件内容
    支持的文件类型：
    - 文本文件：.txt, .md, .rst, .log, .csv, .py, .js, .html, .css, .java, .cpp, .c, .h, .php, .rb, .go, .rs, .ts, .jsx, .tsx, .vue, .xml, .ini, .cfg, .conf, .yml, .yaml
    - JSON文件：.json
    - PDF文件：.pdf
    - Word文档：.docx, .doc
    - Excel文件：.xlsx, .xls
    - 图片文件：.jpg, .jpeg, .png
    """
    read_file_function = ReadFileFunction(file_path)
    if not os.path.exists(file_path):
        return {"error": "文件不存在"}
    
    file_extension = file_path.lower().split('.')[-1]
    
    try:
        # 文本文件类型
        text_extensions = {
            'txt', 'md', 'rst', 'log', 'csv', 'py', 'js', 'html', 'css', 'java', 
            'cpp', 'c', 'h', 'php', 'rb', 'go', 'rs', 'ts', 'jsx', 'tsx', 'vue',
            'xml', 'ini', 'cfg', 'conf', 'sh', 'bat', 'ps1', 'sql', 'r', 'scala',
            'swift', 'kt', 'dart', 'pl', 'lua', 'tcl', 'vb', 'asm', 's'
        }
        
        if file_extension in text_extensions:
            return read_file_function.read_file(file_extension)
        # JSON文件
        elif file_extension == 'json':
            return read_file_function.read_json_file(file_extension)
        
        # YAML文件
        elif file_extension in ['yml', 'yaml']:
            return read_file_function.read_yaml_file(file_extension)
        # PDF文件
        elif file_extension == 'pdf':
            return read_file_function.read_pdf_file(file_extension)
        
        # Word文档
        elif file_extension in ['docx', 'doc']:
            return read_file_function.read_docx_file(file_extension)
        
        # Excel文件
        elif file_extension in ['xlsx', 'xls']:
            return read_file_function.read_xlsx_file(file_extension)

        # 图片文件
        elif file_extension in ['jpg', 'jpeg', 'png']:
            return read_file_function.read_image_file(file_extension)
        
        # 未知类型，以文本读取
        else:
            return read_file_function.read_file(file_extension)
    except Exception as e:
        return {"error": f"读取文件时发生错误: {str(e)}"}


# 数据图表绘制

def data_chart(data:DataFrame,user_requirement:str,file_path:str):
    generate_chart = Generate_chart(data,file_path)
    return generate_chart.generate_chart(user_requirement)

# 文件生成

def file_generation(prompt: str, file_type: str = "txt", file_name: str = "", output_dir = "D:\\Dev\\合作项目\\05.数字员工\\generated_files"):
    """
    根据提示词生成各种类型的文件
    
    参数:
    - prompt: 生成文件内容的提示词
    - file_type: 文件类型 (txt, py, js, html, css, md, json, xml, csv等)
    - file_name: 文件名，如果为None则自动生成
    - output_dir: 输出目录
    
    返回:
    - dict: 包含生成结果的字典
    """
    
    try:
        # 确保使用绝对路径，基于当前脚本所在目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 如果output_dir是相对路径，转换为基于脚本目录的绝对路径
        if not os.path.isabs(output_dir):
            if output_dir.startswith('./'):
                output_dir = output_dir[2:]  # 移除 './'
            output_dir = os.path.join(script_dir, output_dir)
        
        # 确保输出目录存在
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"创建目录: {output_dir}")
        
        # 自动生成文件名
        if file_name == "":
            timestamp = int(time.time())
            file_name = f"generated_{timestamp}"
        
        # 清理文件名，移除可能的路径分隔符
        file_name = file_name.replace('/', '_').replace('\\', '_')

        full_file_name = f"{file_name}"
        file_path = os.path.join(output_dir, full_file_name)
        
        print(f"准备生成文件: {file_path}")
        
        # 根据文件类型生成不同的内容
        content = Generate_file(prompt, file_type)
        
        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"文件生成成功: {file_path}")
        
        return {
            "success": True,
            "file_path": file_path,
            "file_name": full_file_name,
            "file_type": file_type,
            "file_size": len(content)
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