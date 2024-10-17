import asyncio
import json
from typing import Dict, Any, Type, TypeVar, List
import websockets
from websockets.server import WebSocketServerProtocol

from realitydb import DocumentObject, RPCError
from realitydb.utils import get_logger

logger = get_logger(__name__)

T = TypeVar('T', bound=DocumentObject)

class RPCServer:
    def __init__(self, document_classes: List[Type[T]], host: str = 'localhost', port: int = 8888):
        self.document_classes = {cls.__name__: cls for cls in document_classes}
        self.host = host
        self.port = port

    async def handle_request(self, websocket: WebSocketServerProtocol, path: str):
        try:
            async for message in websocket:
                request = json.loads(message)
                method = request.get('method')
                params = request.get('params', {})
                request_id = request.get('id')
                document_type = params.get('document_type')

                try:
                    result = await self.dispatch_method(method, params, document_type)
                    response = {
                        'jsonrpc': '2.0',
                        'result': result,
                        'id': request_id
                    }
                except RPCError as e:
                    response = {
                        'jsonrpc': '2.0',
                        'error': {'code': e.code, 'message': str(e)},
                        'id': request_id
                    }
                except Exception as e:
                    logger.exception(f"Unexpected error: {e}")
                    response = {
                        'jsonrpc': '2.0',
                        'error': {'code': -32603, 'message': 'Internal error'},
                        'id': request_id
                    }

                await websocket.send(json.dumps(response))
        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed")

    async def dispatch_method(self, method: str, params: Dict[str, Any], document_type: str) -> Any:
        if document_type not in self.document_classes:
            raise RPCError(code=-32602, message=f"Invalid document type: {document_type}")

        document_class = self.document_classes[document_type]
        
        if method == 'CreateTable':
            return await document_class.create_table(**params)
        elif method == 'DeleteTable':
            return await document_class.delete_table(**params)
        elif method == 'GetItem':
            return await document_class.get_item(**params)
        elif method == 'PutItem':
            item = document_class(**params['item'])
            return await item.put_item(table_name=params['table_name'])
        elif method == 'DeleteItem':
            return await document_class.delete_item(**params)
        elif method == 'Query':
            return await document_class.query(**params)
        elif method == 'UpdateItem':
            return await document_class.update_item(**params)
        else:
            raise RPCError(code=-32601, message=f"Method '{method}' not found")

    async def start(self):
        server = await websockets.serve(self.handle_request, self.host, self.port)
        logger.info(f"Multi-Document RPC Server started on {self.host}:{self.port}")
        logger.info(f"Serving document types: {', '.join(self.document_classes.keys())}")
        await server.wait_closed()

def run(document_classes: List[Type[T]], host: str = 'localhost', port: int = 8888):
    server = RPCServer(document_classes, host, port)
    asyncio.run(server.start())