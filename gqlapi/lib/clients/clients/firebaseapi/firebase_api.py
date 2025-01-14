import os
import json
import firebase_admin
from firebase_admin import credentials
from firebase_admin import auth
from firebase_admin import firestore
from gqlapi.lib.environ.environ.environ import Environment, get_env
from typing import Dict
import logging

# TODO turn this var into local
global fire_app
fire_app = None

FIREBASE_SERVICE_ACCOUNT = os.getenv("FIREBASE_SERVICE_ACCOUNT", "")


def get_col_name():
    FIRESTONE_COLL_NAME = os.getenv("FIREBASE_SERVICE_ACCOUNT", '')
    if get_env() == Environment.PROD:
        return FIRESTONE_COLL_NAME + f"-{str(Environment.PROD).lower()}"
    return FIRESTONE_COLL_NAME


def init_firebase():
    global fire_app
    cred = credentials.Certificate(json.loads(FIREBASE_SERVICE_ACCOUNT))
    if fire_app is None:
        fire_app = firebase_admin.initialize_app(cred)
    return fire_app


def get_firebase_client():
    fire_app = init_firebase()
    return firestore.client(fire_app)


class FirebaseClient:
    def __init__(self):
        self._client = get_firebase_client()

    def set_document(self, doc_id: str, doc: Dict):
        self.fire_client.collection(get_col_name())\
            .document(doc_id)\
            .set(doc)

    def validate_token(self, credentials):
        try:
            decoded = auth.verify_id_token(credentials)
        except (auth.InvalidIdTokenError, auth.ExpiredIdTokenError) as exc:
            logging.error(exc)
            raise Exception('Invalid basic auth credentials')
        return decoded
