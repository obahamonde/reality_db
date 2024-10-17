# RealityDB

![Cover](images/landscape.jpeg)

RealityDB is a document-oriented database built on top of `rocksdb`, enhanced by Python extensions such as `base64c`, `orjson`, and `rocksdict` for performance-critical operations. It leverages `pydantic` and `OpenAPI` specifications for seamless data management. By accepting a single `OpenAPI` specification, RealityDB can generate the corresponding Python classes and methods for data handling.

Inspired by AWS DynamoDB, RealityDB includes methods like `CreateTable`, `DeleteTable`, `GetItem`, `PutItem`, `DeleteItem`, `Scan`, `Query`, `BatchGetItem`, `BatchWriteItem`, and `UpdateItem` for efficient data storage and retrieval. It offers real-time capabilities using WebSockets for full-duplex communication.

Primarily intended for media-intensive applications—such as images, audio, video, 3D models, and other binary data—RealityDB meets real-time requirements through its optimized `base64c` and `orjson` extensions.

## Features

- [x] **DynamoDB API Compatibility**
  - Implements methods similar to AWS DynamoDB for seamless integration and data operations.
- [x] **Real-time Communication**
  - Utilizes WebSockets for full-duplex communication, enabling real-time data updates and notifications.
- [x] **OpenAPI Specification Migration**
  - Generates Python classes and methods from a single OpenAPI specification for streamlined data management.
- [ ] **OAuth2 Authentication**
  - Implements OAuth2 protocol for secure authentication and authorization.
- [ ] **Indexing of KeySchema Attributes**
  - Supports indexing of key schema attributes for faster and more efficient queries.
- [ ] **Publish/Subscribe Support**
  - Introduces a Pub/Sub model for real-time data changes and event notifications.
- [ ] **Global Distribution @Edge**
  - Enables global distribution and edge computing capabilities for low-latency access worldwide.
- [ ] **Zstd Compression**
  - Integrates Zstandard (zstd) compression for efficient data storage and transfer.
- [ ] **S3FS Integration with Edge Computing**
  - Integrates with S3FS to provide distributed file system capabilities in edge environments.
- [ ] **Authentication and Multi-tenancy**
  - Supports multi-tenant architectures with robust authentication mechanisms for data isolation and security.

## Installation

Install RealityDB using pip:

```bash
pip install realitydb
```

## Usage

Use your own OpenAPI specification to generate the corresponding Python classes and methods for data handling.

```bash
realitydb ./openapi.json
```

You will see the RPCServer running on `ws://localhost:8888` and the RPCClient ready to use.




