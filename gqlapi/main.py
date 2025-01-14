import sys
from databases import Database
from gqlapi.handlers.services.authos import (
    AuthosTokenHandler,
    EcommerceSessionHandler,
    EcommerceUserHandler,
)
from gqlapi.lib.clients.clients.firebaseapi.firebase_auth import FirebaseAuthApi
from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.repository.services.authos import (
    AuthosEcommerceUserRepository,
    AuthosUserSessionRepository,
)

from starlette.responses import JSONResponse

from gqlapi.lib.application.application.server import StarletteServer
from gqlapi import __version__
from gqlapi import config
from gqlapi.app import GraphqlAPIApp
from gqlapi.app.schema import schema
from gqlapi.db import (
    db_startup,
    db_shutdown,
    database as sql_database,
    authos_database as authos_sql_database,
)
from gqlapi.mongo import mongo_db
from gqlapi.auth import initialize_firebase, AlimaAuthBackend
from gqlapi.repository.user.firebase import FirebaseTokenRepository

# application vars
app_name = get_app()

# version default endpoint


async def version_endp(request):  # noqa
    return JSONResponse({"version": __version__}, status_code=200)


def build_authos_handler(db: Database) -> AuthosTokenHandler:
    u_sess_handler = EcommerceSessionHandler(
        user_session_repo=AuthosUserSessionRepository(db)
    )
    return AuthosTokenHandler(
        user_session_handler=u_sess_handler,
        ecommerce_user_handler=EcommerceUserHandler(
            user_session_handler=u_sess_handler,
            ecommerce_user_repo=AuthosEcommerceUserRepository(db),
        ),
    )


def main():
    # Create starlette Graphql app
    gql = GraphqlAPIApp(
        app_name=app_name,
        schema=schema,
        firebase_app=initialize_firebase(config.FIREBASE_SERVICE_ACCOUNT),
        firebase_rest_api=FirebaseAuthApi(config.FIREBASE_SECRET_KEY),
        sql_database=sql_database,
        authos_database=authos_sql_database,
        mongo_database=mongo_db,  # type: ignore (safe)
        on_startup=db_startup,
        on_shutdown=db_shutdown,
        debug=config.TESTING,
    )
    gql.attach_routes([("/", version_endp)])  # Version default server
    # Uvicorn server
    server = StarletteServer(gql, __version__, gql.logger)
    server.add_cors_middleware()
    server.add_auth_middleware(
        AlimaAuthBackend(
            FirebaseTokenRepository(gql.fb_app),
            build_authos_handler(authos_sql_database),
        )
    )
    # start server
    gql.logger.info(f"Starting {app_name} app ...")
    server.start(config.APP_HOST, config.APP_PORT)
    gql.logger.info(f"Stopped {app_name} app!")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        main()
