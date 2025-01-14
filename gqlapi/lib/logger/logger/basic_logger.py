import logging
# import sentry_sdk
from gqlapi.lib.environ.environ.environ import Environment, get_app

formatter = "%(asctime)s: %(pathname)s %(lineno)d [" + get_app() + "] %(levelname)s: %(message)s"
logging.basicConfig(level=logging.INFO, format=formatter)


def get_logger(name: str, level: int = logging.INFO, env: Environment = Environment.LOCAL) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if env == Environment.STAGING or env == Environment.PROD:
        # sentry_sdk.init(
        #     "https://055db74457b6444892deb3388e582bf0@o1148881.ingest.sentry.io/6220401",

        #     # Set traces_sample_rate to 1.0 to capture 100%
        #     # of transactions for performance monitoring.
        #     # We recommend adjusting this value in production.
        #     traces_sample_rate=1.0
        # )
        pass
    return logger


class Logger:
    def __init__(self, env: Environment):
        # Init logger based on environment
        pass
