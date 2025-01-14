import logging
import json
import databases
from typing import Any, Dict, List
from abc import ABC, abstractmethod

from databases import DatabaseURL
from gqlapi.lib.environ import environ
from gqlapi.lib.future.future.future import asyncio_run


class ConnectionInterface(ABC):
    @abstractmethod
    def execute(): raise NotImplementedError


class Connection(ConnectionInterface):
    _tablename: str
    _fields: List[Any]

    def __init__(self, config_file, db_name):
        # environ
        env = environ.get_env()
        if env != environ.Environment.PROD:
            pass

        # Read config file
        with open(config_file) as file:
            config = json.load(file)
            logging.info(config)

        # TODO: Build connection URL based on the config file params
        # env_config = config.get(env.name)
        self.url = DatabaseURL(
            "postgres://postgres:1@0.0.0.0:5432/"+db_name)
        self._connect()

    def _connect(self):
        self._conn = databases.Database(self.url)
        asyncio_run(self._conn.connect())

    def fetch(self, query):
        rows = asyncio_run(self._conn.fetch_all(query=query))
        return [dict(r) for r in rows]

    """
    Direct databases methods using blocking calls to flatten the code
    """

    def execute(self, *args, **kwargs):
        # TODO: Add error handling, alerting, monitoring
        return asyncio_run(self._conn.execute(*args, **kwargs))

    def fetch_one(self, *args, **kwargs):
        # TODO: Add error handling, alerting, monitoring
        return asyncio_run(self._conn.fetch_one(*args, **kwargs))

    def fetch_all(self, *args, **kwargs):
        # TODO: Add error handling, alerting, monitoring
        return asyncio_run(self._conn.fetch_all(*args, **kwargs))

    def get_one(self, qry: str, vals: Dict, warn_msg: str) -> Dict:
        """ Get one record

        Parameters
        ----------
        qry : str
            SQL Query
        vals : Dict
            Key-value elements to query
        warn_msg : str
            Warning message in case of error

        Returns
        -------
        Dict
            Queried data record (empty if not existant)
        """
        try:
            resp = asyncio_run(self._conn.fetch_one(query=qry, values=vals))
            if not resp:
                return {}
            return dict(resp)
        except Exception as ex:
            logging.warning(warn_msg)
            logging.error(ex)
            return {}

    def save(self) -> bool:
        """ Save record

        Returns
        -------
        bool
            Flag validating record was saved
        """
        _keys = []
        _vals = {}
        for x in self._fields:
            if x in self.__dict__:
                _keys.append(x)
                _vals[x] = self.__dict__[x]

        query = f"""INSERT INTO {self._tablename} ( {', '.join(_keys)} )
                    VALUES ( {', '.join([':'+k for k in _keys])} )"""
        try:
            asyncio_run(self._conn.execute(
                query=query,
                values=_vals
            ))
        except Exception as e:
            logging.warning(f"Could not save `{self._tablename}`")
            logging.error(e)
            return False
        return True
