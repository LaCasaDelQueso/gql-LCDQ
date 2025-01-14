from datetime import timedelta
from types import NoneType
from typing import Any, Callable, Optional, Sequence
from gqlapi.endpoints.alima_account.stripe import (
    StripeWebHookListener,
    StripeWebHookListenerTransferAutoPayments,
)
from gqlapi.endpoints.retool.data_orchestration import RetoolWorkflowJob
from gqlapi.utils.automation import DataContext

from starlette.requests import Request
from starlette.websockets import WebSocket
from starlette.responses import Response
from strawberry.schema import BaseSchema, Schema as StrawberrySchema
from strawberry.asgi import GraphQL
from firebase_admin import App as FirebaseApp
from databases import Database
from pymongo.database import Database as MongoDatabase

from gqlapi.lib.clients.clients.firebaseapi.firebase_auth import FirebaseAuthApi
from gqlapi.lib.application.application.base import StarlettBaseApp
from gqlapi.lib.environ.environ.environ import get_env
from gqlapi.domain.models.v2.utils import T
from gqlapi.endpoints.retool.retool_resource import RetoolResource


class AuthedGraphQL(GraphQL):
    def __init__(
        self,
        schema: BaseSchema,
        graphiql: bool = False,
        allow_queries_via_get: bool = True,
        keep_alive: bool = False,
        keep_alive_interval: float = 1,
        debug: bool = False,
        subscription_protocols: Sequence[str] = ...,
        connection_init_wait_timeout: timedelta = ...,
        firebase_rest_api: Optional[FirebaseAuthApi] = None,
        sql_database: Optional[Database] = None,
        authos_database: Optional[Database] = None,
        mongo_database: Optional[MongoDatabase] = None,
        # [TODO] update into correct interface
        auth_permissions_repo_class: Optional[T] = None,
    ) -> None:
        super().__init__(
            schema,
            graphiql,
            allow_queries_via_get,
            keep_alive,
            keep_alive_interval,
            debug,
            subscription_protocols,
            connection_init_wait_timeout,
        )
        # SQL connection
        self._sql = sql_database if sql_database is not None else None
        # Authos SQL connection
        self._authos = authos_database if authos_database is not None else None
        # MONGO connection
        self._mongo = mongo_database if mongo_database is not None else None
        # Firebase Auth API connection
        self._firebase_rest_api = (
            firebase_rest_api if firebase_rest_api is not None else None
        )
        # add auth permissions repo
        self._auth_permissions_repo = (
            auth_permissions_repo_class(sql_database)  # type: ignore
            if auth_permissions_repo_class
            else None
        )

    @property
    def sql(self) -> Database | NoneType:
        return self._sql

    @property
    def authos(self) -> Database | NoneType:
        return self._authos

    @property
    def mongo(self) -> MongoDatabase | NoneType:
        return self._mongo

    @property
    def firebase(self) -> FirebaseAuthApi | NoneType:
        return self._firebase_rest_api

    @property
    def auth_permissions_repo(self) -> T | NoneType:
        return self._auth_permissions_repo

    async def get_context(
        self, request: Request | WebSocket, response: Optional[Response] = None
    ) -> Any:
        _db = DataContext()
        # Add SQL database connection
        if self.sql is not None:
            _db.sql = self.sql
        # Add Authos database connection
        if self.authos is not None:
            _db.authos = self.authos
        # Add Mongo database connection
        if self.mongo is not None:
            _db.mongo = self.mongo
        # Add Firebase Auth API connection
        if self.firebase is not None:
            _db.firebase = self.firebase
        # Ref: https://strawberry.rocks/docs/integrations/asgi
        # Ref: https://strawberry.rocks/docs/guides/authentication
        # [TODO] perform permissions request from DB
        # [TODO] add permissions to request.user['permissions']
        return {"request": request, "response": response, "db": _db}


class GraphqlAPIApp(StarlettBaseApp):
    def __init__(
        self,
        app_name: str,
        schema: StrawberrySchema,
        firebase_app: FirebaseApp,
        firebase_rest_api: FirebaseAuthApi,
        sql_database: Database | NoneType = None,
        authos_database: Database | NoneType = None,
        mongo_database: MongoDatabase | NoneType = None,
        on_startup: Callable | NoneType = None,
        on_shutdown: Callable | NoneType = None,
        debug: bool = False,
    ):
        super().__init__(app_name=app_name)
        self.env = get_env()
        # Add GraphQL schema to app
        self._gql_app = AuthedGraphQL(
            schema,
            graphiql=debug,
            firebase_rest_api=firebase_rest_api,
            sql_database=sql_database,
            authos_database=authos_database,
            mongo_database=mongo_database,
        )
        self.starlette.add_route("/graphql", self._gql_app)
        self.starlette.add_websocket_route("/graphql", self._gql_app)
        self.starlette.add_route("/retool", RetoolResource, methods=["GET"])
        self.starlette.add_route("/data_orch", RetoolWorkflowJob, methods=["POST"])
        self.starlette.add_route(
            "/webhook/stripe-payment-intent", StripeWebHookListener, methods=["POST"]
        )
        self.starlette.add_route(
            "/webhook/stripe-payment-intent/{supplier_business_id}",
            StripeWebHookListenerTransferAutoPayments,
            methods=["POST"],
        )
        # Add Firebase app
        self._fb_app = firebase_app
        # On start / shutdown events
        if on_startup:
            self.add_on_start_event(on_startup)
        if on_shutdown:
            self.add_on_shutdown_event(on_shutdown)

    @property
    def gql_app(self) -> AuthedGraphQL:
        return self._gql_app

    @property
    def fb_app(self) -> FirebaseApp:
        return self._fb_app
