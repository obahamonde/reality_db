# RealityDB

Document-oriented realtime database built on top of RocksDB, tailored for media applications.

## Installation

```bash
pip install realitydb
```

## Usage

```python
from realitydb import DocumentObject

class User(DocumentObject):
    name: str
    age: int
```

```python
async def main():
    user = User(name="John Doe", age=25)
    await user.put()


if __name__ == "__main__":
    asyncio.run(main())
```
