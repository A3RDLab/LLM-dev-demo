# Excel数据分析助手

这是一个基于Streamlit的Excel数据分析应用，它可以帮助用户上传Excel文件并根据自然语言描述的需求自动生成并执行数据分析代码。

## 功能特点

- 上传Excel文件并预览数据
- 使用自然语言描述分析需求
- 自动生成Python分析代码
- 在安全的沙箱环境中执行代码
- 展示分析结果和可视化

## 安装指南

前置条件：本机需安装并启动 **Docker**（llm-sandbox 基于 Docker 容器执行生成的代码）。

1. 克隆仓库到本地

2. 安装依赖
   ```
   pip install -r requirements.txt
   ```

3. 配置API密钥
   - 复制`.env.example`文件并重命名为`.env`
   - 在`.env`文件中填入你的 API Key 和 Base URL（任何 OpenAI 兼容接口均可，如硅基流动、阿里云百炼、DeepSeek）
   - 可选：通过 `MODEL` 变量指定模型（默认 `Pro/deepseek-ai/DeepSeek-V3`）

4. 运行应用
   ```
   streamlit run app.py
   ```

## 使用方法

1. 上传Excel文件（支持.xlsx和.xls格式）
2. 在文本框中输入您的数据分析需求，例如：
   - "分析销售数据的月度趋势并生成折线图"
   - "计算每个产品类别的销售总额并按降序排列"
   - "找出销售额最高的前10个客户并分析他们的购买模式"
3. 点击"开始分析"按钮
4. 查看分析结果和生成的代码

## 技术栈

- Streamlit: 用于构建Web界面
- Pandas: 用于数据处理和分析
- OpenAI 兼容 API + 原生 function calling: 理解需求、生成代码并驱动工具调用循环
- llm-sandbox: 基于 Docker 的安全沙箱，执行生成的代码

## 注意事项

- 请确保您的Excel文件格式正确，且不包含敏感信息
- 分析过程可能需要一些时间，特别是对于大型数据集
- 生成的代码会在安全的沙箱环境中执行，不会影响您的本地环境

## 沙箱机制说明（实测踩过的坑）

llm-sandbox 每个 `SandboxSession` 是独立的 Docker 容器，会话关闭即销毁。因此：

1. **跨会话共享文件**需同时满足：`copy_to_runtime` 传【完整文件路径】（传目录会解压到错误位置） + `keep_template=True, commit_container=True`（把容器状态提交进模板镜像，后续会话才能继承文件）；
2. 每次上传新文件都会 commit 一次镜像，长期运行会产生历史镜像，可定期 `docker image prune` 清理；
3. `verify_sandbox_sharing.py` 是针对上述机制的回归验证脚本，修改沙箱相关代码后建议先跑一遍。