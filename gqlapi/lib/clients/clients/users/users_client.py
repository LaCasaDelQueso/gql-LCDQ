from gqlapi.lib.environ.environ.environ import Environment
from gqlapi.domain.models.v1.user import User
from gqlapi.lib.logger.logger.basic_logger import get_logger

logger = get_logger(__name__)
endpoints = {
    Environment.LOCAL: "http://0.0.0.0:8000"
}

timeouts = {
    Environment.LOCAL: 36000,
}

TOKEN_KEY = "Authorization"


class UsersClient(object):
    def __init__(self):
        # Set environment
        # Set timeouts
        pass

    def get_all_users(self):
        pass

    def find_by_id(self, id: str) -> User:
        pass

    def authenticate_token(self, token: str) -> bool:
        # 1. get token from the cookies/headers
        # 2. send token to get validated
        return True

    def authenticate_employee(self, token: str) -> bool:
        # 1. get token from the cookies
        # 2. Decode token and send to user service
        return True
