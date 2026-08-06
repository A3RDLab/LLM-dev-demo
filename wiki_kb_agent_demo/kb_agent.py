"""
kb_agent.py — LLM Wiki 风格的自然语言导航 Agent

LLM wiki 的消费范式不是向量检索，而是"LLM 自主导航"：
模型从 index.md 目录页出发，用自然语言理解目录结构，决定读哪一页，
再顺着页面内的 wiki 链接迭代深入，直到找到答案。

因此给模型挂三个"图书管理员"式工具：
  - read_page(path)     ：读取一个页面（约定从 index.md 开始）
  - list_pages(subdir)  ：浏览知识库目录结构（链接不够用时兜底）
  - grep_kb(pattern)    ：全文正则搜索（目录定位不到关键词时兜底）

零预处理、零 embedding：知识库 copy 进来即是最新状态。

用法：
    python kb_agent.py                          # 交互式对话
    python kb_agent.py --once "什么是 RAG？"    # 单轮提问
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

HERE = Path(__file__).resolve().parent
load_dotenv(HERE.parent / ".env")
load_dotenv(HERE / ".env")

# 对话模型默认走硅基流动（与仓库其他 demo 一致），可用 --model/--base_url 切换
DEFAULT_BASE_URL = os.getenv("BASE_URL", "https://api.siliconflow.cn/v1")
DEFAULT_MODEL = os.getenv("CHAT_MODEL", "deepseek-ai/DeepSeek-V3")

MAX_TOOL_ROUNDS = 10       # 导航式需要多轮探索，轮数放宽一些
ENTRY_PAGE = "index.md"    # LLM wiki 约定的入口目录页

SYSTEM_PROMPT = f"""你是一个知识库导航助手，只能依据知识库中的内容回答问题。

这个知识库是 LLM wiki 风格：入口是 {ENTRY_PAGE} 目录页，页面之间通过 Markdown 链接互相引用。

工作方式：
1. 对话开始时，先 read_page('{ENTRY_PAGE}') 阅读目录，了解知识库结构；
2. 根据用户问题，从目录中选择最相关的页面 read_page 阅读；
3. 若页面中提到相关的 wiki 链接，继续顺着链接深入阅读；
4. 如果目录不足以定位，用 grep_kb 全文搜索关键词，再用 list_pages 浏览结构；
5. 回答时引用来源页面路径，如：（来源：02-rag.md#分块策略）；
6. 知识库中确实没有相关内容时如实说明，不要编造。"""

# ----------------------------------------------------------- 工具声明（给模型看）

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_page",
            "description": "读取知识库中一个页面的完整 Markdown 内容。导航的起点是 index.md 目录页；读到页面内的 wiki 链接后可继续用它深入。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "页面相对路径，如 'index.md' 或 'guides/02-rag.md'"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_pages",
            "description": "列出知识库中的页面清单（含子目录），用于了解整体结构或在目录页之外寻找页面。",
            "parameters": {
                "type": "object",
                "properties": {
                    "subdir": {"type": "string", "description": "可选，子目录相对路径，如 'guides'；缺省列出全部"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "grep_kb",
            "description": "在知识库全部 Markdown 页面中做正则/关键词搜索，返回匹配的页面、行号与上下文行。用于目录无法定位关键词时兜底。",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "要搜索的关键词或正则表达式，如 '分块策略' 或 'rerank'"},
                    "max_results": {"type": "integer", "description": "最多返回的匹配条数，默认 15", "default": 15},
                },
                "required": ["pattern"],
            },
        },
    },
]


# ----------------------------------------------------------- 工具实现（程序真正执行）

def _safe_resolve(kb_dir: Path, rel: str) -> Path | None:
    """把相对路径解析为真实路径，拒绝跳出知识库目录（防路径穿越）。"""
    target = (kb_dir / rel).resolve()
    if not target.is_relative_to(kb_dir.resolve()):
        return None
    return target


def make_tool_handlers(kb_dir: Path):
    kb_root = kb_dir.resolve()  # 统一用绝对路径，避免相对/绝对混用导致的 relative_to 错误

    def read_page(path: str) -> str:
        target = _safe_resolve(kb_root, path)
        if target is None or not target.is_file():
            return f"错误：页面不存在或路径非法：{path}"
        return target.read_text(encoding="utf-8", errors="ignore")

    def list_pages(subdir: str = "") -> str:
        base = _safe_resolve(kb_root, subdir) if subdir else kb_root
        if base is None or not base.is_dir():
            return f"错误：目录不存在：{subdir or '.'}"
        files = sorted(p.relative_to(kb_root).as_posix() for p in base.rglob("*.md"))
        if not files:
            return "该目录下没有 .md 页面。"
        return "\n".join(files)

    def grep_kb(pattern: str, max_results: int = 15) -> str:
        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error:
            # 非法正则时退化为字面量匹配
            regex = re.compile(re.escape(pattern), re.IGNORECASE)
        hits = []
        for md in sorted(kb_root.rglob("*.md")):
            rel = md.relative_to(kb_root).as_posix()
            for i, line in enumerate(md.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                if regex.search(line):
                    hits.append(f"{rel}:{i}: {line.strip()[:160]}")
                    if len(hits) >= max_results:
                        break
            if len(hits) >= max_results:
                break
        return "\n".join(hits) if hits else "没有匹配结果。"

    return {"read_page": read_page, "list_pages": list_pages, "grep_kb": grep_kb}


# ----------------------------------------------------------- Agent 主循环

def stream_completion(client: OpenAI, model: str, messages: list) -> dict:
    """流式接收一轮模型输出，累积成一条完整的 assistant 消息。

    关键技巧：stream 模式下 content 与 tool_calls 都是增量片段（delta），
    - content 片段直接逐字打印（打字机效果），同时累积；
    - tool_calls 片段按 index 归位：首个片段携带 id 与函数名，
      后续片段只是 arguments 的文本碎片，逐个拼接。
    """
    stream = client.chat.completions.create(
        model=model, messages=messages, tools=TOOLS, stream=True)
    content_parts: list[str] = []
    tool_calls: dict[int, dict] = {}  # index -> 累积中的工具调用
    answer_started = False

    for chunk in stream:
        delta = chunk.choices[0].delta if chunk.choices else None
        if delta is None:
            continue
        if delta.content:  # 最终回答的文字片段：边收边打印
            if not answer_started:  # 首个片段到达才打标签，避免工具轮日志接在标签后
                print("\n助手: ", end="", flush=True)
                answer_started = True
            print(delta.content, end="", flush=True)
            content_parts.append(delta.content)
        for tc in delta.tool_calls or []:
            acc = tool_calls.setdefault(tc.index, {"id": "", "function": {"name": "", "arguments": ""}})
            if tc.id:
                acc["id"] = tc.id
            if tc.function and tc.function.name:
                acc["function"]["name"] = tc.function.name
            if tc.function and tc.function.arguments:
                acc["function"]["arguments"] += tc.function.arguments

    if content_parts:  # 流式回答结束补个换行
        print()
    return {
        "role": "assistant",
        "content": "".join(content_parts),
        "tool_calls": [dict(tool_calls[i], type="function") for i in sorted(tool_calls)] or None,
    }


def run_agent(client: OpenAI, model: str, handlers: dict, messages: list[dict]) -> str:
    """一次用户提问的完整处理：循环执行 模型决策 → 工具执行 → 结果回填。"""
    for _ in range(MAX_TOOL_ROUNDS):
        msg = stream_completion(client, model, messages)
        messages.append(msg)

        if not msg["tool_calls"]:  # 模型给出最终答案（已在 stream_completion 中流式打印）
            return msg["content"]

        # 执行模型要求的所有工具调用，结果以 role=tool 回填
        for call in msg["tool_calls"]:
            fn = handlers.get(call["function"]["name"])
            args = json.loads(call["function"]["arguments"] or "{}")
            print(f"  🔧 调用工具 {call['function']['name']}({args})")
            result = fn(**args) if fn else f"未知工具：{call['function']['name']}"
            messages.append({
                "role": "tool",
                "tool_call_id": call["id"],
                "content": result,
            })
    return "（达到最大工具调用轮数，中止）"


def main():
    parser = argparse.ArgumentParser(description="LLM Wiki 导航 Agent")
    parser.add_argument("--kb-dir", default=str(HERE / "knowledge_base"), help="知识库目录")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--api-key", default=None, help="对话模型 Key（默认取环境变量 API_KEY / SILICONFLOW_API_KEY）")
    parser.add_argument("--once", default=None, help="单轮提问模式，直接传入问题")
    args = parser.parse_args()

    api_key = args.api_key or os.getenv("API_KEY") or os.getenv("SILICONFLOW_API_KEY")
    if not api_key:
        sys.exit("错误：未找到对话模型 API Key，请设置 API_KEY（或 SILICONFLOW_API_KEY），或用 --api-key 传入")

    kb_dir = Path(args.kb_dir)
    if not (kb_dir / ENTRY_PAGE).exists():
        print(f"提示：知识库中没有 {ENTRY_PAGE}，模型将从 list_pages 开始探索")

    client = OpenAI(api_key=api_key, base_url=args.base_url)
    handlers = make_tool_handlers(kb_dir)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if args.once:
        messages.append({"role": "user", "content": args.once})
        # 最终回答已在 run_agent 内流式打印，这里不再重复输出
        run_agent(client, args.model, handlers, messages)
        return

    print("进入对话（输入 exit 或回车退出）")
    while True:
        user_input = input("\n你: ").strip()
        if not user_input or user_input.lower() == "exit":
            break
        messages.append({"role": "user", "content": user_input})
        # 工具轮与最终回答均在 run_agent 内实时打印（回答为逐字流式）
        run_agent(client, args.model, handlers, messages)


if __name__ == "__main__":
    main()
