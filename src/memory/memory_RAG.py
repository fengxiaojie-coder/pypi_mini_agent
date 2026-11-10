# src/memory/memory_rag.py
"""长期记忆 RAG：切块 + 向量检索 + 小量全量注入"""

from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

# 记忆条数 <= 这个值，全量注入；超过才走 RAG
RAG_THRESHOLD = 10

def split_md_to_chunks(text: str) -> list[dict]:
    """把 Markdown 的列表项切成 chunk，带章节名"""
    chunks = []
    current_section = ""
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("## "):
            current_section = stripped[3:].strip()
            continue
        if stripped.startswith("- "):
            content = stripped[2:].strip()
            if content:
                chunks.append({"section": current_section, "text": content})
    return chunks


class MemoryRAG:
    """长期记忆的向量检索"""

    def __init__(self, persist_dir: str = "memory/chroma_db"):
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(
            name="long_term_memory",
            embedding_function=SentenceTransformerEmbeddingFunction(
                model_name="BAAI/bge-small-zh-v1.5",
            ),
        )

        self._indexed_count = 0

    def index(self, memory_md: str, user_md: str):
        """把 MEMORY.md / USER.md 的列表项建索引（全量重建）"""
        chunks = (
            split_md_to_chunks(memory_md)
            + split_md_to_chunks(user_md)
        )

        if not chunks:
            return

        # 条数没变，不重建
        if len(chunks) == self._indexed_count and self.collection.count() > 0:
            return

        # 清空旧索引
        existing = self.collection.get()
        if existing["ids"]:
            self.collection.delete(ids=existing["ids"])

        self.collection.add(
            ids=[str(i) for i in range(len(chunks))],
            documents=[
                f"[{c['section']}] {c['text']}" for c in chunks
            ],
        )
        self._indexed_count = len(chunks)

    def retrieve(self, query: str, top_k: int = 5, max_distance: float = 0.7) -> str:
        """检索 top_k 相关记忆，过滤掉距离过大的"""
        if self.collection.count() == 0:
            return ""

        results = self.collection.query(
            query_texts=[query],
            n_results=top_k,
            include=["documents", "distances"],   # ← 要 distances
        )

        docs = results.get("documents", [[]])[0]
        distances = results.get("distances", [[]])[0]

        if not docs:
            return ""

        print(f"[RAG 距离] query={query!r}")
        for doc, dist in zip(docs, distances):
            print(f"  {dist:.3f}  {doc[:60]}")

        # 过滤：距离小于阈值才保留
        filtered = [
            (doc, dist) for doc, dist in zip(docs, distances)
            if dist <= max_distance
        ]

        if not filtered:
            return ""

        return "\n".join(f"- {doc}" for doc, _ in filtered)