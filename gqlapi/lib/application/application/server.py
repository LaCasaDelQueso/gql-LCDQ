import logging
from abc import ABC, abstractmethod

import uvicorn
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.authentication import AuthenticationBackend

from gqlapi.lib.application.application.router import AsyncRouter
from gqlapi.lib.application.application.base import StarlettBaseApp
from gqlapi.lib.environ.environ import environ

HOST_DEFAULT = '0.0.0.0'


class ServerInterface(ABC):
    @abstractmethod
    def start(self):
        raise NotImplementedError

    @abstractmethod
    def stop(self):
        raise NotImplementedError


class AsyncRouterServer(ServerInterface):
    def __init__(self,
                 app_name: str,
                 version: str,
                 router: AsyncRouter,
                 logger: logging.Logger,
                 ):
        self.app_name = app_name
        self.version = version
        self.app = router._router
        self.logger = logger
        self.port = environ.get_port()
        self.host = HOST_DEFAULT

    def add_cors_middleware(self):
        """ Add Starlette CORS middle ware to app
        """
        self.app = CORSMiddleware(
            app=self.app,
            allow_origins=['*'],
            allow_methods=['*'],
            allow_headers=[
                'X-Requested-With',
                'Content-Type',
                'Authorization'
            ],
            allow_credentials=True
        )

    def start(self, host: str = '0.0.0.0', port: int = 8000, log_level: str = 'info'):
        """ Start Uvicorn server running Starlette App

        Args:
            host (str, optional): Host. Defaults to '0.0.0.0'.
            port (int, optional): Port. Defaults to 8000.
            log_level (str, optional): Log Level. Defaults to 'info'.
        """
        # update host & port upon params
        if host:
            self.host = host
        if port:
            self.port = port
        self.logger.info("Starting application {} host {} port {}".format(
            self.app_name,
            self.host,
            self.port
        ))

        uvicorn.run(
            app=self.app,
            host=self.host,
            port=self.port,
            log_level=log_level
        )

    def stop(self):
        pass


class StarletteServer(ServerInterface):
    def __init__(self,
                 app: StarlettBaseApp,
                 version: str,
                 logger: logging.Logger,
                 ):
        self.version = version
        self.app = app
        self.logger = logger
        self.port = environ.get_port()
        self.host = HOST_DEFAULT

    def add_cors_middleware(self):
        """ Add Starlette CORS Middleware to app
        """
        self.app.starlette.add_middleware(
            CORSMiddleware,
            allow_origins=['*'],
            allow_methods=['*'],
            allow_headers=[
                'X-Requested-With',
                'Content-Type',
                'Authorization'
            ],
            allow_credentials=True
        )

    def add_auth_middleware(self, auth_backend: AuthenticationBackend):
        """ Add Starlette Authentication Middleware to app

        Parameters
        ----------
        auth_backend : AuthenticationBackend
            _description_
        """
        self.app.starlette.add_middleware(
            AuthenticationMiddleware,
            backend=auth_backend
        )

    def start(self, host: str = '0.0.0.0', port: int = 8000, log_level: str = 'info'):
        """ Start Uvicorn server running Starlette App

        Args:
            host (str, optional): Host. Defaults to '0.0.0.0'.
            port (int, optional): Port. Defaults to 8000.
            log_level (str, optional): Log Level. Defaults to 'info'.
        """
        # update host & port upon params
        if host:
            self.host = host
        if port:
            self.port = port
        self.logger.info("Starting application {} host {} port {}".format(
            self.app.app_name,
            self.host,
            self.port
        ))

        uvicorn.run(
            app=self.app.starlette,
            host=self.host,
            port=self.port,
            log_level=log_level
        )

    def stop(self):
        pass
