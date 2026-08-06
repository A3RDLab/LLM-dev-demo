"""
Mini RAG 示例：检索增强生成全链路
====================================
用一个自包含脚本演示生产级 RAG 的完整管线（无需 Redis/向量数据库）：

    文档 → 清洗 → 切块(chunking) → embedding 向量化 → 余弦相似度检索 Top-K
         → 拼装上下文 → LLM 生成答案

语料：AliyunQA_RAG_demo/scrapy-prj-aliyunecs/qa.json（335 条阿里云 ECS 运维文档）
向量化：qwen3.7-text-embedding（云端，索引缓存到本地 .npz 避免重复计费）
生成：环境变量 MODEL（默认 qwen3.6-27b）

用法：
    python mini_rag_demo.py                          # 交互模式
    python mini_rag_demo.py --query "ECS 无法连接怎么办" --top_k 3
    python mini_rag_demo.py --rebuild                # 强制重建索引
"""

import os
import re
import json
import html
import argparse
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from openai import OpenAI

# ===== 配置 =====
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# 加载项目根目录 .env（API_KEY / API_BASE / MODEL / EMBED_MODEL，见 .env.example）
load_dotenv(Path(SCRIPT_DIR) / ".env")
CORPUS_PATH = os.path.join(SCRIPT_DIR, "AliyunQA_RAG_demo", "scrapy-prj-aliyunecs", "qa.json")
INDEX_PATH = os.path.join(SCRIPT_DIR, "rag_index.npz")
META_PATH = os.path.join(SCRIPT_DIR, "rag_index_meta.json")

# 终端颜色：过程信息（索引/检索/状态提示）灰色，最终回答用终端默认色
GRAY = "\033[90m"
RESET = "\033[0m"

EMBED_MODEL = os.getenv("EMBED_MODEL", "qwen3.7-text-embedding")
CHUNK_SIZE = 800      # 每块目标字符数
CHUNK_OVERLAP = 100   # 相邻块重叠字符数，避免语义被切断
EMBED_BATCH = 20      # embedding 批量大小

parser = argparse.ArgumentParser(description='Mini RAG 示例')
parser.add_argument('--query', type=str, default=None, help='单次提问（不传则进入交互模式）')
parser.add_argument('--top_k', type=int, default=3, help='检索返回的块数')
parser.add_argument('--rebuild', action='store_true', help='强制重建索引')
parser.add_argument('--model', type=str, default=os.getenv("MODEL", "qwen3.6-27b"),
                    help='生成模型（默认读环境变量 MODEL）')
parser.add_argument('--api_key', type=str, default=None,
                    help='API密钥（默认使用环境变量API_KEY）')
parser.add_argument('--base_url', type=str, default=os.getenv("API_BASE", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
                    help='API基础URL（默认读环境变量 API_BASE）')
args = parser.parse_args()

api_key = args.api_key if args.api_key else os.getenv("API_KEY")

client = OpenAI(api_key=api_key, base_url=args.base_url)


# ===== 1. 文档清洗与切块 =====
def clean_html(raw: str) -> str:
    """去掉 HTML 标签与实体，保留纯文本"""
    text = re.sub(r'<[^>]+>', ' ', raw)
    text = html.unescape(text)
    return re.sub(r'\s+', ' ', text).strip()


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP):
    """滑动窗口切块：按句号优先断句，凑够 size 左右出一块"""
    sentences = re.split(r'(?<=。)|(?<=！)|(?<=？)', text)
    chunks, buf = [], ""
    for s in sentences:
        if len(buf) + len(s) > size and buf:
            chunks.append(buf)
            buf = buf[-overlap:] + s if overlap else s
        else:
            buf += s
    if buf.strip():
        chunks.append(buf)
    return [c for c in chunks if len(c.strip()) >= 50]  # 丢弃过短的碎片


def load_corpus():
    with open(CORPUS_PATH, encoding="utf-8") as f:
        docs = json.load(f)
    chunks, chunk_urls = [], []
    for doc in docs:
        text = clean_html(doc.get("content", ""))
        if not text:
            continue
        for c in chunk_text(text):
            chunks.append(c)
            chunk_urls.append(doc.get("url", ""))
    return chunks, chunk_urls


# ===== 2. 向量化与索引缓存 =====
def embed_texts(texts):
    """批量调用 embedding 接口"""
    vecs = []
    for i in range(0, len(texts), EMBED_BATCH):
        batch = texts[i:i + EMBED_BATCH]
        resp = client.embeddings.create(model=EMBED_MODEL, input=batch, encoding_format="float")
        vecs.extend([d.embedding for d in resp.data])
        print(f"{GRAY}  向量化进度: {min(i + EMBED_BATCH, len(texts))}/{len(texts)}{RESET}")
    return np.array(vecs, dtype=np.float32)


def build_index(force=False):
    if not force and os.path.exists(INDEX_PATH) and os.path.exists(META_PATH):
        data = np.load(INDEX_PATH)
        with open(META_PATH, encoding="utf-8") as f:
            meta = json.load(f)
        print(f"{GRAY}[索引] 从缓存加载: {len(meta['chunks'])} 块, 维度 {data['vecs'].shape[1]}{RESET}")
        return data["vecs"], meta["chunks"], meta["urls"]

    print(f"{GRAY}[索引] 缓存不存在，开始构建（语料: {os.path.basename(CORPUS_PATH)}）...{RESET}")
    chunks, urls = load_corpus()
    print(f"{GRAY}[索引] 清洗切块完成: {len(chunks)} 块，开始向量化（模型 {EMBED_MODEL}）...{RESET}")
    vecs = embed_texts(chunks)
    # L2 归一化，之后余弦相似度可用点积直接算
    vecs = vecs / np.linalg.norm(vecs, axis=1, keepdims=True)
    np.savez_compressed(INDEX_PATH, vecs=vecs)
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump({"chunks": chunks, "urls": urls, "embed_model": EMBED_MODEL}, f, ensure_ascii=False)
    print(f"{GRAY}[索引] 构建完成并已缓存: {INDEX_PATH}{RESET}")
    return vecs, chunks, urls


# ===== 3. 检索 =====
def retrieve(query: str, vecs, chunks, urls, top_k: int):
    q = client.embeddings.create(model=EMBED_MODEL, input=[query], encoding_format="float")
    qv = np.array(q.data[0].embedding, dtype=np.float32)
    qv = qv / np.linalg.norm(qv)
    scores = vecs @ qv  # 已归一化，点积即余弦相似度
    top_idx = np.argsort(scores)[::-1][:top_k]
    return [(chunks[i], urls[i], float(scores[i])) for i in top_idx]


# ===== 4. 生成 =====
SYSTEM_PROMPT = """你是一个阿里云运维助手。请严格依据【参考资料】回答用户问题：
- 资料中有答案时，给出具体操作步骤，并在末尾列出参考链接；
- 资料中没有答案时，明确说"资料中未找到相关内容"，不要编造。"""


def generate(query: str, hits) -> str:
    context = "\n\n".join(f"[资料{i + 1}]（相关度{score:.3f}）\n{chunk}" for i, (chunk, _, score) in enumerate(hits))
    # stream=True：回答逐 token 生成，边收边打印，避免长回答下干等完整响应
    stream = client.chat.completions.create(
        model=args.model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"【参考资料】\n{context}\n\n【用户问题】\n{query}"},
        ],
        temperature=0.3,
        max_tokens=1500,
        stream=True,
    )
    chunks = []
    for chunk in stream:
        delta = chunk.choices[0].delta.content if chunk.choices else None
        if delta:
            print(delta, end="", flush=True)
            chunks.append(delta)
    print()  # 流式输出结束后换行
    return "".join(chunks)


def answer(query: str, vecs, chunks, urls, top_k: int):
    hits = retrieve(query, vecs, chunks, urls, top_k)
    print(f"\n{GRAY}[检索结果]{RESET}")
    for i, (chunk, url, score) in enumerate(hits):
        print(f"{GRAY}  #{i + 1} 相关度 {score:.3f} | {chunk[:60]}... | {url[:70]}{RESET}")
    print(f"\n{GRAY}[生成回答]{RESET}")
    ans = generate(query, hits)  # 回答已在 generate 内流式打印
    return ans


# ===== 5. 主流程 =====
if __name__ == "__main__":
    vecs, chunks, urls = build_index(force=args.rebuild)

    if args.query:
        answer(args.query, vecs, chunks, urls, args.top_k)
    else:
        print(f"\n{GRAY}进入交互模式（输入问题提问，直接回车退出）{RESET}\n")
        while True:
            q = input("问题> ").strip()
            if not q:
                break
            answer(q, vecs, chunks, urls, args.top_k)
            print()
