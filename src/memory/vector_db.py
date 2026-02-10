"""向量库：Chroma 实现，用于长期记忆与检索。痛点文本存 Embedding，Clusterer 阶段语义检索增强。"""

from __future__ import annotations

from typing import Any

from src.utils.logger import get_logger

logger = get_logger(__name__)

PAIN_MEMORY_COLLECTION = "pain_memory"


def get_vector_store(persist_dir: str | None = None, **kwargs: Any) -> Any:
    """返回 Chroma 持久化客户端。未安装 chromadb 时返回 None。"""
    try:
        import chromadb
        from pathlib import Path
        path = persist_dir or "./data/chroma"
        Path(path).mkdir(parents=True, exist_ok=True)
        return chromadb.PersistentClient(path=path, **kwargs)
    except ImportError:
        return None


def _openai_embedding_function():
    """Chroma 使用 OpenAI text-embedding-3-small（需 OPENAI_API_KEY）。"""
    try:
        from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
        return OpenAIEmbeddingFunction(
            model_name="text-embedding-3-small",
            api_key_env_var="OPENAI_API_KEY",
        )
    except Exception as e:
        logger.warning("OpenAI embedding for Chroma not available: %s", e)
        return None


def get_pain_collection(store: Any, embedding_function: Any = None):
    """获取或创建 pain_memory 集合（存痛点文本的 embedding）。"""
    if store is None:
        return None
    try:
        emb = embedding_function or _openai_embedding_function()
        if emb is None:
            coll = store.get_or_create_collection(
                PAIN_MEMORY_COLLECTION,
                metadata={"description": "pain point long-term memory"},
            )
        else:
            coll = store.get_or_create_collection(
                PAIN_MEMORY_COLLECTION,
                embedding_function=emb,
                metadata={"description": "pain point long-term memory"},
            )
        return coll
    except Exception as e:
        logger.warning("get_pain_collection failed: %s", e)
        return None


def add_pain_texts(
    store: Any,
    ids: list[str],
    documents: list[str],
    metadatas: list[dict] | None = None,
) -> None:
    """将痛点文本写入向量库（由 collection 的 embedding_function 负责嵌入）。"""
    if not store or not ids or not documents:
        return
    coll = get_pain_collection(store)
    if coll is None:
        return
    try:
        meta = metadatas if metadatas is not None else [{}] * len(ids)
        coll.add(ids=ids, documents=documents, metadatas=meta)
        logger.info("Vector DB: added %d pain texts to %s", len(ids), PAIN_MEMORY_COLLECTION)
    except Exception as e:
        logger.warning("add_pain_texts failed: %s", e)


def query_similar_pains(
    store: Any,
    query_text: str,
    n_results: int = 10,
    topic_filter: str | None = None,
) -> list[dict]:
    """语义检索：返回与 query_text 相似的痛点文档，用于 Clusterer 检索增强。"""
    if store is None or not query_text.strip():
        return []
    coll = get_pain_collection(store)
    if coll is None:
        return []
    try:
        where = {"topic": topic_filter} if topic_filter else None
        res = coll.query(query_texts=[query_text.strip()], n_results=n_results, where=where)
        out: list[dict] = []
        if res and res.get("documents"):
            for i, doc in enumerate((res["documents"] or [[]])[0] or []):
                meta = (res.get("metadatas") or [[]])[0]
                out.append({"document": doc, "metadata": meta[i] if i < len(meta) else {}})
        return out
    except Exception as e:
        logger.warning("query_similar_pains failed: %s", e)
        return []


def add_documents(store: Any, ids: list[str], documents: list[str], metadatas: list[dict] | None = None) -> None:
    """向默认 oracle_memory 集合写入文档（兼容旧接口）。"""
    if store is None:
        return
    try:
        coll = store.get_or_create_collection("oracle_memory", metadata={"description": "oracle run memory"})
        coll.add(ids=ids, documents=documents, metadatas=metadatas or [{}] * len(ids))
    except Exception as e:
        logger.warning("add_documents failed: %s", e)


def query(store: Any, query_text: str, n_results: int = 5) -> list[dict]:
    """语义检索（默认集合）。"""
    if store is None:
        return []
    try:
        coll = store.get_or_create_collection("oracle_memory", metadata={"description": "oracle run memory"})
        res = coll.query(query_texts=[query_text], n_results=n_results)
        out: list[dict] = []
        if res and res.get("documents"):
            for i, doc in enumerate((res["documents"] or [[]])[0] or []):
                meta = (res.get("metadatas") or [[]])[0]
                out.append({"document": doc, "metadata": meta[i] if i < len(meta) else {}})
        return out
    except Exception as e:
        logger.warning("query failed: %s", e)
        return []
