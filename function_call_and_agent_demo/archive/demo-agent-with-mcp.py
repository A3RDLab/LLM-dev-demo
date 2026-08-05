import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage  # 添加SystemMessage导入
from langchain_openai import ChatOpenAI
import os

api_key = os.getenv("API_KEY")
if not api_key:
    raise ValueError("API_KEY environment variable is required")

model = ChatOpenAI(model="Pro/deepseek-ai/DeepSeek-V3", api_key=api_key, base_url="https://api.siliconflow.cn/v1/", temperature=0.5)

server_params = StdioServerParameters(
    command="npx",
    args=["@modelcontextprotocol/server-github"],
)

# --- Helper function to format and print a single message ---
def print_message_formatted(msg, step_number):
    print(f"\n--- Step {step_number}: {type(msg).__name__} ---")

    # 打印消息内容 (对ToolMessage尝试美化JSON输出)
    if hasattr(msg, 'content'):
        content_to_print = msg.content
        if isinstance(msg, ToolMessage):
            try:
                parsed_json = json.loads(content_to_print)
                content_to_print = json.dumps(parsed_json, indent=2, ensure_ascii=False)
            except json.JSONDecodeError:
                pass # 非JSON则保持原样
        print(content_to_print)

    # 如果是 AIMessage，额外显示是否有工具调用
    if isinstance(msg, AIMessage):
        if msg.tool_calls:
            print("\nTool Calls:")
            for tool_call in msg.tool_calls:
                print(f"  - Function: {tool_call['name']}")
                try:
                    args_json = json.loads(tool_call['args'])
                    args_str = json.dumps(args_json, indent=4, ensure_ascii=False)
                except:
                    args_str = str(tool_call['args'])
                print(f"    Args: {args_str}")
                print(f"    ID: {tool_call['id']}")
                print()  # 添加空行分隔多个工具调用
        # 检查是否可能是最终答案 (没有新的工具调用)
        # elif msg.content:  # 只有当有内容时才显示
        #     print("\n[Intermediate/Final Answer forming...]")

    # 如果是 ToolMessage，显示它对应的 tool_call_id
    if isinstance(msg, ToolMessage):
         print(f"\n(Result for tool_call_id: {msg.tool_call_id})")
# --- End of Helper function ---


async def main():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()

            # Get tools
            tools = await load_mcp_tools(session)

            # Create the agent
            agent = create_react_agent(model, tools)
            initial_input = {
                "messages": [
                    SystemMessage(content="""你是一个专业的GitHub项目分析助手，擅长使用GitHub API工具。重要提示：
1. 当需要查看仓库目录结构时，可以使用get_file_contents工具，将path参数设为目录路径(以/结尾)
2. 获取文件内容时，确保path参数指向具体文件路径
3. 分析项目时，建议先查看根目录结构，再根据需要深入特定目录
4. 对于开源项目，优先查看README.md、docs/目录和主要源代码目录"""), # 添加system message
                    # HumanMessage(content="分析https://github.com/shadow1ng/fscan，查看相关源码，告诉我redis系统反弹shell相关的代码在哪里，并解释这些代码的含义。")
                    HumanMessage(content="https://github.com/LI-Mingyu/cndevtutorial 中 GRAPE-operator 是如何实现 TTL 的？")
                ]
            }

            print("Agent is starting stream, output will appear step-by-step...")
            print("\n=== Agent Execution Steps ===")

            step_counter = 0 # 使用简单的步骤计数器
            final_answer_content = None # 用于存储最终答案

            # Use astream() to get intermediate results
            async for chunk in agent.astream(initial_input):
                # --- Optional Debug Print ---
                # print("\n<<< RAW CHUNK START >>>")
                # print(chunk)
                # print("<<< RAW CHUNK END >>>\n")
                # --- End Debug Print ---

                messages_in_chunk = [] # 存储当前 chunk 中需要打印的消息

                if isinstance(chunk, dict):
                    # 检查常见的包含消息的键
                    for key in ['agent', 'tools']: # LangGraph 常用的键
                        if key in chunk and isinstance(chunk[key], dict) and "messages" in chunk[key]:
                            potential_messages = chunk[key]["messages"]
                            # 确保 messages 是一个列表
                            if isinstance(potential_messages, list):
                                messages_in_chunk.extend(potential_messages)
                                break # 找到当前 chunk 的消息，停止检查其他键

                # 打印当前 chunk 找到的消息
                if messages_in_chunk:
                    for msg in messages_in_chunk:
                        step_counter += 1
                        print_message_formatted(msg, step_counter) # 传递递增的步骤号

                        # # 尝试捕获最终答案（AIMessage 且无工具调用）
                        # if isinstance(msg, AIMessage) and not msg.tool_calls and msg.content:
                        #     final_answer_content = msg.content # 更新潜在的最终答案
                # else:
                    # print("[DEBUG] No relevant messages found in this chunk's structure.") # 可选调试信息


            # print("\n=== End of Stream ===")
            # # 在流结束后，打印捕获到的最终答案（如果有）
            # if final_answer_content:
            #     print("\n=== FINAL ANSWER ===")
            #     print(final_answer_content)
            # else:
            #     # 如果上面的逻辑没捕获到，可能最终答案在流的最后一个 AIMessage 中
            #     print("\n[Check the last AIMessage above without tool calls for the final answer]")

# Run the async function
if __name__ == "__main__":
    asyncio.run(main())