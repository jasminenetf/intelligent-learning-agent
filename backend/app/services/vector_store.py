"""ChromaDB vector store for course chunks."""

import logging
import os
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class VectorStoreService:
    """Wraps ChromaDB for upsert, search, and delete operations."""

    def __init__(
        self,
        persist_dir: str,
        collection_name: str,
        embedding_service: EmbeddingService,
    ):
        os.makedirs(persist_dir, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        self._embedding_service = embedding_service

    def upsert_chunks(self, chunks: list[dict]) -> dict:
        """Insert or update chunk vectors in ChromaDB. Chunk dict must have id/content/chunk_id/course_id/etc."""
        if not chunks:
            return {"indexed": 0}

        ids = []
        documents = []
        embeddings = []
        metadatas = []

        texts = [c["content"] for c in chunks]
        vecs = self._embedding_service.embed_texts(texts)

        for i, chunk in enumerate(chunks):
            cid = chunk.get("chunk_id", i)
            ids.append(f"chunk-{cid}")
            documents.append(chunk.get("content", ""))
            embeddings.append(vecs[i])
            metadatas.append({
                "chunk_id": chunk.get("chunk_id", 0),
                "course_id": chunk.get("course_id", 0),
                "file_id": chunk.get("file_id", 0),
                "chunk_index": chunk.get("chunk_index", 0),
                "source": chunk.get("source", ""),
                "page_number": chunk.get("page_number") or 0,
            })

        self._collection.upsert(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)
        return {"indexed": len(ids)}

    def search(self, query: str, course_id: Optional[int] = None, top_k: int = 5) -> list[dict]:
        """Search for similar chunks, optionally filtered by course_id."""
        query_vec = self._embedding_service.embed_query(query)
        where_filter = {}
        if course_id is not None:
            where_filter["course_id"] = course_id

        results = self._collection.query(
            query_embeddings=[query_vec],
            n_results=top_k,
            where=where_filter if where_filter else None,
            include=["documents", "metadatas", "distances"],
        )

        items = []
        if results["ids"] and results["ids"][0]:
            for i, chunk_id in enumerate(results["ids"][0]):
                meta = results["metadatas"][0][i] if results["metadatas"] else {}
                dist = results["distances"][0][i] if results["distances"] else 0.0
                items.append({
                    "chunk_id": meta.get("chunk_id", 0),
                    "course_id": meta.get("course_id", 0),
                    "file_id": meta.get("file_id", 0),
                    "chunk_index": meta.get("chunk_index", 0),
                    "content": results["documents"][0][i] if results["documents"] else "",
                    "source": meta.get("source", ""),
                    "page_number": meta.get("page_number"),
                    "score": round(1.0 - min(dist, 1.0), 4),
                })
        return items

    def delete_course_vectors(self, course_id: int) -> dict:
        """Delete all vectors for a given course_id."""
        self._collection.delete(where={"course_id": course_id})
        return {"deleted": True}

    def count(self) -> int:
        """Return total number of vectors in collection."""
        return self._collection.count()
