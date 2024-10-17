from __future__ import annotations

import asyncio
import uuid
from functools import cached_property
from typing import Any, Dict, List, Optional, Union

import base64c as base64  # type: ignore
from pydantic import BaseModel, Field, computed_field
from rocksdict import Rdict as Rdict  # pylint: disable=E0611
from typing_extensions import Literal, Required, Self, TypeAlias, TypedDict

from .utils import RPCError, asyncify

JsonObject: TypeAlias = Union[
    Dict[str, Any], List[Dict[str, Any]], str, int, float, bool, None
]
GlowMethod: TypeAlias = Literal[
    "CreateTable",
    "DeleteTable",
    "GetItem",
    "PutItem",
    "DeleteItem",
    "Scan",
    "Query",
    "BatchGetItem",
    "BatchWriteItem",
    "UpdateItem",
]


class Params(TypedDict, total=False):
    items: Optional[List[Dict[str, Any]]]
    item: Optional[Dict[str, Any]]
    ids: Optional[List[str]]
    user_id: Optional[str]
    table_name: Optional[str]
    document_type: Optional[str]
    id: Optional[str]
    filters: Optional[Dict[str, Any]]
    limit: Optional[int]
    offset: Optional[int]
    prefix: Optional[str]
    updates: Optional[Dict[str, Any]]


class Error(TypedDict, total=False):
    code: Required[int]
    message: Required[str]


class SuccessResponse(TypedDict, total=False):
    message: Required[str]
    id: Required[str]


def get_db(prefix: str, table_name: str) -> Rdict:
    return Rdict("/tmp/" + prefix + "/" + table_name)


class DocumentObject(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    model_config = {
        "json_encoders": {bytes: lambda v: base64.b64encode(v).decode("utf-8")},
        "arbitrary_types_allowed": True,
        "extra": "allow",
    }

    @computed_field(return_type=str)
    @cached_property
    def object(self) -> str:
        return self.__class__.__name__.lower()

    @classmethod
    @asyncify
    def create_table(cls, *, prefix: str, table_name: str) -> SuccessResponse:
        try:
            get_db(prefix, table_name)
            return {
                "message": "Table %s created successfully" % table_name,
                "id": f"{table_name}_{prefix}",
            }
        except Exception as e:
            raise RPCError(message="Error creating table %s" % str(e))

    @classmethod
    @asyncify
    def delete_table(cls, *, prefix: str, table_name: str) -> SuccessResponse:
        try:
            db = get_db(prefix, table_name)
            db.destroy(prefix + table_name)
            return {
                "message": f"Table '{table_name}' deleted successfully",
                "id": table_name,
            }
        except Exception as e:
            raise RPCError(message="Error deleting table: %s" % str(e))

    @classmethod
    @asyncify
    def get_item(cls, *, prefix: str, table_name: str, item_id: str) -> Self:
        db = get_db(prefix, table_name)
        item = db.get(item_id)
        if item is None:
            raise RPCError(code=404, message="Item with id '%s' not found" % item_id)
        return cls.model_validate_json(item.decode("utf-8"))

    @asyncify
    def put_item(self, *, prefix: str, table_name: str) -> Self:
        db = get_db(prefix, table_name)
        db[self.id] = self.model_dump_json().encode("utf-8")
        return self

    @classmethod
    async def scan(cls, *, prefix: str, table_name: str) -> List[Self]:
        db = get_db(prefix, table_name)
        items: List[Self] = []
        iterable = db.iter()
        iterable.seek_to_first()
        while iterable.valid():
            value = iterable.value()
            items.append(cls.model_validate_json(value.decode("utf-8")))
            iterable.next()  # Advance the iterator
        return items

    @classmethod
    @asyncify
    def query(
        cls,
        *,
        prefix: str,
        table_name: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 25,
        offset: int = 0,
    ) -> List[Self]:
        db = get_db(prefix, table_name)
        items: List[Self] = []
        count = 0
        iterable = db.iter()
        iterable.seek_to_first()
        while iterable.valid():
            if count < offset:
                count += 1
                iterable.next()
                continue
            item = cls.model_validate_json(iterable.value().decode("utf-8"))
            if filters:
                if all(getattr(item, k) == v for k, v in filters.items()):
                    items.append(item)
            else:
                items.append(item)
            if len(items) >= limit:
                break
            iterable.next()  # Advance the iterator
        return items

    @classmethod
    async def batch_get_item(
        cls, *, prefix: str, table_name: str, ids: List[str]
    ) -> List[Self]:
        return await asyncio.gather(
            *[
                cls.get_item(prefix=prefix, table_name=table_name, item_id=id)
                for id in ids
            ]
        )

    @classmethod
    async def batch_write_item(
        cls, *, prefix: str, table_name: str, items: List[Self]
    ) -> List[Self]:
        return await asyncio.gather(
            *[item.put_item(prefix=prefix, table_name=table_name) for item in items]
        )

    @classmethod
    @asyncify
    def update_item(
        cls,
        *,
        prefix: str,
        table_name: str,
        item_id: str,
        updates: List[Dict[str, Any]],
    ) -> Self | SuccessResponse:
        db = get_db(prefix, table_name)
        key = item_id.encode("utf-8")
        item_data = db.get(key)
        if item_data is None:
            raise RPCError(message="Item with id '%s' not found" % item_id)
        item = cls.model_validate_json(item_data.decode("utf-8"))

        for update in updates:
            action = update.get("action")
            if action == "put":
                for field, value in update.get("data", {}).items():
                    setattr(item, field, value)
            elif action == "delete":
                db.delete(key)
                return {
                    "message": f"Item '{item_id}' deleted successfully",
                    "id": item_id,
                }
        db[key] = item.model_dump_json().encode("utf-8")
        return item

    @classmethod
    @asyncify
    def delete_item(
        cls, *, prefix: str, table_name: str, item_id: str
    ) -> SuccessResponse:
        db = get_db(prefix, table_name)
        key = item_id.encode("utf-8")
        if key not in db:
            raise RPCError(code=404, message=f"Item with id '{item_id}' not found")
        del db[key]
        return {"message": f"Item '{item_id}' deleted successfully", "id": item_id}
