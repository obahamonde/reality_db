import asyncio
import unittest
from typing import Dict, List
from unittest.mock import MagicMock, patch

import pytest

from realitydb import DocumentObject, RPCError


# Mocked RocksDB methods for testing
def mock_db():
    return MagicMock()


# Helper function for async test methods
def async_test(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.mark.asyncio
class TestDocumentObject(unittest.TestCase):
    @patch("realitydb.get_db", new_callable=mock_db)
    async def test_create_table(self, mock_get_db: MagicMock) -> None:
        """Test creating a new table."""
        mock_get_db.return_value = {}  # Simulate an empty table creation
        result: Dict[str, str] = await DocumentObject.create_table("test_table")
        self.assertEqual(result, {"message": "Table test_table created successfully"})

    @patch("realitydb.get_db", new_callable=mock_db)
    async def test_delete_table(self, mock_get_db: MagicMock) -> None:
        """Test deleting a table."""
        mock_get_db.return_value.destroy = MagicMock()  # Simulate table deletion
        result: Dict[str, str] = await DocumentObject.delete_table("test_table")
        self.assertEqual(result, {"message": "Table 'test_table' deleted successfully"})

    @patch("realitydb.get_db", new_callable=mock_db)
    async def test_get_item(self, mock_get_db: MagicMock) -> None:
        """Test retrieving an item."""
        mock_db_instance = mock_get_db.return_value
        mock_db_instance.get.return_value = '{"id": "1", "foreign_key": "2"}'.encode(
            "utf-8"
        )
        result = await DocumentObject.get_item("test_table", "1")
        self.assertEqual(result.id, "1")
        self.assertEqual(result.foreign_key, "2")

    @patch("realitydb.get_db", new_callable=mock_db)
    async def test_get_item_not_found(self, mock_get_db: MagicMock) -> None:
        """Test item not found error."""
        mock_db_instance = mock_get_db.return_value
        mock_db_instance.get.return_value = None  # Simulate missing item

        with self.assertRaises(RPCError) as error:
            await DocumentObject.get_item("test_table", "1")
        self.assertEqual(error.exception.code, 404)
        self.assertIn("Item with id '1' not found", error.exception.message)

    @patch("realitydb.get_db", new_callable=mock_db)
    async def test_put_item(self, mock_get_db: MagicMock) -> None:
        """Test inserting an item."""
        mock_db_instance = mock_get_db.return_value
        item = DocumentObject(id="1", foreign_key="2")
        result = await item.put_item("test_table")
        mock_db_instance.__setitem__.assert_called_with(
            "1", '{"id": "1", "foreign_key": "2"}'.encode("utf-8")
        )
        self.assertEqual(result.id, "1")

    @patch("realitydb.get_db", new_callable=mock_db)
    async def test_delete_item(self, mock_get_db: MagicMock) -> None:
        """Test deleting an item."""
        mock_db_instance = mock_get_db.return_value
        mock_db_instance.__contains__.return_value = True  # Simulate item exists

        result: Dict[str, str] = await DocumentObject.delete_item("test_table", "1")
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

        result: List[DocumentObject] = await DocumentObject.query("test_table", limit=2)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].id, "1")
        self.assertEqual(result[1].id, "2")

    @patch("realitydb.get_db", new_callable=mock_db)
    async def test_update_item(self, mock_get_db: MagicMock) -> None:
        """Test updating an item."""
        mock_db_instance = mock_get_db.return_value
        mock_db_instance.get.return_value = '{"id": "1", "foreign_key": "2"}'.encode(
            "utf-8"
        )
        item_updates = [{"field": "foreign_key", "value": "3"}]

        result = await DocumentObject.update_item("test_table", "1", item_updates)
        self.assertEqual(result.foreign_key, "3")
        mock_db_instance.__setitem__.assert_called_with(
            b"1", '{"id": "1", "foreign_key": "3"}'.encode("utf-8")
        )


if __name__ == "__main__":
    unittest.main()
