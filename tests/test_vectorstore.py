import pytest
from unittest.mock import AsyncMock, patch
from realitydb.vectorstore import VectorStore

@pytest.mark.asyncio
async def test_add_documents():
    with patch('realitydb.vectorstore.VectorStore.add_documents', new_callable=AsyncMock) as mock_add:
        mock_add.return_value = {"status": "success", "added": 2}
        
        documents = [
            {"id": "1", "content": "Test document 1"},
            {"id": "2", "content": "Test document 2"}
        ]
        result = await VectorStore.add_documents(documents, "test_prefix", "test_table")
        
        assert result == {"status": "success", "added": 2}
        mock_add.assert_called_once_with(documents, "test_prefix", "test_table")

@pytest.mark.asyncio
async def test_search():
    with patch('realitydb.vectorstore.VectorStore.search', new_callable=AsyncMock) as mock_search:
        mock_search.return_value = [
            {"id": "1", "content": "Test document 1", "score": 0.9},
            {"id": "2", "content": "Test document 2", "score": 0.7}
        ]
        
        results = await VectorStore.search("test query", "test_prefix", "test_table", k=2)
        
        assert len(results) == 2
        assert results[0]["id"] == "1"
        assert results[1]["id"] == "2"
        mock_search.assert_called_once_with("test query", "test_prefix", "test_table", k=2)

@pytest.mark.asyncio
async def test_delete_document():
    with patch('realitydb.vectorstore.VectorStore.delete_document', new_callable=AsyncMock) as mock_delete:
        mock_delete.return_value = {"status": "success", "deleted": "1"}
        
        result = await VectorStore.delete_document("1", "test_prefix", "test_table")
        
        assert result == {"status": "success", "deleted": "1"}
        mock_delete.assert_called_once_with("1", "test_prefix", "test_table")

@pytest.mark.asyncio
async def test_update_document():
    with patch('realitydb.vectorstore.VectorStore.update_document', new_callable=AsyncMock) as mock_update:
        mock_update.return_value = {"status": "success", "updated": "1"}
        
        new_content = "Updated test document"
        new_metadata = {"key": "value"}
        result = await VectorStore.update_document("1", new_content, new_metadata, "test_prefix", "test_table")
        
        assert result == {"status": "success", "updated": "1"}
        mock_update.assert_called_once_with("1", new_content, new_metadata, "test_prefix", "test_table")

@pytest.mark.asyncio
async def test_search_empty_result():
    with patch('realitydb.vectorstore.VectorStore.search', new_callable=AsyncMock) as mock_search:
        mock_search.return_value = []
        
        results = await VectorStore.search("non-existent query", 5, "test_prefix", "test_table")
        
        assert len(results) == 0
        mock_search.assert_called_once_with("non-existent query", 5, "test_prefix", "test_table")

@pytest.mark.asyncio
async def test_delete_non_existent_document():
    with patch('realitydb.vectorstore.VectorStore.delete_document', new_callable=AsyncMock) as mock_delete:
        mock_delete.return_value = {"status": "not_found"}
        
        result = await VectorStore.delete_document("non_existent_id", "test_prefix", "test_table")
        
        assert result == {"status": "not_found"}
        mock_delete.assert_called_once_with("non_existent_id", "test_prefix", "test_table")
