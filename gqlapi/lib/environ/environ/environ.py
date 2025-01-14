import os

from enum import Enum


class Environment(Enum):
    LOCAL = 'local'
    DEV = 'dev'
    STAGING = 'staging'
    PROD = 'production'


def get_env() -> str | Environment:
    return os.getenv("APP_ENV", Environment.LOCAL.value)


def get_port() -> int:
    return int(os.getenv("APP_PORT", '8000'))


def get_app() -> str:
    return os.getenv("APP_NAME", '(no-app-name)')
