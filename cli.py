import json
import logging
import sys
import requests
from typing import Dict, List, Type, Any
from pydantic import create_model, BaseModel
from realitydb import DocumentObject
from realitydb.rpc_server import RPCServer
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def openapi_type_to_python(openapi_type: str) -> Any:
    type_mapping = {
        'string': str,
        'integer': int,
        'number': float,
        'boolean': bool,
        'array': List[Any],
        'object': Dict[str, Any]
    }
    return type_mapping.get(openapi_type, Any)

def generate_document_classes(openapi_spec: Dict) -> Dict[str, Type[DocumentObject]]:
    document_classes = {}
    schemas = openapi_spec.get('components', {}).get('schemas', {})
    
    for schema_name, schema in schemas.items():
        if schema.get('type') == 'object':
            properties = schema.get('properties', {})
            field_definitions = {}
            for field_name, field_info in properties.items():
                field_type = openapi_type_to_python(field_info.get('type', 'string'))
                field_definitions[field_name] = (field_type, ...)
            
            # Create a new class that inherits from both BaseModel and DocumentObject
            new_class = create_model(
                schema_name,
                __base__=(DocumentObject, BaseModel),
                **field_definitions
            )
            
            document_classes[schema_name] = new_class
    
    return document_classes

async def run_server_(openapi_spec: Dict[str, Any], host: str = 'localhost', port: int = 8888):
    try:
        # Generate document classes from the OpenAPI spec
        document_classes = generate_document_classes(openapi_spec)
        
        if not document_classes:
            logger.warning("No document classes were generated from the OpenAPI spec.")
            return

        logger.info(f"Generated document classes: {', '.join(document_classes.keys())}")

        # Initialize the RPCServer with the generated document classes
        server = RPCServer(list(document_classes.values()), host=host, port=port)

        # Start the server
        logger.info("Starting RPC Server, Listening on:")
        logger.info(f" ws://{host}:{port}")
        await server.start()

    except Exception as e:
        logger.exception(f"An error occurred while starting the server: {e}")
        raise

# Update the run_server function to use the new run_server_
def run_server():
    try:
        args = sys.argv[1:]
        file_path = args[0] if args else "openapi.json"
    except Exception as e:
        logger.warning(f"No file path provided, defaulting to 'openapi.json'. Error: {e}")
        file_path = "openapi.json"

    try:
        if file_path.startswith("http"):
            logger.info(f"Fetching OpenAPI spec from URL: {file_path}")
            response = requests.get(file_path)
            response.raise_for_status()  # Raise an exception for bad status codes
            open_api_spec = response.json()
        else:
            logger.info(f"Reading OpenAPI spec from file: {file_path}")
            with open(file_path, 'r') as f:
                open_api_spec = json.load(f)
        asyncio.run(run_server_(open_api_spec))
    except requests.RequestException as e:
        logger.error(f"Failed to fetch OpenAPI spec from URL: {e}")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse OpenAPI spec: {e}")
    except FileNotFoundError:
        logger.error(f"OpenAPI spec file not found: {file_path}")
    except Exception as e:
        logger.exception(f"An unexpected error occurred: {e}")