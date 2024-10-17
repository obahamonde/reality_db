from __future__ import annotations

import asyncio
import uuid
from functools import cached_property
from typing import Any, Dict, List, Optional, Union

import base64c as base64  # type: ignore
from pydantic import BaseModel, Field, computed_field
from rocksdict import Rdict as Rdict  # type: ignore
from typing_extensions import Literal, Required, Self, TypeAlias, TypedDict

from .utils import RPCError, asyncify

PREFIX = "/tmp/"

JsonObject: TypeAlias = Union[
    Dict[str, Any], List[Dict[str, Any]], str, int, float, bool, None
]
GlowMethod: TypeAlias = Literal[
    "Select",
    "Insert",
    "Update",
    "Delete",
    "CreateTable",
    "DescribeTable",
    "DescribeIndex",
    "BatchGetItem",
    "BatchWriteItem",
]


def get_db(table_name: str) -> Rdict:
    return Rdict(PREFIX + table_name)


class DocumentObject(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    model_config = {
        "json_encoders": {bytes: lambda v: base64.b64encode(v).decode("utf-8")},
        "arbitrary_types_allowed": True,
        "populate_by_name": True,
    }

    @computed_field(return_type=str)
    @cached_property
    def object(self) -> str:
        return self.__class__.__name__.lower()

    @classmethod
    @asyncify
    def create_table(cls, table_name: str) -> Dict[str, str]:
        try:
            get_db(table_name)
            return {"message": "Table %s created successfully" % table_name}
        except Exception as e:
            raise RPCError(message="Error creating table %s" % str(e))

    @classmethod
    @asyncify
    def delete_table(cls, table_name: str) -> Dict[str, str]:
        try:
            db = get_db(table_name)
            db.destroy(PREFIX + table_name)
            return {"message": f"Table '{table_name}' deleted successfully"}
        except Exception as e:
            raise RPCError(message="Error deleting table: %s" % str(e))

    @classmethod
    @asyncify
    def get_item(cls, table_name: str, item_id: str) -> Self:
        db = get_db(table_name)
        item = db.get(item_id.encode("utf-8"))
        if item is None:
            raise RPCError(code=404, message="Item with id '%s' not found" % item_id)
        return cls.model_validate_json(item.decode("utf-8"))

    @asyncify
    def put_item(self, table_name: str) -> Self:
        db = get_db(table_name)
        db[self.id] = self.model_dump_json().encode("utf-8")
        return self

    @classmethod
    @asyncify
    def delete_item(cls, table_name: str, item_id: str) -> Dict[str, str]:
        db = get_db(table_name)
        key = item_id.encode("utf-8")
        if key not in db:
            raise RPCError(code=404, message=f"Item with id '{item_id}' not found")
        del db[key]
        return {"message": f"Item '{item_id}' deleted successfully"}

    @classmethod
    async def scan(cls, table_name: str) -> List[Self]:
        db = get_db(table_name)
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
        table_name: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 25,
        offset: int = 0,
    ) -> List[Self]:
        db = get_db(table_name)
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
    async def batch_get_item(cls, table_name: str, ids: List[str]) -> List[Self]:
        return await asyncio.gather(*[cls.get_item(table_name, id) for id in ids])

    @classmethod
    async def batch_write_item(cls, table_name: str, items: List[Self]) -> List[Self]:
        return await asyncio.gather(*[item.put_item(table_name) for item in items])

    @classmethod
    @asyncify
    def update_item(
        cls, table_name: str, item_id: str, updates: list[Dict[str, Any]]
    ) -> Self:
        db = get_db(table_name)
        key = item_id.encode("utf-8")
        item_data = db.get(key)
        if item_data is None:
            raise RPCError(message="Item with id '%s' not found" % item_id)
        item = cls.model_validate_json(item_data.decode("utf-8"))
        assert isinstance(item, dict)
        for field, value in updates:  # type: ignore
            setattr(item, field, value)
        db[key] = item.model_dump_json().encode("utf-8")
        return item


DocumentObject.model_rebuild()


class Error(TypedDict, total=False):
    code: Required[int]
    message: Required[str]
    data: Required[JsonObject]
