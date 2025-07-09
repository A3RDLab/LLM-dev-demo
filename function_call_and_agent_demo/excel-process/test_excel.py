import pandas as pd

# 读取Excel文件
df = pd.read_excel('temp_2023年8月-9月销售记录的副本.xlsx')

# 显示前几行数据
print("\n===== Excel数据前5行 =====")
print(df.head())

# 显示列名
print("\n===== 列名列表 =====")
print(df.columns.tolist())