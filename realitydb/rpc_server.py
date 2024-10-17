from __future__ import annotations

import asyncio
import random
from abc import ABC, abstractmethod
from string import ascii_letters, digits, punctuation
from typing import Any, Dict, Generic, List, Type, TypeVar, Union
from uuid import uuid4

import base64c as base64  # type: ignore
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, WebSocketException
from pydantic import BaseModel, Field  # type: ignore

from .models import DocumentObject, GlowMethod
from .utils import get_logger

logger = get_logger(__name__)

# Type Aliases
DataObject = Union[
    Dict[str, Any],
    List[Dict[str, Any]],
    str,
    int,
    float,
    bool,
    DocumentObject,
    List[DocumentObject],
    None,
]

O = TypeVar("O", bound=DocumentObject)

STRINGS = ascii_letters + digits + punctuation


def random_string(length: int) -> str:
    return "".join(random.choices(STRINGS, k=length))


def random_id() -> int:
    return random.randint(0, 2**64 - 1)


class Request(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    data: DataObject = Field(default=None)
    method: GlowMethod

    model_config = {
        "json_encoders": {
            DocumentObject: lambda v: v.model_dump_json(),
            bytes: lambda v: base64.b64encode(v).decode(),
        },
        "arbitrary_types_allowed": True,
        "extra": "allow",
    }


class RPCResponse(BaseModel, Generic[O]):
    id: str
    error: DataObject = Field(default={})
    data: O | list[O] = Field(default=[])

    @classmethod
    def __class_getitem__(cls, item: Type[O]):  # type: ignore
        cls.model = item
        return cls

    model_config = {
        "json_encoders": {
            DocumentObject: lambda v: v.model_dump_json(),
            bytes: lambda v: base64.b64encode(v).decode(),
        },
        "arbitrary_types_allowed": True,
        "extra": "allow",
    }


class AbstractRPCHandler(APIRouter, Generic[O], ABC):
    model: Type[O]

    @classmethod
    def __class_getitem__(cls, item: Type[O]):
        cls.model = item
        return cls

    @abstractmethod
    async def handler(
        self, *, websocket: WebSocket, path: GlowMethod, instance: O | None = None
    ) -> O | list[O]:
        ...

    async def serve(self, *, websocket: WebSocket, method: GlowMethod):
        while True:
            await websocket.accept()
            try:
                data = await websocket.receive_json(mode="json")
                instance = self.model(**data) if data else None
                response = await self.handler(
                    websocket=websocket, path=method, instance=instance
                )

                if isinstance(response, list):
                    await asyncio.gather(
                        *[
                            websocket.send_json(r.model_dump(), mode="json")
                            for r in response
                        ]
                    )
                else:
                    await websocket.send_json(response.model_dump(), mode="json")
                await asyncio.sleep(0.1)
            except (WebSocketDisconnect, WebSocketException) as e:
                logger.error("Error in RPC server: %s", e)
                break
            except Exception as e:
                logger.error("Unexpected error in RPC server: %s", e)
                break
            finally:
                await websocket.close()


class Skill(DocumentObject):
    level: int
    label: str


class RPCServer(AbstractRPCHandler[Skill]):
    async def handler(
        self, *, websocket: WebSocket, path: GlowMethod, instance: Skill | None = None
    ) -> Skill | list[Skill]:
        return Skill(label=random_string(64), level=random.randint(0, 2**63))

