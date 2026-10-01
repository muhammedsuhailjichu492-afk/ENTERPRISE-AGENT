"""
RAG Agent — retrieves relevant organizational policy/SOP context from the
vector DB so the Decision Agent grounds its recommendations in actual
company procedure instead of generic advice.
"""
from app import vector_store


class RAGAgent:
    name = "rag_agent"

    def retrieve(self, query: str, domain: str, k: int = 3) -> dict:
        # Try domain-scoped retrieval first, then fall back to a global search
        # so the agent still surfaces something useful for cross-domain questions.
        hits = vector_store.query(query, domain=domain, k=k)
        if not hits:
            hits = vector_store.query(query, domain=None, k=k)

        return {
            "query": query,
            "domain": domain,
            "results": hits,
        }
