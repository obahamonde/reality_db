import asyncio
import unittest
from typing import Dict, List
from unittest.mock import MagicMock, patch

import pytest

from realitydb import DocumentObject, RPCError, RPCClient

# Mocked RocksDB methods for testing
def mock_db():
    return MagicMock()

class TestDocument1(DocumentObject):
    foreign_key: str

class TestDocument2(DocumentObject):
    extra_field: int

@pytest.mark.asyncio
class TestDocumentObject(unittest.TestCase):
    @patch("realitydb.get_db", new_callable=mock_db)
    async def test_create_table(self, mock_get_db: MagicMock) -> None:
        """Test creating a new table."""
        mock_get_db.return_value = {}  # Simulate an empty table creation
        result: Dict[str, str] = await TestDocument1.create_table(table_name="test_table1")
        self.assertEqual(result, {"message": "Table test_table1 created successfully"})

    @patch("realitydb.get_db", new_callable=mock_db)
    async def test_delete_table(self, mock_get_db: MagicMock) -> None:
        """Test deleting a table."""
        mock_get_db.return_value.destroy = MagicMock()  # Simulate table deletion
        result: Dict[str, str] = await TestDocument1.delete_table(table_name="test_table1")
        self.assertEqual(result, {"message": "Table 'test_table1' deleted successfully"})

    @patch("realitydb.get_db", new_callable=mock_db)
    async def test_get_item(self, mock_get_db: MagicMock) -> None:
        """Test retrieving an item."""
        mock_db_instance = mock_get_db.return_value
        mock_db_instance.get.return_value = '{"id": "1", "foreign_key": "2"}'.encode("utf-8")
        result = await TestDocument1.get_item(table_name="test_table1", id="1")
        self.assertEqual(result.id, "1")
        self.assertEqual(result.foreign_key, "2")

    @patch("realitydb.get_db", new_callable=mock_db)
    async def test_get_item_not_found(self, mock_get_db: MagicMock) -> None:
        """Test item not found error."""
        mock_db_instance = mock_get_db.return_value
        mock_db_instance.get.return_value = None  # Simulate missing item

        with self.assertRaises(RPCError) as error:
            await TestDocument1.get_item(table_name="test_table1", id="1")
        self.assertEqual(error.exception.code, 404)
        self.assertIn("Item with id '1' not found", str(error.exception))

    @patch("realitydb.get_db", new_callable=mock_db)
    async def test_put_item(self, mock_get_db: MagicMock) -> None:
        """Test inserting an item."""
        mock_db_instance = mock_get_db.return_value
        item = TestDocument1(id="1", foreign_key="2")
        result = await item.put_item(table_name="test_table1")
        mock_db_instance.__setitem__.assert_called_with(
            "1", '{"id": "1", "foreign_key": "2"}'.encode("utf-8")
        )
        self.assertEqual(result.id, "1")

    @patch("realitydb.get_db", new_callable=mock_db)
    async def test_delete_item(self, mock_get_db: MagicMock) -> None:
        """Test deleting an item."""
        mock_db_instance = mock_get_db.return_value
        mock_db_instance.__contains__.return_value = True  # Simulate item exists

        result: Dict[str, str] = await TestDocument1.delete_item(table_name="test_table1", id="1")
        mock_db_instance.__delitem__.assert_called_with(b"1")
        self.assertEqual(result, {"message": "Item '1' deleted successfully"})

    @patch("realitydb.get_db", new_callable=mock_db)
    async def test_query(self, mock_get_db: MagicMock) -> None:
        """Test querying items."""
        mock_db_instance = mock_get_db.return_value
        # Simulate multiple items in RocksDB
        mock_db_instance.iter.return_value = mock_db_instance
        mock_db_instance.seek_to_first.return_value = None
        mock_db_instance.valid.side_effect = [True, True, False]
        mock_db_instance.value.side_effect = [
            '{"id": "1", "foreign_key": "2"}'.encode("utf-8"),
            '{"id": "2", "foreign_key": "1"}'.encode("utf-8"),
        ]

        result: List[TestDocument1] = await TestDocument1.query(table_name="test_table1", limit=2)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].id, "1")
        self.assertEqual(result[1].id, "2")

    @patch("realitydb.get_db", new_callable=mock_db)
    async def test_update_item(self, mock_get_db: MagicMock) -> None:
        """Test updating an item."""
        mock_db_instance = mock_get_db.return_value
        mock_db_instance.get.return_value = '{"id": "1", "foreign_key": "2"}'.encode("utf-8")
        item_updates = [{"field": "foreign_key", "value": "3"}]

        result = await TestDocument1.update_item(table_name="test_table1", id="1", updates=item_updates)
        self.assertEqual(result.foreign_key, "3")
        mock_db_instance.__setitem__.assert_called_with(
            b"1", '{"id": "1", "foreign_key": "3"}'.encode("utf-8")
        )

    @patch("realitydb.get_db", new_callable=mock_db)
    async def test_create_table_document2(self, mock_get_db: MagicMock) -> None:
        """Test creating a new table for TestDocument2."""
        mock_get_db.return_value = {}  # Simulate an empty table creation
        result: Dict[str, str] = await TestDocument2.create_table(table_name="test_table2")
        self.assertEqual(result, {"message": "Table test_table2 created successfully"})

    @patch("realitydb.get_db", new_callable=mock_db)
    async def test_get_item_document2(self, mock_get_db: MagicMock) -> None:
        """Test retrieving an item for TestDocument2."""
        mock_db_instance = mock_get_db.return_value
        mock_db_instance.get.return_value = '{"id": "1", "extra_field": 42}'.encode("utf-8")
        result = await TestDocument2.get_item(table_name="test_table2", id="1")
        self.assertEqual(result.id, "1")
        self.assertEqual(result.extra_field, 42)

@pytest.mark.asyncio
class TestRPCClient(unittest.TestCase):
    @patch('websockets.connect')
    async def test_rpc_client_create_table(self, mock_connect):
        mock_ws = MagicMock()
        mock_ws.recv.return_value = '{"jsonrpc": "2.0", "id": "1", "result": {"message": "Table test_table1 created successfully"}}'
        mock_connect.return_value = mock_ws

        client = RPCClient[TestDocument1](TestDocument1, uri="ws://test")
        result = await client.create_table(table_name="test_table1")
        
        self.assertEqual(result, {"message": "Table test_table1 created successfully"})
        mock_ws.send.assert_called_once()
        sent_message = mock_ws.send.call_args[0][0]
        self.assertIn('"method": "CreateTable"', sent_message)
        self.assertIn('"document_type": "TestDocument1"', sent_message)

    @patch('websockets.connect')
    async def test_rpc_client_get_item(self, mock_connect):
        mock_ws = MagicMock()
        mock_ws.recv.return_value = '{"jsonrpc": "2.0", "id": "1", "result": {"id": "1", "foreign_key": "2"}}'
        mock_connect.return_value = mock_ws

        client = RPCClient[TestDocument1](TestDocument1, uri="ws://test")
        result = await client.get_item(table_name="test_table1", id="1")
        
        self.assertEqual(result.id, "1")
        self.assertEqual(result.foreign_key, "2")
        mock_ws.send.assert_called_once()
        sent_message = mock_ws.send.call_args[0][0]
        self.assertIn('"method": "GetItem"', sent_message)
        self.assertIn('"document_type": "TestDocument1"', sent_message)

if __name__ == "__main__":
    unittest.main()