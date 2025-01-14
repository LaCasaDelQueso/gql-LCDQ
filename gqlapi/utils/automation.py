import logging
from typing import Optional
from databases import Database
from pymongo.database import Database as MongoDatabase
from gqlapi.lib.clients.clients.firebaseapi.firebase_auth import FirebaseAuthApi


class DataContext:
    sql: Optional[Database]
    mongo: Optional[MongoDatabase]
    firebase: Optional[FirebaseAuthApi]
    authos: Optional[Database]


class InjectedStrawberryInfo:
    def __init__(self, db, mongo, authos=None):
        db_ctx = DataContext()
        db_ctx.sql = db
        db_ctx.mongo = mongo
        db_ctx.authos = authos
        self.context = {"db": db_ctx}
        logging.info(f"InjectedStrawberryInfo created: SQL: {db}, Mongo: {mongo}, Authos: {authos}")
