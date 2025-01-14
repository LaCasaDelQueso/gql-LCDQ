from abc import ABC, abstractmethod
from typing import Any

from gqlapi.lib.future.future.deprecation import deprecated


class CoreRepositoryInterface(ABC):
    @deprecated("Use add() instead", "domain")
    @abstractmethod
    def new(self, *args) -> Any:
        raise NotImplementedError

    @deprecated("Use fetch() instead", "domain")
    @abstractmethod
    def get(self, *args) -> Any:
        raise NotImplementedError

    @deprecated("Use edit() instead", "domain")
    @abstractmethod
    def update(self, *args) -> bool:
        raise NotImplementedError

    # @abstractmethod
    # def exists(self, *args) -> None:
    #     raise NotImplementedError

    @abstractmethod
    def add(self, *args) -> Any:
        raise NotImplementedError

    @abstractmethod
    def fetch(self, *args) -> Any:
        raise NotImplementedError

    @abstractmethod
    def edit(self, *args) -> Any:
        raise NotImplementedError

    @abstractmethod
    def execute(self, *args):
        raise NotImplementedError

    @abstractmethod
    def raw_query(self, **kwargs) -> Any:
        raise NotImplementedError
