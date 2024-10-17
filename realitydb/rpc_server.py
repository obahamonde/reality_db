from typing import Any, Dict, List, TypeVar
from uuid import UUID, uuid4

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from typing_extensions import Required, TypedDict
from fastapi.responses import StreamingResponse
import tempfile
import base64c
from realitydb.models import DocumentObject, GlowMethod, JsonObject
from realitydb.utils import RPCError, get_logger
from realitydb.documents import DocxFile, PDFFile, PPTXFile, ExcelFile

from .vectorstore import VectorStore

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

        @self.post("/upload")
        async def _(file: UploadFile = File(...)):
            return await self.upload_file(file)

        @self.get("/health")
        async def _():
            return {"status": "ok"}

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
                    response = await self.dispatch(method, properties, path)
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

    async def add_to_vector_store(
        self, method: GlowMethod, properties: Property, prefix: str
    ):
        table_name: str = properties.get("table_name", str(uuid4()))
        documents = properties.get("documents", [])
        result = await VectorStore.add_documents(documents, prefix, table_name)
        return result

    async def search_vector_store(
        self, properties: Property, prefix: str
    ):
        table_name: str = properties.get("table_name", str(uuid4()))
        query = properties.get("query", "")
        k = properties.get("k", 5)
        results = await VectorStore.search(
            query=query,
            k=k,
            prefix=prefix,
            table_name=table_name,
        )
        return results

    async def delete_from_vector_store(
        self, properties: Property, prefix: str
    ):
        table_name: str = properties.get("table_name", str(uuid4()))
        doc_id = properties.get("id")
        if not doc_id:
            raise RPCError(code=400, message="Document ID is required")
        result = await VectorStore.delete_document(
            doc_id=doc_id,
            prefix=prefix,
            table_name=table_name,
        )
        return result

    async def update_in_vector_store(
        self, properties: Property, prefix: str
    ):
        table_name: str = properties.get("table_name", str(uuid4()))
        doc_id = properties.get("id")
        new_content = properties.get("content")
        new_metadata = properties.get("metadata")
        if not doc_id or not new_content:
            raise RPCError(code=400, message="Document ID and new content are required")
        result = await VectorStore.update_document(
            doc_id=doc_id,
            new_content=new_content,
            new_metadata=new_metadata,
            prefix=prefix,
            table_name=table_name,
        )
        return result

    async def dispatch(self, method: GlowMethod, properties: Property, prefix: str):
        result = None
        table_name: str = properties.get("table_name", str(uuid4()))

        if method == "AddToVectorStore":
            result = await self.add_to_vector_store(method, properties, prefix)
        elif method == "SearchVectorStore":
            result = await self.search_vector_store(properties=properties, prefix=prefix)
        elif method == "DeleteFromVectorStore":
            result = await self.delete_from_vector_store(properties=properties, prefix=prefix)
        elif method == "UpdateInVectorStore":
            result = await self.update_in_vector_store(properties=properties, prefix=prefix)
        elif method == "CreateTable":
            result = await DocumentObject.create_table(
                prefix=prefix, table_name=table_name
            )
        elif method == "DeleteTable":
            result = await DocumentObject.delete_table(
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
        if isinstance(result, dict):
            return result
        if isinstance(result, list):
            if all(isinstance(item, DocumentObject) for item in result):
                return [item.model_dump() for item in result]  # type: ignore
            return result
        if isinstance(result, DocumentObject):
            return result.model_dump()
        raise RPCError(code=400, message=f"Unsupported method: {method}")

    async def upload_file(self, file: UploadFile = File(...)):
        content_type = file.content_type
        assert content_type is not None
        assert file.filename is not None
        print(content_type)
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(await file.read())
            temp_file_path = temp_file.name
            if "office" in content_type:
                if "word" in content_type:
                    document = DocxFile(name=temp_file_path)
                elif "excel" in content_type:
                    document = ExcelFile(name=temp_file_path)
                elif "powerpoint" in content_type:
                    document = PPTXFile(name=temp_file_path)
                else:
                    raise RPCError(code=400, message=f"Unsupported office file type: {content_type}")
            elif "pdf" in content_type:
                document = PDFFile(name=temp_file_path)
            else:
                raise RPCError(code=400, message=f"Unsupported file type: {content_type}")
            def generator():
                for chunk in document.extract_text():
                    yield f"<p>{chunk}</p>"
                for image in document.extract_images():
                    yield f"<img src='data:image/jpeg;base64,{base64c.b64encode(image).decode()}'/>"
            return StreamingResponse(generator(), media_type="text/html")

