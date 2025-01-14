from typing import List
import logging
from starlette.routing import Router

from gqlapi.lib.future.future.future import asynchronize


class AsyncRoute:
    def __init__(self, path, name=None, methods=[], fn=None, prefix=None):
        self.name = name
        self.path = path
        self.methods = methods
        self.prefix = prefix
        # Asynchronize response
        self.fn = asynchronize(fn)


class AsyncRouter:
    def __init__(self, logger: logging.Logger):
        self._router = Router()
        self.logger = logger

    def attach_routes(self, routes: List[AsyncRoute]):
        """ Add routes to Starlette Server

        Args:
            routes (List[AsyncRoute]): List of Routes
        """
        for route in routes:
            self._router.add_route(
                route.path,
                route.fn,
                route.methods,
                route.name,
            )

    def get_router(self) -> Router:
        """ Router getter

        Returns:
            Router
        """
        return self._router
