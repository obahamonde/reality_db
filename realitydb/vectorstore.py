from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
from .models import DocumentObject




class VectorStore(DocumentObject):
    content: str
    embedding: List[float]
    metadata: Dict[str, Any]

    @classmethod
    def initialize(cls, model_name: str = "all-MiniLM-L6-v2"):
        cls.model = SentenceTransformer(model_name)
        cls.index = None
        cls.id_to_object: Dict[str, VectorStore] = {}

    @classmethod
    async def add_documents(cls, documents: List[Dict[str, Any]], prefix: str, table_name: str):
        if cls.index is None:
            cls.initialize()

        for doc in documents:
            content = doc.get('content', '')
            metadata = doc.get('metadata', {})
            embedding = cls.model.encode([content])[0].tolist()

            vector_doc = cls(
                content=content,
                embedding=embedding,
                metadata=metadata
            )
            await vector_doc.put_item(prefix=prefix, table_name=table_name)

            if cls.index is None:
                cls.index = faiss.IndexFlatL2(len(embedding))
            
            cls.index.add(np.array([embedding], dtype=np.float32))
            cls.id_to_object[vector_doc.id] = vector_doc

        return {"message": f"Added {len(documents)} documents to the vector store"}

    @classmethod
    async def search(cls, query: str, prefix: str, table_name: str, k: int = 5) -> List[Dict[str, Any]]:
        if cls.index is None:
            cls.initialize()
            # Rebuild index from stored documents
            stored_docs = await cls.scan(prefix=prefix, table_name=table_name)
            for doc in stored_docs:
                cls.index.add(np.array([doc.embedding], dtype=np.float32))
                cls.id_to_object[doc.id] = doc

        query_embedding = cls.model.encode([query])
        distances, indices = cls.index.search(query_embedding, k)
        
        results = []
        for i, idx in enumerate(indices[0]):
            doc = cls.id_to_object[list(cls.id_to_object.keys())[idx]]
            results.append({
                "id": doc.id,
                "content": doc.content,
                "metadata": doc.metadata,
                "distance": float(distances[0][i])
            })
        
        return results

    @classmethod
    async def delete_document(cls, doc_id: str, prefix: str, table_name: str):
        if doc_id in cls.id_to_object:
            del cls.id_to_object[doc_id]
            # Note: FAISS doesn't support direct deletion, so we need to rebuild the index
            cls.index = None
            await cls.delete_item(prefix=prefix, table_name=table_name, item_id=doc_id)
            return {"message": f"Document {doc_id} deleted from vector store"}
        else:
            return {"message": f"Document {doc_id} not found in vector store"}

    @classmethod
    async def update_document(cls, doc_id: str, new_content: str, new_metadata: Optional[Dict[str, Any]], prefix: str, table_name: str):
        if doc_id in cls.id_to_object:
            doc = cls.id_to_object[doc_id]
            doc.content = new_content
            if new_metadata:
                doc.metadata = new_metadata
            doc.embedding = cls.model.encode([new_content])[0].tolist()
            
            await doc.put_item(prefix=prefix, table_name=table_name)
            
            # Update the index
            cls.index = None  # Force rebuild on next search
            return {"message": f"Document {doc_id} updated in vector store"}
        else:
            return {"message": f"Document {doc_id} not found in vector store"}
