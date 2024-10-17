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

    def __getattr__(self, attr: str) -> object:
        proxied = self.__get_proxied__()
        if isinstance(proxied, LazyProxy):
            return proxied  # pyright: ignore
        return getattr(proxied, attr)

    @override
    def __repr__(self) -> str:
        proxied = self.__get_proxied__()
        if isinstance(proxied, LazyProxy):
            return proxied.__class__.__name__
        return repr(self.__get_proxied__())

    @override
    def __str__(self) -> str:
        proxied = self.__get_proxied__()
        if isinstance(proxied, LazyProxy):
            return proxied.__class__.__name__
        return str(proxied)

    @override
    def __dir__(self) -> Iterable[str]:
        proxied = self.__get_proxied__()
        if isinstance(proxied, LazyProxy):
            return []
        return proxied.__dir__()

    @property  # type: ignore
    @override
    def __class__(self) -> type:  # pyright: ignore
        proxied = self.__get_proxied__()
        if issubclass(type(proxied), LazyProxy):
            return type(proxied)
        return proxied.__class__

    def __get_proxied__(self) -> T:
        return self.__load__()

    def __as_proxied__(self) -> T:
        """Helper method that returns the current proxy, typed as the loaded object"""
        return cast(T, self)

    @abstractmethod
    def __load__(self) -> T:
        ...


@dataclass
class DocumentFile(LazyProxy[T], ABC):
    file: T = field(init=False)
    name: str = field(init=False)
    size: int = field(init=False)
    content_type: str = field(init=False)

    def __post_init__(self):
        self.init()

    def init(self):
        self.file = self.__load__()
        self.name = self.name
        self.size = os.path.getsize(self.name)
        guessed_type = mimetypes.guess_type(self.name)[0]  # type: ignore
        if guessed_type is not None:
            self.content_type = guessed_type
        else:
            raise ValueError(f"Could not guess content type for {self.name}")

    @abstractmethod
    def __load__(self) -> T:
        ...

    @abstractmethod
    def extract_text(self) -> Generator[str, None, None]:
        ...

    @abstractmethod
    def extract_images(self) -> Generator[bytes, None, None]:
        ...
