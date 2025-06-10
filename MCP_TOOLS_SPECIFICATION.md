# MCP工具规范化文档

## 概述

本文档描述了项目中MCP (Model Context Protocol) 工具的规范化改进，包括统一的格式标准、错误处理机制和调用规范。

## 主要改进

### 1. 统一返回格式

所有MCP工具现在都遵循统一的返回格式：

```json
{
    "success": true|false,
    "error": "错误信息（仅在失败时存在）",
    "data": "实际数据（成功时的结果）",
    "additional_fields": "具体工具的额外字段"
}
```

### 2. 完善的类型注解

所有工具函数都添加了完整的类型注解：

```python
from typing import Dict, Any, Optional, List

def tool_function(param: str, optional_param: Optional[str] = None) -> Dict[str, Any]:
    """
    工具函数描述
    
    Args:
        param: 参数描述
        optional_param: 可选参数描述
        
    Returns:
        返回值描述
    """
```

### 3. 标准化错误处理

所有工具都实现了统一的错误处理机制：

- 输入验证
- 网络请求异常处理
- JSON解析错误处理
- 通用异常捕获

## 工具列表

### 1. Web搜索工具 (`web_search_tool`)

**功能**: 使用searxng搜索网络信息

**参数**:
- `query` (str): 搜索关键词

**返回格式**:
```json
{
    "success": true,
    "data": {
        "query": "搜索词",
        "pages": [{"title": "标题", "url": "链接", "content": "内容"}],
        "pages_count": 10,
        "suggestions": ["建议1", "建议2"],
        "infoboxes": []
    }
}
```

### 2. 文件读取工具 (`read_file_tool`)

**功能**: 读取各种格式的文件

**支持格式**: txt, pdf, docx, xlsx, 图片等

**参数**:
- `file_path` (str): 文件路径

**返回格式**:
```json
{
    "success": true,
    "content": "文件内容",
    "file_path": "文件路径",
    "file_type": "文件类型"
}
```

### 3. 文件生成工具 (`file_generation_tool`)

**功能**: 根据提示词生成各种类型的文件

**参数**:
- `prompt` (str): 生成内容的提示词
- `file_type` (str): 文件类型，默认"txt"
- `file_name` (str): 文件名，默认自动生成
- `output_dir` (str): 输出目录

**返回格式**:
```json
{
    "success": true,
    "file_path": "生成的文件路径",
    "file_name": "文件名",
    "file_type": "文件类型",
    "file_size": 1024
}
```

### 4. 图片生成工具 (`image_generation_tool`)

**功能**: 根据文本描述生成图片

**参数**:
- `prompt` (str): 图片描述
- `negative_prompt` (str): 负面描述，可选
- `size` (str): 图片尺寸，默认"1024x1024"
- `n` (int): 生成数量，默认1

**返回格式**:
```json
{
    "success": true,
    "images": [{"url": "图片链接"}],
    "task_id": "任务ID"
}
```

### 5. 数据图表工具 (`data_chart_tool`)

**功能**: 根据数据生成图表

**参数**:
- `data_json` (str): JSON格式的数据
- `user_requirement` (str): 图表要求描述
- `file_path` (str): 图表保存路径

**返回格式**:
```json
{
    "success": true,
    "chart_path": "图表文件路径",
    "result": "生成结果",
    "data_shape": [10, 5]
}
```

### 6. AI回答工具 (`generate_answer_tool`)

**功能**: 使用AI模型回答问题

**参数**:
- `query` (str): 用户问题
- `temperature` (float): 回答随机性，默认0.5

**返回格式**:
```json
{
    "success": true,
    "answer": "AI的回答",
    "query": "原始问题"
}
```

### 7. 需求分析工具 (`rhetorical_reason_tool`)

**功能**: 分析用户问题并生成追问

**参数**:
- `user_query` (str): 用户问题

**返回格式**:
```json
{
    "success": true,
    "questions": "追问内容",
    "original_query": "原始问题"
}
```

## 使用示例

### 直接调用本地工具

```python
from tools.local_tools import web_search, file_generation

# 搜索网络信息
result = web_search("Python教程")
print(f"搜索成功: {result['success']}")

# 生成文件
file_result = file_generation(
    prompt="创建一个Hello World程序",
    file_type="py",
    file_name="hello_world"
)
print(f"文件生成成功: {file_result['success']}")
```

### 通过MCP客户端调用

```python
import asyncio
from communication.mcp_client import MultiMCPClient

async def main():
    async with MultiMCPClient() as client:
        # 调用web搜索工具
        result = await client.call_mcp_tool(
            "marix", 
            "web_search_tool", 
            {"query": "Python编程"}
        )
        print(f"搜索结果: {result}")

asyncio.run(main())
```

### 测试工具规范性

运行测试脚本验证所有工具是否符合规范：

```bash
python test_mcp_tools.py
```

## 错误处理标准

### 1. 输入验证错误

```json
{
    "success": false,
    "error": "参数不能为空"
}
```

### 2. 网络请求错误

```json
{
    "success": false,
    "error": "网络请求失败: 连接超时"
}
```

### 3. 文件操作错误

```json
{
    "success": false,
    "error": "文件不存在",
    "file_path": "/path/to/file"
}
```

### 4. API调用错误

```json
{
    "success": false,
    "error": "API响应格式错误",
    "task_id": "12345"
}
```

## 配置要求

### MCP配置文件 (`communication/mcp_config.json`)

```json
{
    "marix": {
        "url": "http://localhost:8001/mcp/",
        "transport": "streamable_http"
    },
    "fetch": {
        "command": "python",
        "args": ["-m", "mcp_server_fetch"],
        "transport": "stdio"
    }
}
```

### 依赖包要求

```text
langchain_mcp_adapters
pandas
requests
openai
mcp_server_fetch
```

## 最佳实践

1. **始终检查返回值的success字段**
2. **妥善处理错误情况**
3. **使用异步上下文管理器进行MCP客户端操作**
4. **为所有工具调用添加超时设置**
5. **记录详细的操作日志**

## 维护说明

- 所有新增工具必须遵循统一的格式规范
- 必须包含完整的类型注解和文档字符串
- 必须实现标准的错误处理机制
- 必须通过测试脚本验证

---

**更新日期**: 2024年12月
**版本**: 1.0.0 