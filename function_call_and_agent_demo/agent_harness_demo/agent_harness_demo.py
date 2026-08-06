# -*- coding: utf-8 -*-
"""Agent Harness 演示：LangChain DeepAgents + Agent Skills 渐进式披露

Harness = 模型之外的运行时外壳：系统提示词、工具编排、上下文管理、错误恢复。
DeepAgents 把一个 Claude Code 式的 harness 打包成可嵌入的组件：
    - planning（todo 规划）
    - 文件系统（read_file / write_file / edit_file / ls / glob / grep）
    - subagents（子代理派发）
    - skills（Agent Skills，SKILL.md 开放标准 + 三层渐进式披露）

本 demo 的观察重点——Skill 的三层渐进式披露（progressive disclosure）：
    第 1 层（元数据）：agent 启动时，系统提示词里只有每个 Skill 的 name + description
    第 2 层（指令）：agent 判断任务相关后，read_file 读取完整 SKILL.md
    第 3 层（资源）：按 SKILL.md 指引，需要时才读取 scripts/ references/ 等附属文件

运行：
    python agent_harness_demo.py
    python agent_harness_demo.py --task "分析销售数据的地区分布" --model qwen-max \
        --base_url https://dashscope.aliyuncs.com/compatible-mode/v1 --api_key $DASHSCOPE_API_KEY
"""
import argparse
import io
import os
import sys
import traceback
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from deepagents import create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend

# 终端颜色：过程信息（工具调用/结果/任务头）灰色，模型最终回复用终端默认色
GRAY = "\033[90m"
RESET = "\033[0m"

# 显式加载仓库根目录 .env（API_KEY / API_BASE / MODEL），避免依赖运行时的 cwd
_HERE = Path(__file__).resolve().parent
load_dotenv(_HERE.parent.parent / ".env")
load_dotenv(_HERE / ".env")

# Windows 控制台默认 GBK 编码，打印中文轨迹会 UnicodeEncodeError，强制 UTF-8
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent          # backend 根目录 = 本 demo 目录

# Windows 上 LibreOffice 默认不注册 PATH（winget 安装亦然），探测常见安装位置补进去，
# 使 skill 的 recalc.py 能直接找到 soffice.exe；macOS/Linux 上 soffice 通常已在 PATH，此步无害
if sys.platform == "win32":
    for _p in (r"C:\Program Files\LibreOffice\program",
               r"C:\Program Files (x86)\LibreOffice\program"):
        if Path(_p, "soffice.exe").exists() and _p not in os.environ.get("PATH", ""):
            os.environ["PATH"] = _p + os.pathsep + os.environ.get("PATH", "")
            break
DEFAULT_TASK = (
    "分析 data/ 中的销售记录 Excel，按 xlsx skill 的规范生成一份分析报告：\n"
    "1) 先用 pandas 读取并摸清数据结构（列、行数、时间范围）；\n"
    "2) 统计总销售额、各月销售额、销售额最高的前 5 个商品/类目；\n"
    "3) 把分析结论写入 report.md，并把带公式的汇总明细表写入 output/report.xlsx；\n"
    "4) 按 skill 规范运行 scripts/recalc.py 对 output/report.xlsx 做公式重算校验，有错误则修正后重跑"
)

SYSTEM_PROMPT = """你是一个数据分析 agent，运行在 harness 提供的工作目录中。

工作方式约定：
- data/ 目录下是输入数据；分析结论写入 report.md，Excel 产物一律放入 output/ 目录。
- 你配备了若干 Skill（见系统提示词中的 skill 清单）。当任务与某个 skill 的描述匹配时，
  必须先 read_file 读取该 skill 的完整 SKILL.md，再严格按其中的规范执行。
- 执行 Python 代码使用 execute_python 工具。环境中已预装 pandas 与 openpyxl。
- skill 自带的脚本（如 skills/xlsx/scripts/recalc.py）是完整可执行的：
  在 execute_python 中用 subprocess 运行，注意脚本内部导入约定要求 cwd 切到
  skills/xlsx/scripts/（如 subprocess.run(['python3', 'recalc.py', <文件绝对路径>], cwd='skills/xlsx/scripts')；
  Windows 上解释器用 sys.executable，并在 env 中设 PYTHONUTF8=1）。
  产出带公式的 Excel 后必须按其规范执行重算校验，并根据返回的 JSON 修正问题。
"""


@tool
def execute_python(code: str) -> str:
    """在本机执行一段 Python 代码并返回其输出。

    用于数据分析（读写 Excel、统计计算等）。代码的工作目录即 harness 工作目录，
    可以用相对路径访问 data/ 与 output/。已预装 pandas、openpyxl。
    在 Windows 上运行子进程（如 skill 的 recalc.py）时，请在 env 中设置 PYTHONUTF8=1
    以避免控制台编码导致的输出乱码。
    """
    stdout, stderr = io.StringIO(), io.StringIO()
    prev_cwd = os.getcwd()
    try:
        os.chdir(HERE)   # 固定工作目录：无论从哪里启动脚本，相对路径都指向本 demo 目录
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exec(code, {"__name__": "__main__"}, {})
    except Exception:
        # 把异常栈回传给模型，harness 惯例：让 agent 自己看到错误并修正
        stderr.write(traceback.format_exc(limit=5))
    finally:
        os.chdir(prev_cwd)
    out, err = stdout.getvalue().strip(), stderr.getvalue().strip()
    result = "\n\n".join(filter(None, [f"stdout:\n{out}" if out else "",
                                       f"stderr:\n{err}" if err else ""]))
    return result[:8000] or "（代码执行完毕，无任何输出）"


def build_agent(args):
    llm = ChatOpenAI(model=args.model, api_key=args.api_key, base_url=args.base_url,
                     temperature=0)
    # FilesystemBackend 以本 demo 目录为根：skills/ 与 data/ 都在 agent 的文件系统视野内
    backend = FilesystemBackend(root_dir=HERE)
    agent = create_deep_agent(
        model=llm,
        tools=[execute_python],
        system_prompt=SYSTEM_PROMPT,
        skills=["skills/"],      # 第 1 层：启动时只把 SKILL.md frontmatter 注入提示词
        backend=backend,
    )
    return agent


def run(agent, task):
    config = {"recursion_limit": 80}
    step = 0
    # stream_mode="messages" 时，每个 chunk 是 (message, metadata) 元组
    for msg, _meta in agent.stream({"messages": [{"role": "user", "content": task}]},
                                   config=config, stream_mode="messages"):
        mtype = type(msg).__name__
        if mtype == "AIMessage":
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    step += 1
                    args_str = str(tc["args"])
                    args_str = args_str if len(args_str) <= 200 else args_str[:200] + " …(截断)"
                    marker = ""
                    if tc["name"] == "read_file" and "SKILL.md" in str(tc["args"]):
                        marker = "   <<< 第 2 层：加载完整 SKILL.md 指令"
                    elif tc["name"] == "read_file":
                        marker = "   <<< 第 3 层：按需读取 skill 附属资源"
                    print(f"\n{GRAY}[{step:02d}] 🛠  调用工具 {tc['name']}({args_str}){marker}{RESET}")
            elif msg.content:
                print(f"\n{GRAY}🤖 模型回复：{RESET}\n{msg.content}")
        elif mtype == "ToolMessage":
            content = str(msg.content)
            print(f"{GRAY}     ↳ 结果({len(content)} 字符)：{content[:300]}"
                  + (" …(截断)" if len(content) > 300 else "") + f"{RESET}")


def main():
    parser = argparse.ArgumentParser(description='Agent Harness 演示（DeepAgents + Skills）')
    parser.add_argument('--model', type=str, default=os.getenv("MODEL", "Pro/deepseek-ai/DeepSeek-V3"),
                        help='模型名（默认读环境变量 MODEL）')
    parser.add_argument('--api_key', type=str, default=None,
                        help='API Key（默认读环境变量 API_KEY）')
    parser.add_argument('--base_url', type=str, default=os.getenv("API_BASE", "https://api.siliconflow.cn/v1/"),
                        help='OpenAI 兼容端点（默认读环境变量 API_BASE）')
    parser.add_argument('--task', type=str, default=DEFAULT_TASK, help='演示任务描述')
    args = parser.parse_args()
    args.api_key = args.api_key or os.getenv("API_KEY")
    if not args.api_key:
        sys.exit("缺少 API Key：设置环境变量 API_KEY，或通过 --api_key 传入")

    print(f"{GRAY}任务：{args.task}\n{'=' * 60}{RESET}")
    agent = build_agent(args)
    run(agent, args.task)
    print(f"\n{GRAY}{'=' * 60}{RESET}")
    print(f"{GRAY}产物检查：report.md / output/report.xlsx（位于本目录下）{RESET}")


if __name__ == "__main__":
    main()
