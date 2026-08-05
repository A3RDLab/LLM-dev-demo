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
from typing import List, Optional

from openai import OpenAI
from pydantic import BaseModel, Field

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
parser.add_argument('--model', type=str, default='Pro/deepseek-ai/DeepSeek-V3',
                    help='指定使用的模型名称')
parser.add_argument('--api_key', type=str, default=None,
                    help='指定API密钥（默认使用环境变量API_KEY）')
parser.add_argument('--base_url', type=str, default="https://api.siliconflow.cn/v1/",
                    help='指定API基础URL')
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

# ===== 4. 发起带 json_schema 约束的请求 =====
completion = client.chat.completions.create(
    model=args.model,
    messages=[
        {"role": "system", "content": "你是一个信息抽取助手，请严格按给定 Schema 输出结果。"},
        {"role": "user", "content": f"请从下面的文本中抽取联系人信息：\n\n{TEXT}"},
    ],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "extraction_result",
            "strict": True,
            # 直接从 Pydantic 模型生成 Schema，模型定义即契约
            "schema": ExtractionResult.model_json_schema(),
        },
    },
    temperature=0.2,
)

raw = completion.choices[0].message.content

# ===== 5. 服务端已保证格式合法，可放心直接解析并用 Pydantic 校验 =====
result = ExtractionResult.model_validate_json(raw)

print("=== 原始 JSON ===")
print(json.dumps(json.loads(raw), ensure_ascii=False, indent=2))

print("\n=== Pydantic 对象（可直接用于后续业务逻辑） ===")
print(f"公司: {result.company}")
print(f"摘要: {result.summary}")
for c in result.contacts:
    print(f"- {c.name} | 角色: {c.role} | 电话: {c.phone} | 邮箱: {c.email}")
