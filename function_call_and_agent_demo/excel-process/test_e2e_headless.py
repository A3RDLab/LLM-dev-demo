"""
端到端无头测试：验证 app.py 核心 agent 链路（不经过 Streamlit UI）。

流程与真实使用一致：
    1. copy_file_to_sandbox：上传阶段把 Excel 复制进沙箱（commit_container 持久化）
    2. run_agent：LLM 决策 → run_code 沙箱执行 → 结果回填 → 最终回答
任务设计为需要真实代码执行（统计聚合 + 作图 + 文件拷回），
覆盖 function calling 循环、沙箱执行、跨会话文件共享三条链路。

运行（需要 Docker + excel-process 依赖）：
    cd function_call_and_agent_demo/excel-process
    ../../.venv-excel/bin/python test_e2e_headless.py
"""
import os
import sys
import glob

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import run_agent, copy_file_to_sandbox

EXCEL_SRC = "/Users/limingyu/Code/LI-Mingyu/LLM-dev-demo/2023年8月-9月销售记录.xlsx"
SANDBOX_FILE = "/sandbox/2023年8月-9月销售记录.xlsx"
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_PNG = os.path.join(OUT_DIR, "e2e_top_categories.png")

# 清理历史产物，确保验证的是本次运行生成的文件
if os.path.exists(OUT_PNG):
    os.remove(OUT_PNG)

print("=== 步骤1：上传 Excel 到沙箱（跨会话持久化）===")
print(copy_file_to_sandbox(EXCEL_SRC, SANDBOX_FILE))

print("\n=== 步骤2：run_agent 执行分析任务 ===")
task = f"""Excel 文件已在沙箱中，路径为 {SANDBOX_FILE}。
请完成：
1. 统计每个"品类"的销售总额（销售额 = 单价 × 销售量）；
2. 把结果保存为柱状图（图中文字用英文），存到沙箱 /sandbox/e2e_top_categories.png，
   然后用 copy_file_from_sandbox 工具拷回本地，local_path 直接填短文件名
   e2e_top_categories.png 即可；
3. 最后用文字总结哪个品类销售额最高。"""

run_agent(task)

print("\n=== 步骤3：校验产物 ===")
if os.path.exists(OUT_PNG) and os.path.getsize(OUT_PNG) > 1000:
    print(f"✅ 图片已生成: {OUT_PNG} ({os.path.getsize(OUT_PNG)} bytes)")
else:
    print(f"❌ 图片未生成或过小: {OUT_PNG}")
    sys.exit(1)
