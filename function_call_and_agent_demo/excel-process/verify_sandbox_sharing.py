"""
回归验证脚本：模拟 app.py 修复后的完整沙箱流程。

流程（与 app.py 一致）：
    1. copy_file_to_sandbox：完整文件路径 + keep_template + commit_container
    2. run_code：新的独立会话中读取该 Excel 并做简单分析

历史 bug 记录（均已实测确认并修复）：
    - copy_to_runtime 传目录路径 → 文件解压到错误位置
    - 会话关闭即销毁容器，keep_template 只保留镜像 → 跨会话文件丢失
    - 新版 llm-sandbox 的 .text 已废弃 → 改用 .stdout
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import copy_file_to_sandbox, run_code

EXCEL_SRC = "/Users/limingyu/Code/LI-Mingyu/LLM-dev-demo/2023年8月-9月销售记录.xlsx"
SANDBOX_FILE = "/sandbox/2023年8月-9月销售记录.xlsx"

print("=== 步骤1：上传阶段复制 Excel 到沙箱（独立会话） ===")
print(copy_file_to_sandbox(EXCEL_SRC, SANDBOX_FILE))

print("\n=== 步骤2：run_code 新会话中读取并分析（独立会话） ===")
analysis_code = f"""
import pandas as pd
import os
assert os.path.exists('{SANDBOX_FILE}'), '文件在跨会话后丢失！'
df = pd.read_excel('{SANDBOX_FILE}')
print('读取成功, 形状:', df.shape)
print('列名:', list(df.columns))
"""
result = run_code("python", analysis_code, ["pandas", "openpyxl"])
print(result)

if "读取成功" in result:
    print("\n✅ 验证通过：跨会话文件共享正常，app.py 修复有效")
else:
    print("\n❌ 验证失败")
    sys.exit(1)
