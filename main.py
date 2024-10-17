import asyncio
import logging
import random
from string import ascii_letters, digits, punctuation

import orjson
from realitydb.models import DocumentObject
from realitydb.rpc_server import RPCResponse, RPCServer
from realitydb.utils import RPCError
from fastapi import WebSocket
from pydantic import Field

logger = logging.getLogger(__name__)  # Se arregla la obtención del logger


# Función para generar un string aleatorio de longitud dada
def random_string(length: int) -> str:
    return "".join(random.choices(ascii_letters + digits + punctuation, k=length))


# Función para generar un ID aleatorio
def random_id() -> int:
    return random.randint(0, 2**64 - 1)


# Instancia del servidor RPC
app = RPCServer()


# Modelo de Expert
class Expert(DocumentObject):
    name: str = Field(default_factory=lambda: random_string(64))
    age: int = Field(
        default_factory=lambda: random.randint(0, 100)
    )  # Rango de edad más razonable


@app.websocket("/rpc")
async def serve(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Genera una respuesta con un objeto Expert
            response = RPCResponse[Expert](data=Expert(), error=None)

            # Loggear la respuesta como JSON
            logger.info(
                orjson.dumps(response.model_dump(), option=orjson.OPT_SERIALIZE_NUMPY)
            )

            # Enviar la respuesta como JSON
            await websocket.send_json(response.model_dump())

            # Pausar el bucle por 1 segundo
            await asyncio.sleep(1)
    except (RPCError, Exception) as e:
        # Captura errores y logea detalles
        logger.error("Error in websocket: %s", e)
        await websocket.close()
