import os
import json
from pathlib import Path

from databases import DatabaseURL
import pytz
from starlette.config import Config
from gqlapi.lib.environ.environ.vault import set_vault_vars

set_vault_vars()
cfg = Config(environ=dict(os.environ))
app_path = Path(__file__).parent

# Server
APP_HOST = "0.0.0.0"  # (do not change)
APP_PORT = 8000  # (do not change)
LOG_LEVEL = cfg("LOG_LEVEL", cast=str, default="INFO")

# application
APP_NAME = cfg("APP_NAME", cast=str, default="ALIMA_GQL_API")
# environment
ENV = cfg("DEV_ENV", cast=str, default="DEV")
assert ENV.lower() in set(
    {"prod", "stg", "dev"}
), f"Invalid Development Environment!, ({ENV}): Only `prod`, `stg` or `dev`"
if ENV.lower() != "prod":
    APP_NAME += "-" + ENV.lower()
try:
    _testing = cfg("TESTING", cast=str, default="false")
    TESTING = _testing == "true"
except Exception:
    TESTING = False

environment = ENV.lower()
APP_TZ = pytz.timezone("America/Mexico_City")

# Env Vars
STRIPE_API_KEY = cfg("STRIPE_API_KEY", cast=str, default="")
STRIPE_API_SECRET = cfg("STRIPE_API_SECRET", cast=str, default="")
KALTO_USERNAME = cfg("KALTO_USERNAME", cast=str, default="")
KALTO_PASSWORD = cfg("KALTO_PASSWORD", cast=str, default="")
KALTO_X_MERCHANT_KEY = cfg("KALTO_X_MERCHANT_KEY", cast=str, default="")
FACT_USR = cfg("FACT_USR", cast=str, default="")
FACT_PWD = cfg("FACT_PWD", cast=str, default="")
AUTHOS_SECRET_KEY = cfg(
    "AUTHOS_SECRET_KEY",
    cast=str,
    default="bc908639ecdb6f3f21e15af14c2580f3aaa68ad7099de693d41ffe3924eff12d",
)
AUTHOS_ALGORITHM = "HS256"
AUTHOS_TOKEN_TTL = 7  # days

# Aux services
FIREBASE_SERVICE_ACCOUNT = cfg(
    "FIREBASE_SERVICE_ACCOUNT", cast=json.loads, default="{}"
)
FIREBASE_SECRET_KEY = cfg("FIREBASE_SECRET_KEY", cast=str, default="")
SENDGRID_API_KEY = cfg("SENDGRID_API_KEY", cast=str, default="")
SENDGRID_SINGLE_SENDER = cfg("SENDGRID_SINGLE_SENDER", cast=str, default="")
RESEND_API_KEY = cfg("RESEND_API_KEY", cast=str, default="")
RESEND_SINGLE_SENDER = cfg("RESEND_SINGLE_SENDER", cast=str, default="")
HILOS_API_KEY = cfg("HILOS_API_KEY", cast=str, default="")
CLOUDINARY_BASE_URL = (
    "https://res.cloudinary.com/neutro-mx/image/upload/c_scale,f_auto,q_auto,"
)

# database SQL
DATABASE_DEFAULT = cfg("RDS_DB_NAME", cast=str, default="postgres")
DATABASE_NAME = cfg("DB_NAME", cast=str, default="alima_marketplace")
DATABASE_HOST = cfg("RDS_HOSTNAME", cast=str, default="localhost")
DATABASE_READONLY_HOST = cfg("RDS_READ_HOSTNAME", cast=str, default=DATABASE_HOST)
DATABASE_PORT = cfg("RDS_PORT", cast=str, default="5432")
DATABASE_USER = cfg("RDS_USERNAME", cast=str, default="postgres")
DATABASE_PSWD = cfg("RDS_PASSWORD", cast=str, default="")
DATABASE_URL = DatabaseURL(
    f"postgres://{DATABASE_USER}:{DATABASE_PSWD}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"
)
READ_DATABASE_URL = DatabaseURL(
    f"postgres://{DATABASE_USER}:{DATABASE_PSWD}@{DATABASE_READONLY_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"
)
if ENV.lower() != "prod":
    DATABASE_URL = DATABASE_URL.replace(
        database=DATABASE_URL.database + f"_{ENV.lower()}"
    )
    READ_DATABASE_URL = READ_DATABASE_URL.replace(
        database=READ_DATABASE_URL.database + f"_{ENV.lower()}"
    )
# database Authos SQL
DATABASE_AUTHOS_NAME = cfg("DB_AUTHOS_NAME", cast=str, default="authos")
DATABASE_AUTHOS_URL = DatabaseURL(
    f"postgres://{DATABASE_USER}:{DATABASE_PSWD}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_AUTHOS_NAME}"
)
if ENV.lower() != "prod":
    DATABASE_AUTHOS_URL = DATABASE_AUTHOS_URL.replace(
        database=DATABASE_AUTHOS_URL.database + f"_{ENV.lower()}"
    )
# database Mongo
MONGO_DB_NAME = cfg("MONGO_DB_NAME", cast=str, default="alima_business")
MONGO_URI = cfg("MONGO_URI", cast=str, default="mongodb://localhost:27017")
if ENV.lower() != "prod":
    MONGO_DB_NAME = MONGO_DB_NAME + f"_{ENV.lower()}"
MONGO_SECRET_BYPASS = cfg("MONGO_SECRET_BYPASS", cast=str, default="")
# algolia
ALGOLIA_APP_ID = cfg("ALGOLIA_APP_ID", cast=str, default="")
ALGOLIA_SEARCH_KEY = cfg("ALGOLIA_SEARCH_KEY", cast=str, default="")
ALGOLIA_INDEX_NAME = cfg("ALGOLIA_INDEX_NAME", cast=str, default="")

# retool
RETOOL_SECRET_BYPASS = cfg("RETOOL_SECRET_BYPASS", cast=str, default="")

# support contact
ALIMA_SUPPORT_PHONE = "7751084135"
ALIMA_EXTERNAL_RESTO_REVIEW = "https://app.alima.la/ext/review/client/"
ALIMA_EXTERNAL_SUPPLIER_REVIEW = "https://app.alima.la/ext/review/supplier/"

# constants
ALIMA_ADMIN_BUSINESS = {
    "dev": os.getenv("ALIMA_ADMIN_BUSINESS", ""),
    "stg": "9145f549-a3bb-437e-847b-7ee5b7a65473",  # fixed
    "prod": "b9e6c097-aa67-4132-8326-3516140e06c6",  # fixed
}.get(ENV.lower(), "")

ALIMA_ADMIN_BRANCH = {
    "dev": os.getenv("ALIMA_ADMIN_BRANCH", ""),
    "stg": "51e18f7e-5283-4685-b7c0-28f70ba5647d",  # fixed
    "prod": "d858e206-0fe3-49d0-8f02-5e7dda241176",  # fixed
}.get(ENV.lower(), "")

ALIMA_EXPEDITION_PLACE = {
    "dev": "15830",
    "stg": "15830",  # fixed
    "prod": "06100",  # fixed
}.get(ENV.lower(), "")

# Scorpions VARS
SCORPION_USER = cfg("SCORPION_USER", cast=str, default="")
SCORPION_PASSWORD = cfg("SCORPION_PASSWORD", cast=str, default="")

# Vercel VARS
VERCEL_TOKEN = cfg("VERCEL_TOKEN", cast=str, default="")
VERCEL_TEAM = cfg("VERCEL_TEAM", cast=str, default="")

# Go Daddy VARS
GODADDY_API_KEY = cfg("GODADDY_API_KEY", cast=str, default="")
GODADDY_API_SECRET = cfg("GODADDY_API_SECRET", cast=str, default="")
GODADDY_DOMAIN = cfg("GODADDY_DOMAIN", cast=str, default="")
