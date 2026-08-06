# Please install OpenAI SDK first: `pip3 install openai`
# 配置优先级：命令行参数 > 环境变量（MODEL / API_BASE / API_KEY，见根目录 .env.example）

import os
import argparse
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# 加载项目根目录 .env（API_KEY / API_BASE / MODEL，见 .env.example）
load_dotenv(Path(__file__).resolve().parent / ".env")

parser = argparse.ArgumentParser(description='最简单的单次 LLM 调用示例')
parser.add_argument('--model', type=str, default=os.getenv("MODEL", "qwen3-max"),
                    help='指定使用的模型名称（默认读环境变量 MODEL）')
parser.add_argument('--api_key', type=str, default=None,
                    help='指定API密钥（默认使用环境变量API_KEY）')
parser.add_argument('--base_url', type=str, default=os.getenv("API_BASE", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
                    help='指定API基础URL（默认读环境变量 API_BASE）')

args = parser.parse_args()

# 优先使用命令行提供的API_KEY，若没有则使用环境变量
api_key = args.api_key if args.api_key else os.getenv("API_KEY")

client = OpenAI(api_key=api_key, base_url=args.base_url)

response = client.chat.completions.create(
    model=args.model,
    messages=[
        {"role": "system", "content": "你在回答博士生的提问。"},
        {"role": "user", "content": "Hello!"},
        {"role": "assistant", "content": "Hello! 👋 How can I assist you today? 😊"},
        {"role": "user", "content": "你好，我是张三，我想咨询一下关于深度求索的问题。"}
    ],
    stream=False
)

message = response.choices[0].message
print(message.content)
