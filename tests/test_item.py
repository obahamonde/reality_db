import unittest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from realitydb.rpc_server import RPCServer
from realitydb.models import DocumentObject
from realitydb.utils import RPCError

# Import TestClient from starlette
from starlette.testclient import TestClient

# Rename the class to avoid PytestCollectionWarning
class TestDocument(DocumentObject):
    data: str

class TestRPCServer(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Initialize the RPC server
        self.app = RPCServer()
        # Use TestClient to test the FastAPI app
        self.client = TestClient(self.app)

    @patch('realitydb.models.DocumentObject.create_table', new_callable=AsyncMock)
    async def test_create_table(self, mock_create_table):
        # Set up the mock return value
        mock_create_table.return_value = {
            "message": "Table TestTable created successfully",
            "id": "TestTable"
        }

        with self.client.websocket_connect("/test") as websocket:
            request = {
                "method": "CreateTable",
                "properties": {"table_name": "TestTable"},
                "id": str(uuid4())
            }
            websocket.send_json(request)
            response = websocket.receive_json()
            self.assertEqual(response["status"], "success")
            self.assertEqual(response["result"]["message"], "Table TestTable created successfully")
            self.assertEqual(response["result"]["id"], "TestTable")
            # Ensure the mocked method was called with correct parameters
            mock_create_table.assert_awaited_once_with(prefix="test", table_name="TestTable")

    @patch('realitydb.models.DocumentObject.put_item', new_callable=AsyncMock)
    async def test_put_item(self, mock_put_item):
        # Set up the mock return value
        mock_put_item.return_value = TestDocument(id="item1", data="Sample data")

        with self.client.websocket_connect("/test") as websocket:
            request = {
                "method": "PutItem",
                "properties": {
                    "table_name": "TestTable",
                    "item": {"id": "item1", "data": "Sample data"}
                },
                "id": str(uuid4())
            }
            websocket.send_json(request)
            response = websocket.receive_json()
            self.assertEqual(response["status"], "success")
            self.assertEqual(response["result"]["id"], "item1")
            self.assertEqual(response["result"]["data"], "Sample data")
            mock_put_item.assert_awaited_once()
            args, kwargs = mock_put_item.call_args
            self.assertEqual(kwargs['prefix'], 'test')
            self.assertEqual(kwargs['table_name'], 'TestTable')

    @patch('realitydb.models.DocumentObject.get_item', new_callable=AsyncMock)
    async def test_get_item(self, mock_get_item):
        # Set up the mock return value
        mock_get_item.return_value = TestDocument(id="item1", data="Sample data")

        with self.client.websocket_connect("/test") as websocket:
            request = {
                "method": "GetItem",
                "properties": {
                    "table_name": "TestTable",
                    "id": "item1"
                },
                "id": str(uuid4())
            }
            websocket.send_json(request)
            response = websocket.receive_json()
            self.assertEqual(response["status"], "success")
            self.assertEqual(response["result"]["id"], "item1")
            self.assertEqual(response["result"]["data"], "Sample data")
            mock_get_item.assert_awaited_once_with(prefix='test', table_name='TestTable', item_id='item1')

    @patch('realitydb.models.DocumentObject.delete_item', new_callable=AsyncMock)
    async def test_delete_item(self, mock_delete_item):
        # Set up the mock return value
        mock_delete_item.return_value = {
            "message": "Item 'item1' deleted successfully",
            "id": "item1"
        }

        with self.client.websocket_connect("/test") as websocket:
            request = {
                "method": "DeleteItem",
                "properties": {
                    "table_name": "TestTable",
                    "id": "item1"
                },
                "id": str(uuid4())
            }
            websocket.send_json(request)
            response = websocket.receive_json()
            self.assertEqual(response["status"], "success")
            self.assertEqual(response["result"]["message"], "Item 'item1' deleted successfully")
            self.assertEqual(response["result"]["id"], "item1")
            mock_delete_item.assert_awaited_once_with(prefix='test', table_name='TestTable', item_id='item1')

    @patch('realitydb.models.DocumentObject.query', new_callable=AsyncMock)
    async def test_query(self, mock_query):
        # Set up the mock return value
        mock_query.return_value = [
            TestDocument(id="item1", data="Sample data"),
            TestDocument(id="item2", data="Another data")
        ]

        with self.client.websocket_connect("/test") as websocket:
            request = {
                "method": "Query",
                "properties": {
                    "table_name": "TestTable",
                    "filters": {"data": "Sample data"},
                    "limit": 10,
                    "offset": 0
                },
                "id": str(uuid4())
            }
            websocket.send_json(request)
            response = websocket.receive_json()
            self.assertEqual(response["status"], "success")
            self.assertEqual(len(response["result"]), 2)
            mock_query.assert_awaited_once_with(
                prefix='test',
                table_name='TestTable',
                filters={"data": "Sample data"},
                limit=10,
                offset=0
            )

    @patch('realitydb.models.DocumentObject.update_item', new_callable=AsyncMock)
    async def test_update_item(self, mock_update_item):
        # Set up the mock return value
        mock_update_item.return_value = TestDocument(id="item1", data="Updated data")

        with self.client.websocket_connect("/test") as websocket:
            request = {
                "method": "UpdateItem",
                "properties": {
                    "table_name": "TestTable",
                    "id": "item1",
                    "updates": [{"action": "put", "data": {"data": "Updated data"}}]
                },
                "id": str(uuid4())
            }
            websocket.send_json(request)
            response = websocket.receive_json()
            self.assertEqual(response["status"], "success")
            self.assertEqual(response["result"]["id"], "item1")
            self.assertEqual(response["result"]["data"], "Updated data")
            mock_update_item.assert_awaited_once_with(
                prefix='test',
                table_name='TestTable',
                item_id='item1',
                updates=[{"action": "put", "data": {"data": "Updated data"}}]
            )

    @patch('realitydb.models.DocumentObject.scan', new_callable=AsyncMock)
    async def test_scan(self, mock_scan):
        # Set up the mock return value
        mock_scan.return_value = [
            TestDocument(id="item1", data="Sample data"),
            TestDocument(id="item2", data="Another data")
        ]

        with self.client.websocket_connect("/test") as websocket:
            request = {
                "method": "Scan",
                "properties": {
                    "table_name": "TestTable"
                },
                "id": str(uuid4())
            }
            websocket.send_json(request)
            response = websocket.receive_json()
            self.assertEqual(response["status"], "success")
            self.assertEqual(len(response["result"]), 2)
            mock_scan.assert_awaited_once_with(prefix='test', table_name='TestTable')

    @patch('realitydb.models.DocumentObject.batch_get_item', new_callable=AsyncMock)
    async def test_batch_get_item(self, mock_batch_get_item):
        # Set up the mock return value
        mock_batch_get_item.return_value = [
            TestDocument(id="item1", data="Sample data"),
            TestDocument(id="item2", data="Another data")
        ]

        with self.client.websocket_connect("/test") as websocket:
            request = {
                "method": "BatchGetItem",
                "properties": {
                    "table_name": "TestTable",
                    "ids": ["item1", "item2"]
                },
                "id": str(uuid4())
            }
            websocket.send_json(request)
            response = websocket.receive_json()
            self.assertEqual(response["status"], "success")
            self.assertEqual(len(response["result"]), 2)
            ids = [item["id"] for item in response["result"]]
            self.assertIn("item1", ids)
            self.assertIn("item2", ids)
            mock_batch_get_item.assert_awaited_once_with(
                prefix='test',
                table_name='TestTable',
                ids=["item1", "item2"]
            )

    @patch('realitydb.models.DocumentObject.batch_write_item', new_callable=AsyncMock)
    async def test_batch_write_item(self, mock_batch_write_item):
        # Set up the mock return value
        mock_batch_write_item.return_value = [
            TestDocument(id="item1", data="Sample data"),
            TestDocument(id="item2", data="Another data")
        ]

        with self.client.websocket_connect("/test") as websocket:
            items = [
                {"id": "item1", "data": "Sample data"},
                {"id": "item2", "data": "Another data"}
            ]
            request = {
                "method": "BatchWriteItem",
                "properties": {
                    "table_name": "TestTable",
                    "items": items
                },
                "id": str(uuid4())
            }
            websocket.send_json(request)
            response = websocket.receive_json()
            self.assertEqual(response["status"], "success")
            self.assertEqual(len(response["result"]), 2)
            mock_batch_write_item.assert_awaited_once()
            args, kwargs = mock_batch_write_item.call_args
            self.assertEqual(kwargs['prefix'], 'test')
            self.assertEqual(kwargs['table_name'], 'TestTable')
            # Updated assertion
            self.assertEqual(
                [item.model_dump(exclude={'object'}) for item in kwargs['items']],
                items
            )
    @patch('realitydb.models.DocumentObject.get_item', new_callable=AsyncMock)
    async def test_get_item_nonexistent(self, mock_get_item):
        # Set up the mock to raise an exception
        mock_get_item.side_effect = RPCError(code=404, message="Item not found")

        with self.client.websocket_connect("/test") as websocket:
            request = {
                "method": "GetItem",
                "properties": {
                    "table_name": "TestTable",
                    "id": "nonexistent"
                },
                "id": str(uuid4())
            }
            websocket.send_json(request)
            response = websocket.receive_json()
            self.assertEqual(response["status"], "error")
            self.assertEqual(response["error"]["code"], 404)
            self.assertEqual(response["error"]["message"], "Item not found")
            mock_get_item.assert_awaited_once_with(prefix='test', table_name='TestTable', item_id='nonexistent')

if __name__ == '__main__':
    unittest.main()
