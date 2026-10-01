"""
Vector DB layer (ChromaDB, local persistent client, bundled ONNX MiniLM
embedding function — no external embedding API key required).

This is the "Vector DB" component of the architecture: the RAG Agent queries
it, the Supervisor seeds it once at startup from app/knowledge_base.
"""
from app.config import settings

_collection = None


def _get_collection():
    global _collection
    if _collection is not None:
        return _collection

    import chromadb

    client = chromadb.PersistentClient(path=settings.CHROMA_PATH)
    _collection = client.get_or_create_collection(
        name="enterprise_knowledge_base",
        metadata={"hnsw:space": "cosine"},
    )
    return _collection


def seed_if_empty() -> None:
    from app.knowledge_base.sample_docs import DOCUMENTS

    collection = _get_collection()
    if collection.count() > 0:
        return

    collection.add(
        ids=[d["id"] for d in DOCUMENTS],
        documents=[d["text"] for d in DOCUMENTS],
        metadatas=[{"domain": d["domain"], "title": d["title"]} for d in DOCUMENTS],
    )


def query(text: str, domain: str | None = None, k: int = 3) -> list[dict]:
    collection = _get_collection()
    where = {"domain": domain} if domain else None
    result = collection.query(query_texts=[text], n_results=k, where=where)

    hits = []
    ids = result.get("ids", [[]])[0]
    docs = result.get("documents", [[]])[0]
    metas = result.get("metadatas", [[]])[0]
    dists = result.get("distances", [[]])[0]
    for i in range(len(ids)):
        hits.append({
            "id": ids[i],
            "title": metas[i].get("title", ""),
            "domain": metas[i].get("domain", ""),
            "text": docs[i],
            "relevance": round(1 - dists[i], 4) if dists else None,
        })
    return hits
