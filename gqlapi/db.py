from glob import glob
import logging
from asyncpg import InvalidCatalogNameError
import databases

from gqlapi.config import (
    DATABASE_AUTHOS_URL,
    DATABASE_URL,
    DATABASE_DEFAULT,
    READ_DATABASE_URL,
    app_path as APP_PATH,
)

database = databases.Database(DATABASE_URL)
read_database = databases.Database(READ_DATABASE_URL)
authos_database = databases.Database(DATABASE_AUTHOS_URL)


async def create_db():
    # find schema file
    _schema = glob(APP_PATH.parent.as_posix() + "/schema.sql")
    if not _schema:
        raise Exception("Could not find schema file!")
    _schema = _schema[0]
    # connect with default DB
    db_url = DATABASE_URL.replace(database=DATABASE_DEFAULT)
    tmp_db = databases.Database(db_url)
    await tmp_db.connect()
    await tmp_db.execute(f"CREATE DATABASE {DATABASE_URL.database}")
    await tmp_db.disconnect()
    logging.info(f"Created database: {DATABASE_URL.database}")
    # connecting to new database
    await database.connect()
    # execute schema
    with open(_schema, "r") as sch_file:
        sch_stmt = sch_file.read()
        for qry in sch_stmt.split(";"):
            logging.debug(f"\nInserting:\n {qry}")
            try:
                await database.execute(qry)
            except Exception as e:
                print(type(e))
                logging.error(e)


async def create_authos_db():
    # find schema file
    _schema = glob(APP_PATH.parent.as_posix() + "/authos_schema.sql")
    if not _schema:
        raise Exception("Could not find schema file!")
    _schema = _schema[0]
    # connect with default DB
    db_url = DATABASE_AUTHOS_URL.replace(database=DATABASE_DEFAULT)
    tmp_db = databases.Database(db_url)
    await tmp_db.connect()
    await tmp_db.execute(f"CREATE DATABASE {DATABASE_AUTHOS_URL.database}")
    await tmp_db.disconnect()
    logging.info(f"Created database: {DATABASE_AUTHOS_URL.database}")
    # connecting to new database
    await database.connect()
    # execute schema
    with open(_schema, "r") as sch_file:
        sch_stmt = sch_file.read()
        for qry in sch_stmt.split(";"):
            logging.debug(f"\nInserting:\n {qry}")
            try:
                await database.execute(qry)
            except Exception as e:
                print(type(e))
                logging.error(e)


async def db_startup():
    logging.info(f"Connecting {DATABASE_URL.database}..")
    # connect to default database
    try:
        await database.connect()
    except InvalidCatalogNameError:
        try:
            await create_db()
        except Exception as e:
            logging.error(e)
            logging.warn("DB engine not initiated!")
    # connect to read database
    await read_database.connect()
    logging.info(f"Connecting {DATABASE_AUTHOS_URL.database}..")
    # connect to authos database
    try:
        await authos_database.connect()
    except InvalidCatalogNameError:
        try:
            await create_authos_db()
        except Exception as e:
            logging.error(e)
            logging.warn("DB engine not initiated!")


async def db_shutdown():
    logging.info(f"Closing connection {DATABASE_URL.database}..")
    await database.disconnect()
    logging.info(f"Closing connection {DATABASE_AUTHOS_URL.database}..")
    await authos_database.disconnect()
