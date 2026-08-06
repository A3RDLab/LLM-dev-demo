import os
import argparse
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage

# 加载项目根目录 .env（API_KEY / API_BASE / MODEL，见 .env.example）
load_dotenv(Path(__file__).resolve().parent / ".env")

# 设置命令行参数解析
parser = argparse.ArgumentParser(description='LangChain对话脚本')
parser.add_argument('--model', type=str, default=os.getenv("MODEL", "deepseek-ai/DeepSeek-R1"),
                    help='指定使用的模型名称（默认读取环境变量 MODEL）')
parser.add_argument('--api_key', type=str, default=None,
                    help='指定API密钥（默认使用环境变量 API_KEY）')
parser.add_argument('--base_url', type=str, default=os.getenv("API_BASE", "https://api.siliconflow.cn/v1/"),
                    help='指定API基础URL（默认读取环境变量 API_BASE）')

args = parser.parse_args()

# 优先使用命令行提供的API_KEY，若没有则使用环境变量
api_key = args.api_key if args.api_key else os.getenv("API_KEY")

# 初始化LangChain模型
llm = ChatOpenAI(
    model=args.model,
    openai_api_key=api_key,
    openai_api_base=args.base_url,
    temperature=0.7
)

# 初始化空对话历史
messages = []

# 直接进入对话循环
while True:
    user_input = input("\n请输入（直接回车退出对话）: ").strip()
    
    # 退出条件检测
    if not user_input or user_input.lower() == 'exit':
        break
    
    # 添加用户输入到对话历史
    messages.append(HumanMessage(content=user_input))
    
    # 生成流式回复
    print(f"\n{args.model} 正在思考...")
    answer_content = ""
    is_answering = False
    
    # 使用LangChain的流式处理
    for chunk in llm.stream(messages):
        # 处理回复内容
        if chunk.content and chunk.content != "":
            # 首次开始回复时显示分隔
            if not is_answering:
                print(f"\n\n{args.model} 回复:")
                is_answering = True
            
            # 输出当前块内容
            print(chunk.content, end='', flush=True)
            answer_content += chunk.content
    
    # 添加完整回复到对话历史
    if answer_content:
        messages.append(AIMessage(content=answer_content))

print("对话已结束")
