"""
Text2SQL 示例：自然语言查询数据库
====================================
演示现代 Text2SQL 的轻量主流路线（无需 Vanna 训练）：

    1. 自动内省数据库 schema（DDL）注入系统提示词——模型"看得见"表结构
    2. 模型以原生 function calling 发起 execute_sql 工具调用
    3. 工具执行 SQL 并回填结果；SQL 报错时把错误信息回传，模型自我修复重试
    4. 模型基于查询结果用自然语言回答

数据库：Chinook.sqlite（音乐商店示例库，11 张表：Customer/Invoice/Track/...）
安全约束：只允许只读查询（SELECT/WITH），数据库以 read-only 模式打开

用法：
    python text2sql_demo.py                                     # 默认示例问题
    python text2sql_demo.py --query "每个国家客户的总消费是多少？按降序取前5"
"""

import os
import json
import sqlite3
import argparse
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# ===== 配置 =====
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# 加载项目根目录 .env（API_KEY / API_BASE / MODEL，见 .env.example）
load_dotenv(Path(SCRIPT_DIR) / ".env")
DB_PATH = os.path.join(SCRIPT_DIR, "Chinook.sqlite")

parser = argparse.ArgumentParser(description='Text2SQL 示例')
parser.add_argument('--query', type=str,
                    default='哪个国家的客户总消费最高？金额是多少？顺便列出消费前3名的客户',
                    help='自然语言问题')
parser.add_argument('--db', type=str, default=DB_PATH, help='SQLite 数据库路径')
parser.add_argument('--model', type=str, default=os.getenv("MODEL", "qwen3.6-27b"),
                    help='模型名称（默认读环境变量 MODEL）')
parser.add_argument('--api_key', type=str, default=None,
                    help='API密钥（默认使用环境变量API_KEY）')
parser.add_argument('--base_url', type=str, default=os.getenv("API_BASE", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
                    help='API基础URL（默认读环境变量 API_BASE）')
args = parser.parse_args()

api_key = args.api_key if args.api_key else os.getenv("API_KEY")
client = OpenAI(api_key=api_key, base_url=args.base_url)


# ===== 1. Schema 内省：让模型"看得见"表结构 =====
def get_schema(db_path: str) -> str:
    """生成紧凑的 DDL 描述：表名 + 列名/类型/主键"""
    # read-only 模式打开，从连接层面杜绝写操作
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cur = conn.cursor()
    tables = [r[0] for r in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    lines = []
    for t in tables:
        cols = cur.execute(f"PRAGMA table_info('{t}')").fetchall()
        col_desc = ", ".join(
            f"{c[1]} {c[2]}{' PK' if c[5] else ''}" for c in cols)
        count = cur.execute(f"SELECT COUNT(*) FROM '{t}'").fetchone()[0]
        lines.append(f"{t}({col_desc})  -- {count}行")
    conn.close()
    return "\n".join(lines)


# ===== 2. 工具定义与执行 =====
TOOLS = [{
    "type": "function",
    "function": {
        "name": "execute_sql",
        "description": "在 Chinook 数据库上执行只读 SQL 查询并返回结果。SQL 语法错误时会返回错误信息，可修正后重试。",
        "parameters": {
            "type": "object",
            "properties": {
                "sql": {"type": "string", "description": "要执行的 SELECT 语句"}
            },
            "required": ["sql"]
        }
    }
}]


def execute_sql(sql: str) -> str:
    """只读执行 SQL，返回格式化结果或错误信息（错误回传给模型以实现自修复）"""
    s = sql.strip().lower()
    if not (s.startswith("select") or s.startswith("with")):
        return "错误：出于安全考虑只允许 SELECT/WITH 查询"
    try:
        conn = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchmany(20)
        columns = [d[0] for d in cur.description] if cur.description else []
        conn.close()
        result = {"columns": columns, "rows": [list(r) for r in rows],
                  "row_count_returned": len(rows)}
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:
        return f"SQL 执行错误: {e}。请检查表名/列名是否正确，修正后重试。"


# ===== 3. Agent 循环：决策 → 执行 → 回填 → 再决策 =====
def stream_chat(messages):
    """流式接收一轮模型输出，累积成一条完整的 assistant 消息。

    流式要点：content 片段逐字打印（最终回答打字机效果）；
    tool_calls 片段按 index 归位——首个片段携带 id 与函数名，
    后续片段只是 arguments 的文本碎片，逐个拼接。
    """
    stream = client.chat.completions.create(
        model=args.model, messages=messages, tools=TOOLS, temperature=0.1, stream=True)
    content_parts = []
    tool_calls = {}  # index -> 累积中的工具调用
    answer_started = False

    for chunk in stream:
        delta = chunk.choices[0].delta if chunk.choices else None
        if delta is None:
            continue
        if delta.content:
            if not answer_started:  # 首个片段到达才打标签，避免工具轮日志接在标签后
                print("[最终回答]")
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

    if answer_started:  # 流式回答结束补个换行
        print()
    return {
        "content": "".join(content_parts),
        "tool_calls": [dict(tool_calls[i], type="function") for i in sorted(tool_calls)] or None,
    }


def run(query: str, schema: str, max_rounds: int = 5):
    messages = [
        {"role": "system", "content": f"""你是数据分析师，负责把用户的自然语言问题转换为 SQL 查询 Chinook 数据库。
数据库 Schema（表名(列名 类型[ PK])）：
{schema}

工作方式：使用 execute_sql 工具执行查询；拿到结果后用中文总结回答用户问题。
如果 SQL 报错，根据错误信息修正后重试。不要编造数据。"""},
        {"role": "user", "content": query},
    ]

    for round_no in range(1, max_rounds + 1):
        print(f"\n── 第 {round_no} 轮 ──")
        msg = stream_chat(messages)

        if not msg["tool_calls"]:
            return msg["content"]  # 最终回答已在 stream_chat 内逐字流式打印

        # 把 assistant 的工具调用消息追加回历史（保持消息序列合法）
        messages.append({"role": "assistant", "content": msg["content"],
                         "tool_calls": msg["tool_calls"]})

        for tc in msg["tool_calls"]:
            sql = json.loads(tc["function"]["arguments"])["sql"]
            print(f"[执行 SQL] {sql}")
            result = execute_sql(sql)
            print(f"[查询结果] {result[:300]}{'...' if len(result) > 300 else ''}")
            messages.append({"role": "tool", "tool_call_id": tc["id"], "content": result})

    raise RuntimeError(f"超过 {max_rounds} 轮仍未得到最终回答")


if __name__ == "__main__":
    schema = get_schema(args.db)
    print("[Schema 内省结果]")
    print(schema)
    print(f"\n[用户问题] {args.query}")
    run(args.query, schema)
