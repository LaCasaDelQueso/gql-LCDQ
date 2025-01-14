from typing import Callable, List, Tuple
from starlette.applications import Starlette

from gqlapi.lib.logger.logger.basic_logger import get_logger
from gqlapi.lib.environ.environ import vault


class BaseApp:
    def __init__(self, app_name: str = ''):
        vault.set_vault_vars()
        _name = app_name if app_name else __name__
        self.app_name = _name
        self.logger = get_logger(_name)


class StarlettBaseApp(BaseApp):
    def __init__(self, app_name: str = ''):
        super().__init__(app_name)
        self._starlette = Starlette()

    @property
    def starlette(self) -> Starlette:
        return self._starlette

    def attach_routes(self, routes: List[Tuple[str, Callable]]):
        """ Attach routes to Starlette APP

        Args:
            routes (List[Tuple[str,Route]]): List of Routes
        """
        for r in routes:
            self.starlette.add_route(*r)

    def add_on_start_event(self, on_start_fn: Callable):
        """ Add On start routine to Starlette app

        Parameters
        ----------
        on_start_fn : Callable
            Event function
        """
        self._starlette.add_event_handler(
            'startup',
            on_start_fn
        )

    def add_on_shutdown_event(self, on_shut_fn: Callable):
        """ Add On shutdown routine to Starlette app

        Parameters
        ----------
        on_start_fn : Callable
            Event function
        """
        self._starlette.add_event_handler(
            'shutdown',
            on_shut_fn
        )
