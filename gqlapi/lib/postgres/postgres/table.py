# import logging
# from connection import Connection
# from typing import Dict

# class BaseTable:
#     _tablename = ""
#     _fields = {}

#     def __init__(self, conn: Connection, **kwargs) -> None:
#         self.conn = conn
#         for k,v in kwargs.items():
#             if k in self._fields:
#                 self.__dict__[k] = self._fields[k](v)

#     @staticmethod
#     async def get_one(qry:str, vals:Dict, warn_msg:str) -> Dict:
#         """ Get one record

#         Parameters
#         ----------
#         qry : str
#             SQL Query
#         vals : Dict
#             Key-value elements to query
#         warn_msg : str
#             Warning message in case of error

#         Returns
#         -------
#         Dict
#             Queried data record (empty if not existant)
#         """
#         try:
#             resp = await database.fetch_one(query=qry, values=vals)
#             if not resp:
#                 return {}
#             return dict(resp)
#         except Exception as ex:
#             logging.warning(warn_msg)
#             logging.error(ex)
#             return {}

#     async def save(self) -> bool:
#         """ Save record

#         Returns
#         -------
#         bool
#             Flag validating record was saved
#         """
#         _keys = []; _vals = {}
#         for x in self._fields:
#             if x in self.__dict__:
#                 _keys.append(x)
#                 _vals[x] = self.__dict__[x]

#         query = f"""INSERT INTO {self._tablename} ( {', '.join(_keys)} )
#                     VALUES ( {', '.join([':'+k for k in _keys])} )"""
#         try:
#             await database.execute(
#                 query=query,
#                 values=_vals
#             )
#         except Exception as e:
#             logging.warning(f"Could not save `{self._tablename}`")
#             logging.error(e)
#             return False
#         return True
