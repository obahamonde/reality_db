from __future__ import annotations

import asyncio
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar
from uuid import uuid4

import websockets
from pydantic import BaseModel, Field

from .models import DocumentObject, GlowMethod
from .utils import RPCError, get_logger

logger = get_logger(__name__)

O = TypeVar('O', bound=DocumentObject)

class RPCRequest(BaseModel):
    jsonrpc: str = Field(default="2.0")
    method: GlowMethod
    params: Dict[str, Any]
    id: str = Field(default_factory=lambda: str(uuid4()))

class RPCResponse(BaseModel, Generic[O]):
    jsonrpc: str = Field(default="2.0")
    id: str
    result: Optional[O] = None
    error: Optional[Dict[str, Any]] = None

class RPCClient(Generic[O]):
    def __init__(self, model: Type[O], uri: str = "ws://localhost:8888"):
        self.model = model
        self.uri = uri
        self.ws: Optional[websockets.WebSocketClientProtocol] = None

    async def connect(self):
        if not self.ws or self.ws.closed:
            self.ws = await websockets.connect(self.uri)
        return self

    async def close(self):
        if self.ws and not self.ws.closed:
            await self.ws.close()
            self.ws = None

    async def _send_request(self, method: GlowMethod, params: Dict[str, Any]) -> O:
        if not self.ws or self.ws.closed:
            await self.connect()

        # Include document_type in the request params
        params["document_type"] = self.model.__name__

        request = RPCRequest(method=method, params=params)
        await self.ws.send(request.model_dump_json()) # type: ignore

        raw_response = await self.ws.recv()  # type: ignore
        response = RPCResponse[O].model_validate_json(raw_response)

        if response.error:
            raise RPCError(response.error.get("code", -32000), response.error.get("message", "Unknown error"))

        if response.result is None:
            raise RPCError(-32603, "Internal error: No result in response")

        return self.model.model_validate(response.result)

    async def create_table(self, *, table_name: str):
        return await self._send_request("CreateTable", {"table_name": table_name})

    async def delete_table(self, *, table_name: str):
        return await self._send_request("DeleteTable", {"table_name": table_name})

    async def put_item(self, *, table_name: str, item: O):
        return await self._send_request("PutItem", {"table_name": table_name, "item": item.model_dump()})

    async def get_item(self, *, table_name: str, id: str):
        return await self._send_request("GetItem", {"table_name": table_name, "id": id})

    async def update_item(self, *, table_name: str, id: str, updates: Dict[str, Any]):
        return await self._send_request("UpdateItem", {"table_name": table_name, "id": id, "updates": updates})

    async def delete_item(self, *, table_name: str, id: str):  
        return await self._send_request("DeleteItem", {"table_name": table_name, "id": id})

    async def scan(self, *, table_name: str, limit: int = 25, offset: int = 0):
        result = await self._send_request("Scan", {"table_name": table_name, "limit": limit, "offset": offset})
        return [self.model.model_validate(item) for item in result]

    async def query(self, *, table_name: str, filters: Optional[Dict[str, Any]] = None, limit: int = 25, offset: int = 0):
        params = {"table_name": table_name, "limit": limit, "offset": offset}
        if filters:
            params["filters"] = filters
        result = await self._send_request("Query", params)
        return [self.model.model_validate(item) for item in result]

    async def batch_get_item(self, *, table_name: str, ids: List[str]):
        result = await self._send_request("BatchGetItem", {"table_name": table_name, "ids": ids})
        return [self.model.model_validate(item) for item in result]

    async def batch_write_item(self, *, table_name: str, items: List[O]):
        items_data = [item.model_dump() for item in items]
        result = await self._send_request("BatchWriteItem", {"table_name": table_name, "items": items_data})
        return [self.model.model_validate(item) for item in result]

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()