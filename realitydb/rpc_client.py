from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, Generic, List, Literal, Optional, Type, TypeVar
from uuid import uuid4

import websockets
from pydantic import BaseModel, Field
from typing_extensions import TypeAlias

from .models import DocumentObject, Error  # type: ignore
from .utils import RPCError

O = TypeVar("O", bound=DocumentObject)
GlowMethod: TypeAlias = Literal[
    "CreateTable",
    "DeleteTable",
    "PutItem",
    "GetItem",
    "UpdateItem",
    "DeleteItem",
    "Scan",
    "Query",
    "BatchGetItem",
    "BatchWriteItem",
]


class RPCResponse(BaseModel, Generic[O]):
    model_config = {
        "json_encoders": {Type[O]: lambda v: v.model_dump()},
        "arbitrary_types_allowed": True,
        "extra": "allow",
    }
    id: str = Field(...)
    jsonrpc: Literal["2.0"] = Field(default="2.0")
    result: O
    error: Optional[Error] = Field(default=None)


@dataclass
class RPCClient(Generic[O]):
    model: Type[RPCResponse[O]]
    uri: str = field(default="ws://localhost:8888")
    ws: Optional[websockets.WebSocketClientProtocol] = field(default=None, init=False)

    @classmethod
    def __class_getitem__(cls, item: Type[RPCResponse[O]]):
        cls.model = item
        return cls

    def __post_init__(self):
        asyncio.create_task(self._connect())

    def __del__(self):
        asyncio.create_task(self._close())

    async def _connect(self):
        self.ws = await websockets.connect(self.uri)

    async def _close(self):
        if self.ws:
            await self.ws.close()
            self.ws = None

    async def _send_request(self, method: GlowMethod, *, params: Dict[str, Any]) -> O:
        try:
            if not self.ws:
                raise ValueError("Not connected to the server")
            request = {
                "jsonrpc": "2.0",
                "method": method,
                "params": params,
                "id": str(uuid4()),
            }
            data = self.model(**request)
            await self.ws.send(data.model_dump_json())
            raw_response = await self.ws.recv()
            response = self.model.model_validate_json(raw_response)
            if response.error:
                raise RPCError(response.error["code"], response.error["message"])
            return response.result
        except (Exception, RPCError) as e:
            raise e

    async def create_table(self, *, table_name: str):
        params = {"table_name": table_name}
        return await self._send_request("CreateTable", params=params)

    async def delete_table(self, *, table_name: str):
        params = {"table_name": table_name}
        return await self._send_request("DeleteTable", params=params)

    async def put_item(self, *, table_name: str, item: O):
        params = {"table_name": table_name, "item": item.model_dump()}
        result = await self._send_request("PutItem", params=params)
        return self.model.model_validate(result)

    async def get_item(self, *, table_name: str, id: str):
        params = {"table_name": table_name, "id": id}
        result = await self._send_request("GetItem", params=params)
        return self.model.model_validate(result)

    async def update_item(self, *, table_name: str, id: str, updates: Dict[str, Any]):
        params = {"table_name": table_name, "id": id, "updates": updates}
        result = await self._send_request("UpdateItem", params=params)
        return self.model.model_validate(result)

    async def delete_item(self, *, table_name: str, id: str):
        params = {"table_name": table_name, "id": id}
        return await self._send_request("DeleteItem", params=params)

    async def scan(self, *, table_name: str, limit: int = 25, offset: int = 0):
        params = {"table_name": table_name, "limit": limit, "offset": offset}
        result = await self._send_request("Scan", params=params)
        return [self.model.model_validate(item) for item in result]

    async def query(
        self,
        *,
        table_name: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 25,
        offset: int = 0,
    ):
        params = {"table_name": table_name, "limit": limit, "offset": offset}
        if filters:
            params["filters"] = filters
        result = await self._send_request("Query", params=params)
        return [self.model.model_validate(item) for item in result]

    async def batch_get_item(self, *, ids: List[str], table_name: str):
        params = {"table_name": table_name, "ids": ids}
        result = await self._send_request("BatchGetItem", params=params)
        return [self.model.model_validate(item) for item in result]

    async def batch_write_item(self, *, items: List[O], table_name: str):
        items_data = [item.model_dump() for item in items]
        params = {"table_name": table_name, "items": items_data}
        result = await self._send_request("BatchWriteItem", params=params)
        return [self.model.model_validate(item) for item in result]

    async def __aenter__(self):
        await self._connect()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[BaseException],
        exc_value: Optional[BaseException],
        traceback: Optional[Any],
    ):
        await self._close()
