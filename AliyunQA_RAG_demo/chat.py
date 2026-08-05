import numpy as np
import streamlit as st
import tiktoken
from openai import OpenAI  
import logging
from redis import Redis
from redis.commands.search.query import Query
import os
from datetime import date, datetime, timedelta
import json

# Rerank：用专用重排模型对粗召回结果精排，是当前 RAG 的标准实践
from dashscope import TextReRank

# Define a function to get the session id and the remote ip 
# Caution: this function is implemented in a hacky way and may break in the future
from streamlit import runtime
from streamlit.runtime.scriptrunner import get_script_run_ctx

LLM = "qwen-max"
VECTOR_DIM = 1024
DISTANCE_METRIC = "COSINE"  
INDEX_NAME = "AliyunQA"
RETRIEVE_TOP_K = 10   # 向量粗召回条数
RERANK_TOP_N = 2      # rerank 后保留的精排条数
RERANK_MODEL = "gte-rerank-v2"

client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),  # 环境变量名称变更
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

# Helper functions
def json_gpt(input: str):
    completion = client.chat.completions.create(  # 使用客户端实例
        model=LLM,
        messages=[
            {"role": "system", "content": "Output only valid JSON"},
            {"role": "user", "content": input},
        ],
        temperature=0.2,
    )
    text = completion.choices[0].message.content
    parsed = json.loads(text)

    return parsed


def rerank(query: str, docs: list):
    """用 gte-rerank 对粗召回的文档按与 query 的相关性精排，返回按分数降序的文档列表"""
    resp = TextReRank.call(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        model=RERANK_MODEL,
        query=query,
        documents=[d.md for d in docs],
        top_n=RERANK_TOP_N,
        return_documents=True,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Rerank failed: {resp.code} {resp.message}")
    # results 已按 relevance_score 降序，映射回原始 redis doc 以保留 url 等字段
    ranked = []
    for item in resp.output.results:
        ranked.append((docs[item.index], item.relevance_score))
    return ranked


# The streamlit script starts here
logging.info("Starting Streamlit script ...")

# Prepare to connect to Redis
redis_host = os.getenv('REDIS_HOST', 'localhost')  # default to 'localhost' if not set
redis_port = os.getenv('REDIS_PORT', '6379')  # default to '6379' if not set
redis_db = os.getenv('REDIS_DB', '0')  # default to '0' if not set. RediSearch only operates on the default (0) db
 # Instantiates a Redis client. decode_responses=False to avoid decoding the returned embedding vectors
r = Redis(host=redis_host, port=redis_port, db=redis_db, decode_responses=False)


st.set_page_config(
    page_title="阿里云运维助手",
    page_icon="🤖",
)
st.subheader("阿里云运维助手")

if "messages" not in st.session_state.keys():
    # Initialize the session_state.messages
    st.session_state.messages = [{"role": "system", "content": "你是一个阿里云运维助手。"}]
else: # Since streamlit script is executed every time a widget is changed, this "else" is not necessary, but improves readability
    # Display chat messages
    for message in st.session_state.messages:
        if message["role"] == "user" or message["role"] == "assistant":
            with st.chat_message(message["role"]):
                st.write(message["content"])

# User-provided prompt
if user_prompt := st.chat_input('在此输入您的问题'):
    logging.info(f"User's prompt: {user_prompt}")
    with st.chat_message("user"):
        st.write(user_prompt)
        st.session_state.messages.append({"role": "user", "content": user_prompt})
    with st.chat_message("assistant"):
        with st.spinner("人工智能正在思考..."):
            QUERY_GEN_PROMPT = f"""
You are an Aliyun operations assistant
You have access to a search API that returns troubleshooting articles.
Generate search query extracting key words from the user's question.

User question: {user_prompt}

Format: {{"searchQuery": "search query"}}"""
            query_str = json_gpt(QUERY_GEN_PROMPT)["searchQuery"]
            logging.info(f"Generated query: {query_str}")
            try:
                query_embedding = client.embeddings.create(input=query_str, model="text-embedding-v3", dimensions=1024, encoding_format="float")
                query_vec = np.array(query_embedding.data[0].embedding, dtype=np.float32).tobytes()
                # 第一步：向量粗召回 Top-K
                query_base = (Query(f"*=>[KNN {RETRIEVE_TOP_K} @md_embedding $vec as score]").sort_by("score").return_fields("score", "url", "md").dialect(2))
                query_param = {"vec": query_vec}
                candidates = r.ft(INDEX_NAME).search(query_base, query_param).docs
                # 第二步：rerank 精排，取 Top-N
                ranked_results = rerank(query_str, candidates)
                query_results = [doc for doc, _ in ranked_results]
                result_md = "\n\n".join(doc.md for doc in query_results)
            except Exception as e:
                logging.error(f"Error querying Reids with embedding: {e}")
                st.error("无法搜索答案，这很可能是系统故障导致，请联系我的主人。")
                st.stop()
            logging.info(f"Search results: {[(f'({score:.3f})' + doc.md[:20]).replace(chr(10), '') for doc, score in ranked_results]}...")
            st.session_state.messages.append({"role": "user", "content": f"""请根据搜索结果回答user在前面遇到的问题。注意，请务必首先依赖搜索结果，而不是你自己已有的知识。如果搜索结果中包含了具体操作步骤，也请据此给用户具体操作指引。
搜索结果：\n{result_md}"""})
            test_messages = st.session_state.messages.copy()
            try:
                # 流式响应处理
                llm_response = client.chat.completions.create(
                    model=LLM,
                    messages=st.session_state.messages,
                    temperature=0.5,
                    stream=True
                )
                resp_display = st.empty()
                collected_resp_content = ""
                for chunk in llm_response:
                    if chunk.choices[0].finish_reason is None:  
                        content = chunk.choices[0].delta.content 
                        if content:
                            collected_resp_content += content
                            resp_display.write(collected_resp_content)

            # 修改6: 错误处理适配
            except Exception as e:
                logging.error(f"阿里云API错误: {e}")
                st.error('服务暂时不可用，请稍后重试或联系管理员')
                st.stop()
            logging.info(f"AI's response: {collected_resp_content[:50]}".replace("\n", "") + "..." + f"{collected_resp_content[-50:]}".replace("\n", ""))

    # Add the generated msg to session state
    st.session_state.messages[-1] = {"role": "assistant", "content": collected_resp_content}
    st.write("\n参考文档：\n\n" + "\n\n".join(doc.url for doc in query_results))

st.write("**注意：人工智能生成内容仅供参考。**")
logging.info("Streamlit script ended.")