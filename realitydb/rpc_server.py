from typing import Any, Dict, List, TypeVar
from uuid import UUID, uuid4

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing_extensions import Required, TypedDict
from realitydb.models import (
    DocumentObject,
    GlowMethod,
    JsonObject,
)
from realitydb.utils import RPCError, get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound=DocumentObject)


class Property(TypedDict, total=False):
    id: str
    item: JsonObject
    items: List[JsonObject]
    filters: Dict[str, Any]
    limit: int
    offset: int
    updates: List[Dict[str, Any]]


class RPCRequest(TypedDict, total=False):
    method: Required[GlowMethod]
    properties: Required[Property]
    id: Required[UUID]


class RPCServer(FastAPI):
    def __init__(
        self,
        title: str = "RealityDB",
        description: str = "RealityDB",
        version: str = "0.1.0",
    ):
        super().__init__(
            title=title,
            description=description,
            version=version,
            debug=True,
        )

        @self.websocket("/{path:path}")
        async def _(ws: WebSocket, path: str):
            await self.handler(ws, path)

    async def handler(self, ws: WebSocket, path: str):
        await ws.accept()
        logger.info(f"New WebSocket connection: {path}")

        try:
            while True:
                data_dict: RPCRequest = await ws.receive_json()
                logger.info(f"Received: {data_dict}")

                method = data_dict.get("method", "PutItem")
                properties = data_dict.get("properties", {})
                request_id = data_dict.get("id", uuid4())

                try:
                    response = await self.dispatch(method, properties,path)
                    await ws.send_json(
                        {
                            "id": str(request_id),
                            "result": response,
                            "status": "success",
                        }
                    )
                except RPCError as e:
                    await ws.send_json(
                        {
                            "id": str(request_id),
                            "error": {"code": e.code, "message": e.message},
                            "status": "error",
                        }
                    )

        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected: {path}")
        except Exception as e:
            logger.error(f"Error in WebSocket handler: {e}")
            await ws.close()

    async def dispatch(self, method: GlowMethod, properties: Property,prefix:str):
        result = None
        table_name: str = properties.get("table_name", str(uuid4()))
        if method == "CreateTable":
            result =await DocumentObject.create_table(
                prefix=prefix, table_name=table_name
            )
        elif method == "DeleteTable":
            result =await DocumentObject.delete_table(
                prefix=prefix, table_name=table_name
            )
        elif method == "GetItem":
            assert "id" in properties, "id is required"
            item_id = properties["id"]
            result = await DocumentObject.get_item(
                prefix=prefix, table_name=table_name, item_id=item_id
            )
        elif method == "PutItem":
            item = DocumentObject(**properties["item"])  # type: ignore
            result = await item.put_item(prefix=prefix, table_name=table_name)
        elif method == "DeleteItem":
            assert "id" in properties, "id is required"
            item_id = properties["id"]
            return await DocumentObject.delete_item(
                prefix=prefix, table_name=table_name, item_id=item_id
            )
        elif method == "Scan":
            result = await DocumentObject.scan(prefix=prefix, table_name=table_name)
        elif method == "Query":
            filters = properties.get("filters", {})
            limit = properties.get("limit", 25)
            offset = properties.get("offset", 0)
            result = await DocumentObject.query(
                prefix=prefix,
                table_name=table_name,
                filters=filters,
                limit=limit,
                offset=offset,
            )
        elif method == "BatchGetItem":
            ids = properties["ids"]  # type: ignore
            result = await DocumentObject.batch_get_item(
                prefix=prefix, table_name=table_name, ids=ids
            )
        elif method == "BatchWriteItem":
            items = [DocumentObject(**item) for item in properties["items"]]  # type: ignore
            result = await DocumentObject.batch_write_item(
                prefix=prefix, table_name=table_name, items=items
            )
        elif method == "UpdateItem":
            item_id = properties.get("id", str(uuid4()))
            updates = properties.get("updates", [])
            result = await DocumentObject.update_item(
                prefix=prefix,
                table_name=table_name,
                item_id=item_id,
                updates=updates,
            )
        if result is None:
            return {}
        if isinstance(result,dict):
            return result
        if isinstance(result,list):
            return [item.model_dump() for item in result]
        if isinstance(result,DocumentObject):
            return result.model_dump()
        else:
            raise RPCError(code=400, message=f"Unsupported method: {method}")