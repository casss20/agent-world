"""
Vector Memory
Semantic memory with embeddings and similarity search.

Adapted from Ruflo pattern: HybridBackend vector store + semantic search.
Requires: pgvector extension in PostgreSQL, sentence-transformers or openai embeddings.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, desc

logger = logging.getLogger(__name__)


class VectorMemory:
    """
    Semantic memory storage using PostgreSQL pgvector.
    - Store text with vector embeddings
    - Similarity search using cosine distance
    - Namespace isolation per room/agent
    """

    def __init__(self, embedding_dim: int = 1536):
        self.embedding_dim = embedding_dim
        self._embedding_fn = None

    def set_embedder(self, embed_fn: Any) -> None:
        """Set the embedding function (e.g., OpenAI, sentence-transformers)."""
        self._embedding_fn = embed_fn

    async def _ensure_extension(self, db: AsyncSession) -> None:
        """Ensure pgvector extension is installed."""
        try:
            await db.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await db.execute(text(f"""
                CREATE TABLE IF NOT EXISTS vector_memory (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    namespace VARCHAR(255) NOT NULL,
                    content TEXT NOT NULL,
                    embedding vector({self.embedding_dim}),
                    metadata JSONB DEFAULT '{{}}',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """))
            await db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_vector_memory_embedding
                ON vector_memory USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
            """))
            await db.commit()
        except Exception as e:
            logger.warning("pgvector setup warning: %s", e)

    async def store(
        self,
        db: AsyncSession,
        namespace: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Store content with embedding in vector memory."""
        await self._ensure_extension(db)

        embedding = await self._embed(content)

        mem_id = str(uuid.uuid4())
        await db.execute(
            text("""
                INSERT INTO vector_memory (id, namespace, content, embedding, metadata)
                VALUES (:id, :namespace, :content, :embedding, :metadata)
            """),
            {
                "id": mem_id,
                "namespace": namespace,
                "content": content,
                "embedding": str(embedding),
                "metadata": json.dumps(metadata or {}),
            },
        )
        await db.commit()
        return mem_id

    async def search(
        self,
        db: AsyncSession,
        namespace: str,
        query: str,
        top_k: int = 5,
        min_similarity: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """Semantic search within a namespace."""
        await self._ensure_extension(db)

        query_embedding = await self._embed(query)

        result = await db.execute(
            text("""
                SELECT id, content, metadata,
                       1 - (embedding <=> :query_embedding) as similarity
                FROM vector_memory
                WHERE namespace = :namespace
                ORDER BY embedding <=> :query_embedding
                LIMIT :top_k
            """),
            {
                "query_embedding": str(query_embedding),
                "namespace": namespace,
                "top_k": top_k,
            },
        )

        rows = result.fetchall()
        return [
            {
                "id": row.id,
                "content": row.content,
                "similarity": row.similarity,
                "metadata": row.metadata,
            }
            for row in rows
            if row.similarity >= min_similarity
        ]

    async def delete_namespace(
        self, db: AsyncSession, namespace: str
    ) -> int:
        """Delete all memories in a namespace."""
        result = await db.execute(
            text("DELETE FROM vector_memory WHERE namespace = :namespace"),
            {"namespace": namespace},
        )
        await db.commit()
        return result.rowcount

    async def _embed(self, text: str) -> List[float]:
        """Generate embedding for text."""
        if self._embedding_fn:
            return await self._embedding_fn(text)

        # Fallback: simple hash-based pseudo-embedding (NOT for production)
        import hashlib
        h = hashlib.sha256(text.encode()).digest()
        # Expand to embedding_dim using repeated hashing
        vec = []
        for i in range(self.embedding_dim):
            vec.append(((h[i % 32] + i * 7) % 255) / 255.0 - 0.5)
        return vec


# ── Global Instance ─────────────────────────────────────────────────────────
vector_memory = VectorMemory()
