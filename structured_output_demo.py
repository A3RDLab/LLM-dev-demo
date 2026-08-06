"""
Structured Output（结构化输出）示例
=====================================
演示现代 LLM 应用开发的标配能力：让模型严格按照给定的 JSON Schema 输出，
而不是靠 prompt 里写"请输出 JSON"再手动解析（容易格式错误、难以校验）。

对比旧写法：
    旧：prompt 里要求"只输出 JSON" -> json.loads() -> 经常解析失败需要重试
    新：response_format={"type": "json_schema", ...} -> 服务端保证输出符合 Schema

依赖：pip install openai pydantic
运行前请设置环境变量 API_KEY（可参考根目录 .env.example）
"""

import os
import json
import argparse
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field

# 加载项目根目录 .env（API_KEY / API_BASE / MODEL，见 .env.example）
load_dotenv(Path(__file__).resolve().parent / ".env")

# 终端颜色：过程信息（分节标题、降级提示）灰色，结果（JSON/Pydantic 对象）用终端默认色
GRAY = "\033[90m"
RESET = "\033[0m"

# ===== 1. 用 Pydantic 定义期望的输出结构 =====
class Contact(BaseModel):
    """从一段自然语言文本中抽取出的联系人信息"""
    name: str = Field(description="联系人姓名")
    role: Optional[str] = Field(default=None, description="职位/角色，未提及时为 null")
    phone: Optional[str] = Field(default=None, description="手机号，未提及时为 null")
    email: Optional[str] = Field(default=None, description="邮箱，未提及时为 null")


class ExtractionResult(BaseModel):
    """结构化抽取的完整结果"""
    contacts: List[Contact] = Field(description="文本中出现的所有联系人")
    company: Optional[str] = Field(default=None, description="涉及的公司名称")
    summary: str = Field(description="一句话概括文本内容")


# ===== 2. 命令行参数（与仓库其他 demo 保持一致的风格） =====
parser = argparse.ArgumentParser(description='Structured Output 示例')
parser.add_argument('--model', type=str, default=os.getenv("MODEL", "Pro/deepseek-ai/DeepSeek-V3"),
                    help='指定使用的模型名称（默认读取环境变量 MODEL）')
parser.add_argument('--api_key', type=str, default=None,
                    help='指定API密钥（默认使用环境变量 API_KEY）')
parser.add_argument('--base_url', type=str, default=os.getenv("API_BASE", "https://api.siliconflow.cn/v1/"),
                    help='指定API基础URL（默认读取环境变量 API_BASE）')
args = parser.parse_args()

api_key = args.api_key if args.api_key else os.getenv("API_KEY")

client = OpenAI(api_key=api_key, base_url=args.base_url)

# ===== 3. 待抽取的示例文本 =====
TEXT = """
今天参加了联想集团举办的 AI 应用交流会。
会上认识了两位合作伙伴：
王小明，联想解决方案架构师，手机 138-0013-8000，邮箱 wangxm@example.com；
另外一位是负责采购的李华，只留了邮箱 lihua@example.com，电话说回头再给。
会议主要讨论了大模型在企业知识管理场景的落地方案。
"""

MESSAGES = [
    # 注意：提示词里明确提到 JSON——json_object 宽松模式要求 messages 中必须出现 "json" 字样
    {"role": "system", "content": "你是一个信息抽取助手，请严格按给定 Schema 输出 JSON 结果。"},
    {
        "role": "user",
        # 关键：宽松模式下服务端不会把 Schema 传给模型，必须把 Schema 写进提示词，
        # 否则模型不知道需要哪些字段（实战中常见的丢字段问题）
        "content": (
            f"请从下面的文本中抽取联系人信息，输出符合以下 JSON Schema 的 JSON：\n"
            f"{json.dumps(ExtractionResult.model_json_schema(), ensure_ascii=False, indent=2)}\n\n"
            f"文本：\n{TEXT}"
        ),
    },
]

# ===== 4. 发起请求：优先 json_schema 严格模式，不支持时自动降级为 json_object =====
# 两种模式都开 stream=True：JSON 同样逐 token 生成，流式打印与前面实验保持一致的体验
from openai import BadRequestError

# 关键经验：思考模型开思考模式做结构化输出容易失控（思考流与 JSON 约束打架，
# 产出超长垃圾文本），生产上对思考模型做 JSON 抽取时应关闭思考
EXTRA_BODY = {"enable_thinking": False}

try:
    stream = client.chat.completions.create(
        model=args.model,
        messages=MESSAGES,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "extraction_result",
                "strict": True,
                # 直接从 Pydantic 模型生成 Schema，模型定义即契约
                "schema": ExtractionResult.model_json_schema(),
            },
        },
        extra_body=EXTRA_BODY,
        max_tokens=2000,
        temperature=0.2,
        stream=True,
    )
    mode = "json_schema 严格模式（服务端保证符合 Schema）"
except BadRequestError as e:
    # 部分部署只支持 json_object：只保证输出是合法 JSON，不保证符合 Schema，
    # 结构正确性完全依赖后面的 Pydantic 校验兑底
    print(f"{GRAY}[服务端不支持 json_schema，降级为 json_object 宽松模式]{RESET}\n{GRAY}{str(e)[:120]}...{RESET}\n")
    stream = client.chat.completions.create(
        model=args.model,
        messages=MESSAGES,
        response_format={"type": "json_object"},
        extra_body=EXTRA_BODY,
        max_tokens=2000,
        temperature=0.2,
        stream=True,
    )
    mode = "json_object 宽松模式（仅保证合法 JSON）"

# ===== 5. 流式接收 JSON：边生成边打印，同时累积完整文本 =====
# delta.content 里流出的就是 JSON 文本片段，与非流式调用相比只是把
# “生成完一次性返回”变成“逐块返回”，最终内容完全一致
print(f"{GRAY}=== 流式生成 JSON（{mode}） ==={RESET}")
chunks = []
for chunk in stream:
    delta = chunk.choices[0].delta.content if chunk.choices else None
    if delta:
        print(delta, end="", flush=True)
        chunks.append(delta)
print("\n")
raw = "".join(chunks)

# ===== 6. 解析并用 Pydantic 校验（宽松模式下这一步是结构正确性的唯一防线） =====
# 注意：不能因为“流式看着输出了”就跳过校验——中途的片段大多不是合法 JSON，
# 结构正确性仍以这里的完整校验为准
result = ExtractionResult.model_validate_json(raw)

print(f"{GRAY}=== Pydantic 对象（可直接用于后续业务逻辑） ==={RESET}")
print(f"公司: {result.company}")
print(f"摘要: {result.summary}")
for c in result.contacts:
    print(f"- {c.name} | 角色: {c.role} | 电话: {c.phone} | 邮箱: {c.email}")
