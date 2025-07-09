import streamlit as st
import os
import json
import tempfile
import pandas as pd
from typing import Optional, List
from dotenv import load_dotenv
from llm_sandbox import SandboxSession
from openai import OpenAI
from logger import log_model_request, log_model_response, log_tool_result

# 加载环境变量
load_dotenv()

# 初始化 OpenAI 客户端
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_API_BASE")
)

# 设置页面配置
st.set_page_config(
    page_title="Excel数据分析助手",
    page_icon="📊",
    layout="wide"
)

# 页面标题
st.title("Excel数据分析助手")
st.markdown("上传Excel文件并使用自然语言描述您的分析需求，AI将为您生成并执行分析代码。")

# 定义函数
def run_code(lang: str, code: str, libraries: Optional[List] = None) -> str:
    """
    在沙盒环境中运行代码
    """
    with SandboxSession(lang=lang, verbose=False, keep_template=True) as session:
        result = session.run(code, libraries).text
        if not result or result.strip() == '':
            return "执行成功，但没有输出结果。请尝试添加print语句来显示结果。"
        return result

def copy_file_to_sandbox(local_path: str, sandbox_path: str) -> str:
    """
    将本地文件复制到沙盒环境中
    """
    try:
        with SandboxSession(lang="python", keep_template=True) as session:
            session.copy_to_runtime(local_path, sandbox_path)
        return f"文件已成功复制到沙盒: {local_path} -> {sandbox_path}"
    except Exception as e:
        return f"复制文件失败: {str(e)}"

def copy_file_from_sandbox(sandbox_path: str, local_path: str) -> str:
    """
    从沙盒环境复制文件到本地
    """
    try:
        with SandboxSession(lang="python", keep_template=True) as session:
            session.copy_from_runtime(sandbox_path, local_path)
        return f"文件已成功从沙盒复制: {sandbox_path} -> {local_path}"
    except Exception as e:
        return f"复制文件失败: {str(e)}"

def run_agent(user_input: str, excel_file_path: Optional[str] = None):
    """
    使用 OpenAI SDK 调用大模型并执行工具调用
    """
    # 定义工具
    tools = [
        {
            "type": "function",
            "function": {
                "name": "run_code",
                "description": "Run code in a sandboxed environment.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lang": {
                            "type": "string",
                            "description": "The language of the code. Must be one of ['python', 'java', 'javascript', 'cpp', 'go', 'ruby']"
                        },
                        "code": {
                            "type": "string",
                            "description": "The code to run."
                        },
                        "libraries": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            },
                            "description": "The libraries to use, it is optional."
                        }
                    },
                    "required": ["lang", "code"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "copy_file_to_sandbox",
                "description": "Copy a file from local to sandbox environment.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "local_path": {
                            "type": "string",
                            "description": "Local file path."
                        },
                        "sandbox_path": {
                            "type": "string",
                            "description": "Destination path in sandbox."
                        }
                    },
                    "required": ["local_path", "sandbox_path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "copy_file_from_sandbox",
                "description": "Copy a file from sandbox to local environment.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sandbox_path": {
                            "type": "string",
                            "description": "File path in sandbox."
                        },
                        "local_path": {
                            "type": "string",
                            "description": "Destination local path."
                        }
                    },
                    "required": ["sandbox_path", "local_path"]
                }
            }
        }
    ]

    # 准备用户输入
    messages = [
        {
            "role": "system", 
            "content": """你是一位Excel数据分析专家，擅长使用Python进行数据处理和可视化。请根据用户的需求，生成并执行相应的代码来分析Excel数据。
            所有的数据分析都应当在沙盒中进行，为了捕获程序运行的状态和结果，在代码中用print()语句把你想了解的信息输出。
            如果涉及到生成图片或产生其他文件，除了在界面上渲染显示外，还应将其从沙盒环境复制到外部存储。
            如果要作图，由于中文字体可能出现显示问题，所以图片中文字一律使用英文。"""
        },
        {"role": "user", "content": user_input},
        {"role": "assistant", "content": "好的，请稍等，我正在分析您的需求并生成代码。"},
    ]
    
    # 如果提供了Excel文件路径，先将其复制到沙盒中
    if excel_file_path:
        # 修改为只提供目标目录路径，不包含文件名
        sandbox_dir = "/sandbox/"
        # 从原始路径中提取文件名
        excel_filename = os.path.basename(excel_file_path)
        # 构建完整的沙盒路径（仅用于告知模型）
        sandbox_excel_path = os.path.join(sandbox_dir, excel_filename)
        
        # 调用复制函数时只传递目录路径
        copy_result = copy_file_to_sandbox(excel_file_path, sandbox_dir)
        st.info(copy_result)
        
        # 提取Excel文件的前几行数据
        try:
            # 读取Excel文件
            df = pd.read_excel(excel_file_path)
            # 获取前5行数据
            preview_rows = min(5, len(df))
            excel_preview = df.head(preview_rows).to_string()
            # 获取列名信息
            columns_info = "列名: " + ", ".join(df.columns.tolist())
            # 获取数据类型信息
            dtypes_info = "数据类型:\n" + df.dtypes.to_string()
            # 构建Excel预览信息
            excel_info = f"\n\nExcel文件预览信息:\n文件名: {excel_filename}\n总行数: {len(df)}\n总列数: {df.shape[1]}\n{columns_info}\n\n前{preview_rows}行数据预览:\n{excel_preview}\n\n{dtypes_info}"
            
            # 告诉模型Excel文件的位置和预览信息
            messages[0]["content"] += f"\n\nExcel文件已上传到沙盒环境，路径为: {sandbox_excel_path}{excel_info}"
        except Exception as e:
            # 如果提取失败，只告诉模型文件位置
            st.warning(f"无法提取Excel预览: {str(e)}")
            messages[0]["content"] += f"\n\nExcel文件已上传到沙盒环境，路径为: {sandbox_excel_path}"
    
    # 创建结果显示区域的容器，以便实时更新内容
    result_container = st.container()
    
    # 创建进度指示器
    with st.status("正在处理您的请求...", expanded=True) as status:
        # 初始状态消息，将在流程结束时被清除
        status_message = st.empty()
        status_message.write("正在分析您的需求并生成代码...")
        
        # 循环处理工具调用
        generated_files = []  # 用于跟踪生成的文件
        all_outputs = []  # 存储所有输出
        step_counter = 1  # 用于跟踪步骤编号
        
        # 在容器（streamlit概念）中预先创建标题，避免重复
        with result_container:
            st.subheader("处理进度与结果", divider="rainbow")
            # 创建各种输出的占位符
            output_placeholder = st.empty()
        
        # 实时显示结果的函数
        def update_results():
            # 使用with块和output_placeholder来避免重复渲染
            with output_placeholder.container():
                # 清空之前的内容
                st.empty()
                
                # 使用一个计数器来确保每次渲染都有唯一的key
                import time
                render_id = int(time.time() * 1000)  # 使用毫秒级时间戳
                
                # 遍历所有输出并生成对应的显示元素
                for idx, output in enumerate(all_outputs):
                    # 使用渲染ID、索引和输出类型组合生成唯一key
                    unique_key = f"{render_id}_{idx}_{output['type']}"
                    
                    if output["type"] == "ai":
                        # markdown不支持key参数，使用container包装
                        with st.container():
                            st.markdown(output["content"])
                    elif output["type"] == "code":
                        with st.container():
                            # 使用expander组件包装代码块，默认折叠状态
                            with st.expander("查看代码", expanded=False):
                                st.code(output["content"], language=output["lang"])
                    elif output["type"] == "result":
                        with st.container():
                            # 使用expander组件包装执行结果，默认折叠状态
                            with st.expander("查看执行结果", expanded=False):
                                st.text_area("执行结果", output["content"], height=200, key=f"result_{unique_key}")
                    elif output["type"] == "info":
                        with st.container():
                            st.info(output["content"])
                    elif output["type"] == "files":
                        with st.container():
                            st.subheader("生成的文件")
                            for file_idx, file in enumerate(output["content"]):
                                st.success(f"文件已保存: {file}")
                                # 如果是图片文件，尝试显示
                                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.svg', '.gif')):
                                    # 移除key参数，st.image()不支持该参数
                                    st.image(file)
        
        while True:
            # 更新状态消息
            status.update(label=f"步骤 {step_counter}: 正在与AI模型交互...", state="running")
            
            # 记录发送给模型的请求
            log_model_request(messages, model="deepseek-ai/DeepSeek-V3")
            
            response = client.chat.completions.create(
                model="deepseek-ai/DeepSeek-V3",  # 可以根据需要更换为其他模型
                messages=messages,
                tools=tools,
                tool_choice="auto"
            )
            
            response_message = response.choices[0].message
            messages.append(response_message)
            
            # 记录模型的响应
            log_model_response(response_message, model="deepseek-ai/DeepSeek-V3")
            
            # 记录大模型的输出并实时显示
            if response_message.content:
                all_outputs.append({"type": "ai", "content": response_message.content})
                update_results()  # 实时更新显示
            
            # 检查是否有工具调用
            if hasattr(response_message, 'tool_calls') and response_message.tool_calls:
                # 处理工具调用
                for tool_call in response_message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    # 更新状态消息，显示当前执行的操作
                    status.update(label=f"步骤 {step_counter}: 执行操作 - {function_name}", state="running")
                    step_counter += 1
                    
                    if function_name == "run_code":
                        # 解析参数
                        lang = function_args.get("lang")
                        code = function_args.get("code")
                        libraries = function_args.get("libraries")
                        
                        # 显示代码
                        all_outputs.append({"type": "code", "lang": lang, "content": code})
                        update_results()  # 实时更新显示代码
                        
                        # 执行代码
                        status.update(label=f"步骤 {step_counter-1}: 正在执行代码...", state="running")
                        result = run_code(lang, code, libraries)
                        all_outputs.append({"type": "result", "content": result})
                        update_results()  # 实时更新显示结果
                        
                    elif function_name == "copy_file_to_sandbox":
                        local_path = function_args.get("local_path")
                        sandbox_path = function_args.get("sandbox_path")
                        result = copy_file_to_sandbox(local_path, sandbox_path)
                        all_outputs.append({"type": "info", "content": result})
                        update_results()  # 实时更新显示
                        
                    elif function_name == "copy_file_from_sandbox":
                        sandbox_path = function_args.get("sandbox_path")
                        local_path = function_args.get("local_path")
                        status.update(label=f"步骤 {step_counter-1}: 正在复制文件...", state="running")
                        result = copy_file_from_sandbox(sandbox_path, local_path)
                        all_outputs.append({"type": "info", "content": result})
                        generated_files.append(local_path)
                        update_results()  # 实时更新显示
                    
                    # 记录工具执行结果
                    log_tool_result(function_name, result)
                    
                    # 将工具执行结果添加到消息中
                    tool_message = {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": function_name,
                        "content": result
                    }
                    messages.append(tool_message)
                
                # 继续对话
                continue
            else:
                # 没有工具调用，处理生成的文件并返回最终结果
                final_result = response_message.content
                
                # 如果有生成的文件，将它们添加到结果中
                if generated_files:
                    file_paths_text = "\n\n生成的文件:\n" + "\n".join(generated_files)
                    final_result += file_paths_text
                    all_outputs.append({"type": "files", "content": generated_files})
                    update_results()  # 实时更新显示
                
                # 清除初始状态消息并更新状态为完成
                status_message.empty()
                status.update(label="处理完成！", state="complete")
                break
    
    # 最终结果已经在实时更新中显示，不需要重复显示

# 主应用逻辑
def main():
    # 侧边栏 - 文件上传
    with st.sidebar:
        st.header("上传文件")
        uploaded_file = st.file_uploader("选择一个Excel文件", type=["xlsx", "xls"])
        
        # 如果上传了文件，保存到临时文件并显示预览
        temp_file_path = None
        if uploaded_file is not None:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                temp_file_path = tmp_file.name
            
            # 显示文件预览
            st.subheader("文件预览")
            try:
                df = pd.read_excel(temp_file_path)
                st.dataframe(df.head(10))
                st.info(f"总行数: {len(df)}，总列数: {df.shape[1]}")
            except Exception as e:
                st.error(f"无法预览文件: {str(e)}")
    
    # 主界面 - 用户输入
    st.subheader("请描述您的分析需求")
    user_request = st.text_area(
        "例如: 分析销售数据，找出销售额最高的前5个产品，并生成柱状图", 
        height=100,
        key="user_input_text_area"
    )
    
    # 处理按钮
    if st.button("开始分析", type="primary"):
        if not user_request:
            st.warning("请输入您的分析需求")
        else:
            # 执行分析
            run_agent(user_request, temp_file_path)

if __name__ == "__main__":
    main()