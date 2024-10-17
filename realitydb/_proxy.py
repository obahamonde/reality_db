from __future__ import annotations

import mimetypes
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Generator, Generic, Iterable, TypeVar, cast

from typing_extensions import override

T = TypeVar("T")


class LazyProxy(Generic[T], ABC):
    """Implements data methods to pretend that an instance is another instance.

    This includes forwarding attribute access and other methods.
    """
    @abstractmethod
    def __load__(self) -> T:
        ...


@dataclass
class DocumentFile(LazyProxy[T], ABC):
    name: str
    size: int = field(init=False)
   
    def __post_init__(self):
        self.init()

    def init(self):
        self.file = self.__load__()
        
        self.size = os.path.getsize(self.name)
      
    @abstractmethod
    def __load__(self) -> T:
        ...

    @abstractmethod
    def extract_text(self) -> Generator[str, None, None]:
        ...

    @abstractmethod
    def extract_images(self) -> Generator[bytes, None, None]:
        ...
