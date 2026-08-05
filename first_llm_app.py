import os
import argparse
from openai import OpenAI

# 设置命令行参数解析
parser = argparse.ArgumentParser(description='AI对话脚本')
parser.add_argument('--model', type=str, default='deepseek-ai/DeepSeek-R1',
                    help='指定使用的模型名称（默认：deepseek-ai/DeepSeek-R1）')
parser.add_argument('--api_key', type=str, default=None,
                    help='指定API密钥（默认使用环境变量API_KEY）')
parser.add_argument('--base_url', type=str, default="https://api.siliconflow.cn/v1/",
                    help='指定API基础URL（默认：https://api.siliconflow.cn/v1/）')

args = parser.parse_args()

# 终端颜色（ANSI 转义码）：思考过程灰色，正式回复青色，便于区分
GRAY = "\033[90m"
CYAN = "\033[36m"
RESET = "\033[0m"

# 优先使用命令行提供的API_KEY，若没有则使用环境变量
api_key = args.api_key if args.api_key else os.getenv("API_KEY")

client = OpenAI(
    api_key=api_key,
    base_url=args.base_url,
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
    messages.append({'role': 'user', 'content': user_input})
    
    # 生成流式回复
    reasoning_content = ""  # 记录完整思考过程
    answer_content = ""     # 记录完整回复
    is_answering = False    # 标记是否开始回复
    has_reasoning = False   # 标记模型是否具有思考能力
    
    # 创建流式请求
    completion = client.chat.completions.create(
        model=args.model,
        messages=messages,
        stream=True,
        temperature=0.7
    )
    
    for chunk in completion:
        # 如果chunk.choices为空，可能包含usage信息
        if not chunk.choices:
            if hasattr(chunk, 'usage'):
                # 可以在这里处理usage信息
                pass
        else:
            delta = chunk.choices[0].delta
            
            # 处理思考过程
            # 注意：用真值判断而非 is not None，且与 content 分支相互独立——
            # 过渡 chunk 可能同时携带 reasoning_content="" 和 content，
            # 若用 elif 互斥会把正文 token 丢掉
            reasoning_piece = getattr(delta, 'reasoning_content', None)
            if reasoning_piece:
                # 第一次发现有思考能力时，显示思考提示
                if not has_reasoning:
                    has_reasoning = True
                    print(f"\n{GRAY}── {args.model} 正在思考... ──{RESET}")
                
                print(f"{GRAY}{reasoning_piece}{RESET}", end='', flush=True)
                reasoning_content += reasoning_piece
            
            # 处理回复内容
            if delta.content:
                # 首次开始回复时显示分隔
                if not is_answering:
                    # 如果有思考过程，添加额外换行
                    if has_reasoning:
                        print(f"\n\n{CYAN}── {args.model} 回复: ──{RESET}")
                    else:
                        # 如果没有思考过程，直接显示回复提示
                        print(f"\n{CYAN}── {args.model} 回复: ──{RESET}")
                    
                    is_answering = True
                
                # 输出回复内容
                print(f"{CYAN}{delta.content}{RESET}", end='', flush=True)
                answer_content += delta.content
    
    # 将完整回复添加到对话历史
    if answer_content:
        messages.append({'role': 'assistant', 'content': answer_content})
        print()  # 在回复结束后添加换行
    elif has_reasoning:
        # 兑底提示：模型只输出了思考过程，未返回正文（通常是部署配置或模型异常）
        print(f"\n{GRAY}[模型只输出了思考过程，未返回正文内容]{RESET}")

print("对话已结束")
