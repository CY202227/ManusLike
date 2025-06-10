import re
from openai import OpenAI  
import sys
import os
from pandas import DataFrame
from pathlib import Path
from tools.functions.prompts.chart_prompt import prompt
# 设置默认编码
sys.stdout.reconfigure(encoding='utf-8')

class Generate_chart:
    def __init__(self, data:DataFrame, file_path:str):
        self.data = data
        self.file_path = file_path
        self.client = OpenAI(api_key=os.getenv("DEFAULT_API_KEY"), base_url=os.getenv("DEFAULT_BASE_URL"))
        self.data_columns = self.data.columns.tolist()
        self.data_type = self.data.dtypes.tolist()
        self.data_all = self.data.to_dict(orient='records')  # 获取所有数据

    def generate_chart(self,user_requirement:str):
 
        message_prompt = prompt.format(
            data_columns=self.data_columns, 
            data_type=self.data_type, 
            data_all=self.data_all, 
            file_path=self.file_path,
            user_requirement=user_requirement
        )

        # 构造请求信息  
        messages = [  
            {"role": "system", "content": "You are a helpful assistant.\n Based on the dataset user provided, do not assume.\n Think step by step, \nUse Markdown to format the output."},  
            {"role": "user", "content": message_prompt},
        ]  

        max_retries = 10
        retry_count = 0
        last_error = None

        while retry_count < max_retries:
            try:
                if last_error:
                    # 如果存在上一次的错误，将其添加到消息中
                    error_message = f"上一次尝试执行生成的代码时发生了以下错误，请修正并重新生成代码：\n{last_error}"
                    current_messages = messages + [{"role": "user", "content": error_message}]
                else:
                    current_messages = messages

                response = self.client.chat.completions.create(  
                    model= os.getenv("DEFAULT_MODEL_NAME"),  
                    messages=current_messages,
                    stream=False
                )  
                
                response_code = response.choices[0].message.content  
                code_blocks = re.findall(r'```(.*?)```', response_code, re.DOTALL)  
                cleaned_code_blocks = [code.replace("python\n","") for code in code_blocks]  
                print(f"尝试次数: {retry_count + 1}")
                print(cleaned_code_blocks)
                # 创建一个字典来存储执行结果
                local_vars = {}
                all_blocks_succeeded = True
                for code in cleaned_code_blocks:  
                    try:
                        # 执行代码并捕获结果
                        exec(code, globals(), local_vars)
                        # 如果代码生成了图表，处理图表保存和返回
                        if 'fig' in local_vars:
                            # 获取图表HTML内容
                            html_content = local_vars['fig'].to_html(full_html=True, include_plotlyjs=True)
                            # 获取图表JSON数据
                            chart_data = local_vars['fig'].to_json()
                            
                            # 生成保存路径
                            chart_filename = f"chart_{int(__import__('time').time())}.html"
                            chart_path = os.path.join(os.path.dirname(self.file_path), chart_filename)
                            
                            # 保存HTML文件
                            with open(chart_path, 'w', encoding='utf-8') as f:
                                f.write(html_content)
                            
                            print(f"📊 图表已保存到: {chart_path}")
                            
                            # 保留show()方法用于本地预览
                            local_vars['fig'].show()
                            
                            # 返回包含文件路径和HTML内容的结果
                            return {
                                "type": "chart",
                                "success": True,
                                "html_content": html_content,
                                "chart_data": chart_data,
                                "file_path": chart_path,
                                "file_name": chart_filename,
                                "file_type": "html",
                                "message": f"图表生成成功！已保存为: {chart_filename}"
                            }
                    except Exception as e:
                        print(f"执行代码块时出错: {e}")
                        last_error = f"代码块 \n```python\n{code}\n```\n 执行失败，错误信息: {e}" # 更新错误信息
                        all_blocks_succeeded = False
                        break # 单个代码块执行失败，跳出内层循环，触发重试
                
                if all_blocks_succeeded:
                    if 'fig' not in local_vars and cleaned_code_blocks: # 检查所有代码块执行后是否生成了图表
                        last_error = "所有代码块执行完毕，但没有生成图表 'fig'。"
                        all_blocks_succeeded = False # 标记为失败以触发重试

                if all_blocks_succeeded:
                    break # 所有代码块成功执行，跳出重试循环
                else:
                    retry_count += 1
                    if retry_count < max_retries:
                        messages.append({"role": "user", "content": "请重新生成代码,上一次的错误为：" + last_error})
                        print(f"准备重试 ({retry_count}/{max_retries})...")
                    else:
                        print("已达到最大重试次数，执行失败。")
                        return {
                            "type": "chart",
                            "success": False,
                            "error": f"已达到最大重试次数。最后一次错误: {last_error}",
                            "message": "图表生成失败"
                        }

            except Exception as e: # 这里捕获API调用或其他外部错误
                print(f"API 调用或代码执行时出错: {e}")
                last_error = str(e) # 保存错误信息
                retry_count += 1
                if retry_count < max_retries:
                    print(f"准备重试 ({retry_count}/{max_retries})...")
                else:
                    print("已达到最大重试次数，API调用或外部执行失败。")
                    return {
                        "type": "chart", 
                        "success": False,
                        "error": f"API调用失败: {str(e)}",
                        "message": "图表生成失败"
                    }