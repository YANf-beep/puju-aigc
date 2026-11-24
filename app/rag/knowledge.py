"""轻量RAG检索：jieba 分词 + TF-IDF + 余弦相似度（对应开题报告模块2「检索增强生成」）。

设计说明：
- 知识条目存于 data/knowledge/puju_knowledge.json，随素材库持续扩充；
- 当前为纯Python关键词检索实现，CPU零成本、无外部依赖；
- 升级路径（工程优化方向，可写入论文）：换用 sentence-transformers 的
  bge-small-zh-v1.5 语义向量（CPU可跑，国内镜像 hf-mirror.com 下载），
  再进一步可接入向量数据库。接口 retrieve()/format_snippets() 保持不变。
"""
from __future__ import annotations

import json
import math
from collections import Counter
from typing import Any

import jieba

from .. import config

_STOP_WORDS = set(
    "的了和与及或在是对于为有其之不是等中并将被让给从而之以者".split()
    + ["什么", "哪些", "怎么", "如何", "介绍", "关于", "请问"]
)


def _tokenize(text: str) -> list[str]:
    return [
        t
        for t in jieba.lcut(text)
        if t.strip() and t not in _STOP_WORDS and not t.isspace()
    ]


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    common = set(a) & set(b)
    dot = sum(a[t] * b[t] for t in common)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


class TfidfRetriever:
    """极简TF-IDF检索器（数据量在千条级以内完全够用）。"""

    def __init__(self, entries: list[dict[str, Any]]):
        self.entries = entries
        self.doc_tokens = [
            _tokenize(f"{e.get('title', '')} {e.get('text', '')}") for e in entries
        ]
        n = len(entries) or 1
        df: Counter[str] = Counter()
        for toks in self.doc_tokens:
            df.update(set(toks))
        self.idf = {t: math.log((n + 1) / (c + 1)) + 1.0 for t, c in df.items()}
        self.doc_vecs = [self._vec(toks) for toks in self.doc_tokens]

    def _vec(self, toks: list[str]) -> dict[str, float]:
        tf = Counter(toks)
        total = len(toks) or 1
        return {t: (c / total) * self.idf.get(t, 1.0) for t, c in tf.items()}

    def retrieve(self, query: str, k: int = 3) -> list[dict[str, Any]]:
        qv = self._vec(_tokenize(query))
        scored = [
            (score, i) for i, score in enumerate(_cosine(qv, dv) for dv in self.doc_vecs)
        ]
        scored.sort(reverse=True)
        hits = []
        for score, i in scored[:k]:
            if score <= 0:
                break
            e = self.entries[i]
            hits.append({"title": e.get("title", ""), "text": e.get("text", ""), "score": round(score, 4)})
        return hits


_retriever: TfidfRetriever | None = None


def _get_retriever() -> TfidfRetriever:
    global _retriever
    if _retriever is None:
        entries = json.loads(config.KNOWLEDGE_FILE.read_text(encoding="utf-8"))
        _retriever = TfidfRetriever(entries)
    return _retriever


def retrieve(query: str, k: int = 3) -> list[dict[str, Any]]:
    """检索与 query 最相关的 k 条领域知识。"""
    return _get_retriever().retrieve(query, k)


def format_snippets(hits: list[dict[str, Any]]) -> list[str]:
    """把检索结果整理为可注入提示词的文本片段。"""
    return [f"{h['title']}：{h['text']}" for h in hits]


def reload_knowledge() -> None:
    """知识文件更新后重新加载（开发调试用）。"""
    global _retriever
    _retriever = None
