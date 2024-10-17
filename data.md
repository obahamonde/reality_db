poetry run pytest
============================= test session starts ==============================
platform darwin -- Python 3.10.15, pytest-8.3.3, pluggy-1.5.0
rootdir: /Users/oscarbahamonde/Desktop/realitydb
configfile: pyproject.toml
testpaths: tests
plugins: asyncio-0.24.0, cov-4.1.0, anyio-4.6.2.post1
asyncio: mode=strict, default_loop_scope=None
collected 11 items

tests/test_item.py .F.........                                           [100%]

=================================== FAILURES ===================================
_____________________ TestRPCServer.test_batch_write_item ______________________

self = <tests.test_item.TestRPCServer testMethod=test_batch_write_item>
mock_batch_write_item = <AsyncMock name='batch_write_item' id='4395267504'>

    @patch('realitydb.models.DocumentObject.batch_write_item', new_callable=AsyncMock)
    async def test_batch_write_item(self, mock_batch_write_item):
        # Set up the mock return value
        mock_batch_write_item.return_value = [
            DocumentObject(id="item1", data="Sample data"),
            DocumentObject(id="item2", data="Another data")
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
>           self.assertEqual(
                [item.model_dump() for item in kwargs['items']],
                items
            )
E           AssertionError: Lists differ: [{'id[28 chars]data', 'object': 'documentobject'}, {'id': 'it[53 chars]ct'}] != [{'id[28 chars]data'}, {'id': 'item2', 'data': 'Another data'}]
E           
E           First differing element 0:
E           {'id': 'item1', 'data': 'Sample data', 'object': 'documentobject'}
E           {'id': 'item1', 'data': 'Sample data'}
E           
E           - [{'data': 'Sample data', 'id': 'item1', 'object': 'documentobject'},
E           -  {'data': 'Another data', 'id': 'item2', 'object': 'documentobject'}]
E           + [{'data': 'Sample data', 'id': 'item1'},
E           +  {'data': 'Another data', 'id': 'item2'}]

tests/test_item.py:256: AssertionError
----------------------------- Captured stderr call -----------------------------
{"timestamp": "2024-10-17 11:56:40,300", "level": "INFO", "name": "realitydb.rpc_server", "message": "New WebSocket connection: test"}
{"timestamp": "2024-10-17 11:56:40,300", "level": "INFO", "name": "realitydb.rpc_server", "message": "Received: {'method': 'BatchWriteItem', 'properties': {'table_name': 'TestTable', 'items': [{'id': 'item1', 'data': 'Sample data'}, {'id': 'item2', 'data': 'Another data'}]}, 'id': '7e35a5d6-7b04-40e6-b58d-b2ed67044745'}"}
{"timestamp": "2024-10-17 11:56:40,301", "level": "INFO", "name": "realitydb.rpc_server", "message": "WebSocket disconnected: test"}
------------------------------ Captured log call -------------------------------
INFO     realitydb.rpc_server:rpc_server.py:58 New WebSocket connection: test
INFO     realitydb.rpc_server:rpc_server.py:63 Received: {'method': 'BatchWriteItem', 'properties': {'table_name': 'TestTable', 'items': [{'id': 'item1', 'data': 'Sample data'}, {'id': 'item2', 'data': 'Another data'}]}, 'id': '7e35a5d6-7b04-40e6-b58d-b2ed67044745'}
INFO     realitydb.rpc_server:rpc_server.py:88 WebSocket disconnected: test
=============================== warnings summary ===============================
tests/test_item.py:15
  /Users/oscarbahamonde/Desktop/realitydb/tests/test_item.py:15: PytestCollectionWarning: cannot collect test class 'TestDocument' because it has a __init__ constructor (from: tests/test_item.py)
    class TestDocument(DocumentObject):

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html

--------- coverage: platform darwin, python 3.10.15-final-0 ----------
Name                      Stmts   Miss  Cover   Missing
-------------------------------------------------------
realitydb/__init__.py         3      0   100%
realitydb/_proxy.py          71     71     0%   1-97
realitydb/documents.py       61     61     0%   1-80
realitydb/models.py         137     72    47%   58, 78-85, 90-98, 103-107, 111-113, 117-125, 138-157, 163, 174, 188-207, 214-219
realitydb/rpc_server.py      91      5    95%   89-91, 152, 160
realitydb/utils.py          109     62    43%   32-39, 43-51, 55, 59, 107-120, 133-140, 155-172, 186-187, 203-204, 219-227, 237-240
-------------------------------------------------------
TOTAL                       472    271    43%

=========================== short test summary info ============================
FAILED tests/test_item.py::TestRPCServer::test_batch_write_item - AssertionEr...
=================== 1 failed, 10 passed, 1 warning in 0.69s ====================
