# 数据集《2023年8月-9月销售记录.xlsx》的前几行如下：
# 品类	产品名	单价(元)	销售量	销售日期	供应商
# 手机	Xiaomi Mi 11	4999	20	2023/8/2	北京科技有限公司
# 耳机	Sony WH-1000XM4	2999	15	2023/8/3	上海音响有限公司
# 笔记本电脑	Lenovo ThinkPad X1	8999	10	2023/8/5	深圳创新科技有限公司
# 智能手表	Apple Watch Series 7	3299	25	2023/8/6	广州数码有限公司
# 平板电脑	Apple iPad Pro	7999	30	2023/8/7	天津通讯有限公司
# 分析销售总额前五的品类，以及每个品类的总销售额，用python代码实现

import pandas as pd
import matplotlib.pyplot as plt
# 读取Excel文件
df = pd.read_excel('../2023年8月-9月销售记录.xlsx')

df['销售额'] = df['单价(元)'] * df['销售量']

# 计算每个品类的总销售额
category_sales = df.groupby('品类')['销售额'].sum().reset_index()
# 按销售额排序并选择前5个品类
top_categories = category_sales.sort_values(by='销售额', ascending=False).head(5)
# 绘制柱状图
plt.figure(figsize=(10, 6))
plt.bar(top_categories['品类'], top_categories['销售额'], color='skyblue')
plt.xlabel('品类')
plt.ylabel('总销售额')
plt.title('销售总额前五的品类')
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()
# 输出结果
print(top_categories)

