import asyncio
import logging
import random
from string import ascii_letters, digits, punctuation

import orjson
from fastapi import WebSocket
from pydantic import Field

from realitydb import DocumentObject, RPCClient, RPCError, RPCResponse, RPCServer

logger = logging.getLogger(__name__)  # Se arregla la obtención del logger


# Función para generar un string aleatorio de longitud dada
def random_string(length: int) -> str:
    return "".join(random.choices(ascii_letters + digits + punctuation, k=length))


# Función para generar un ID aleatorio
def random_id() -> int:
    return random.randint(0, 2**64 - 1)


class Expert(DocumentObject):
    name: str = Field(default_factory=lambda: random_string(64))
    age: int = Field(
        default_factory=lambda: random.randint(0, 100)
    )  # Rango de edad más razon


# Instancia del servidor RPC
app = RPCServer(document_classes=[Expert])


async def main():
    await app.start()


if __name__ == "__main__":
    asyncio.run(main())
