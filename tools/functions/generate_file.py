from openai import OpenAI
import os
import time
from dotenv import load_dotenv
from pathlib import Path

# 加载根目录的.env文件
root_dir = Path(__file__).parent.parent.parent  # 获取项目根目录
env_path = root_dir / '.env'
load_dotenv(dotenv_path=env_path)


def Generate_file(prompt: str, file_type: str = "txt"):
    """
    兼容原有调用方式的函数
    """
    generator = Generate_file_Class(prompt, file_type)
    return generator.generate_file()


class Generate_file_Class:
    def __init__(self, prompt: str, file_type: str = "txt"):
        self.prompt = prompt
        self.file_type = file_type
        self.client = OpenAI(api_key=os.getenv("DEFAULT_API_KEY"), base_url=os.getenv("DEFAULT_BASE_URL"))

    def generate_file(self):
        """
        使用AI模型生成文件内容
        """
        try:
            system_prompt = self._get_system_prompt()
            
            print(f"📝 正在生成 {self.file_type} 文件内容...")
            response = self.client.chat.completions.create(
                model=os.getenv("DEFAULT_MODEL_NAME"),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": self.prompt}
                ],
                temperature=0.7,
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
            return f"生成文件内容时发生错误: {str(e)}"

    def _get_system_prompt(self):
        """
        根据文件类型获取相应的系统提示词
        """
        prompts = {
            "py": """你是一个专业的Python开发工程师。请根据用户的需求生成完整的Python代码。
                        要求：
                        1. 代码结构清晰，包含必要的注释
                        2. 添加适当的错误处理
                        3. 遵循PEP8编码规范
                        4. 包含main函数和必要的导入语句
                        5. **直接输出可执行 Python 代码**：代码中不要包含任何注释，必须保证正确,不要放在代码块中```python ```。
                    """,

            "js": """你是一个专业的JavaScript开发工程师。请根据用户的需求生成完整的JavaScript代码。
要求：
1. 代码结构清晰，包含必要的注释
2. 使用现代JavaScript语法（ES6+）
3. 添加适当的错误处理
4. 代码可以直接在浏览器或Node.js中运行
5. 代码可以直接运行,不需要任何解释,不要放在代码块中```js ```""",

            "html": """你是一个专业的前端开发工程师。请根据用户的需求生成完整的HTML页面。
要求：
1. 使用HTML5标准
2. 包含完整的head和body结构
3. 添加适当的CSS样式
4. 响应式设计
5. 语义化的HTML标签
6. 代码可以直接运行,不需要任何解释,不要放在代码块中```html ```""",

            "css": """你是一个专业的CSS开发工程师。请根据用户的需求生成完整的CSS样式表。
要求：
1. 使用现代CSS特性
2. 包含响应式设计
3. 代码结构清晰，有适当的注释
4. 遵循CSS最佳实践
5. 不需要任何解释,不要放在代码块中```css ```""",

            "md": """你是一个技术文档写作专家。请根据用户的需求生成完整的Markdown文档。
要求：
1. 使用标准Markdown语法
2. 结构清晰，包含目录
3. 内容详尽且有逻辑性
4. 适当使用代码块、表格、列表等元素
5. 不需要任何解释,也不要放在代码块中""",

            "json": """你是一个数据结构专家。请根据用户的需求生成合法的JSON数据。
要求：
1. JSON格式正确，可以被解析
2. 数据结构合理
3. 包含示例数据
4. 字段命名清晰
5. 不需要任何解释,不要放在代码块中```json ```""",

            "xml": """你是一个数据结构专家。请根据用户的需求生成合法的XML文档。
要求：
1. XML格式正确，包含声明
2. 标签结构合理
3. 包含示例数据
4. 使用适当的属性和元素
5. 不需要任何解释,不要放在代码块中```xml ```""",

            "csv": """你是一个数据分析专家。请根据用户的需求生成CSV格式的数据文件。
要求：
1. 包含表头
2. 数据格式正确
3. 字段分隔符使用逗号
4. 包含示例数据
5. 不需要任何解释,不要放在代码块中```csv ```""",

            "sql": """你是一个数据库专家。请根据用户的需求生成SQL脚本。
要求：
1. SQL语法正确
2. 包含创建表、插入数据、查询等操作
3. 添加适当的注释
4. 考虑数据完整性约束
5. 代码可以直接运行,不需要任何解释,不要放在代码块中```sql ```""",

            "txt": """你是一个专业的内容创作者。请根据用户的需求生成文本内容。
要求：
1. 内容结构清晰
2. 语言表达准确
3. 符合用户的具体需求
4. 内容完整且有价值
5. 不需要任何解释,不要放在代码块中```txt ```""",
        }
        
        return prompts.get(self.file_type, prompts["txt"])