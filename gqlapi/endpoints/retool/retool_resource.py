import logging
from typing import Any, Dict
from uuid import UUID
from bson import Binary
from starlette.responses import JSONResponse
import json

from starlette.endpoints import HTTPEndpoint
from gqlapi import repository

from gqlapi.mongo import mongo_db
from gqlapi.config import MONGO_SECRET_BYPASS

mongo_collections = [
    "restaurant_business_account",
    "restaurant_employee_directory",
    "supplier_business_account",
    "supplier_employee_directory",
    "supplier_registration_status",
    "supplier_unit_delivery_info",
]

mongo_methods = ["delete", "fetch", "insert", "update"]


class RetoolResource(HTTPEndpoint):
    """[summary]

    Parameters
    ----------
    request : starlette.requests.Request

    Returns
    -------
    starlette.responses.JSONResponse
    """

    async def get(self, request):
        """Get Products by search key

        Parameters
        ----
        request: starlette.requests.Request

        Returns:
        ----
        starlette.response.JSONResponse
        """
        try:
            resp = await request.body()
            resp_decode = resp.decode("utf-8").replace("'", '"')
            data = json.loads(resp_decode)
            if (
                "password" not in data
                or "method" not in data
                or "collection" not in data
                or "query" not in data
            ):
                return JSONResponse(
                    {"error": "Missing query parameters", "status": "error"},
                    status_code=400,
                )
            if data["password"] != MONGO_SECRET_BYPASS:
                return JSONResponse(
                    {"error": "Access Denied", "status": "error"}, status_code=401
                )
            if data["method"] not in mongo_methods:
                return JSONResponse(
                    {"error": data["method"] + " doesnt' exists"}, status_code=400
                )
            if data["collection"] not in mongo_collections:
                return JSONResponse(
                    {
                        "error": data["collection"] + " doesn't exists",
                        "status": "error",
                    },
                    status_code=400,
                )

            # for fields in data["query"]:
            #     if "type" not in fields or "key" not in fields or "value" not in fields:
            #         return JSONResponse(
            #             {"error": "Missing `query` parameters", "status": "error"},
            #             status_code=400,
            #         )
            #     if fields["type"] not in ["uuid", "float", "string", "list"]:
            #         return JSONResponse(
            #             {
            #                 "error": fields["type"] + "Missing `query` parameters",
            #                 "status": "error",
            #             },
            #             status_code=400,
            #         )

            #     core_query = get_core_query(core_query=core_query, fields=fields)
            if "query_schema" in data and data["query_schema"]:
                data["query"] = retool_decode_to_mongo(
                    schema=data["query_schema"], query=data["query"]
                )

            mongo_repo = repository.CoreMongoBypassRepository(mongo_db=mongo_db)  # type: ignore
            if data["method"] == "delete":
                data_resp = await mongo_repo.delete_many(
                    core_element_collection=data["collection"],
                    core_element_name=data["collection"],
                    core_query=data["query"],
                )
                return JSONResponse(
                    {"data": data_resp.deleted_count, "status": "ok"}, status_code=200
                )

            if data["method"] == "fetch":
                data_resp = await mongo_repo.fetch_many(
                    core_element_collection=data["collection"],
                    core_element_name=data["collection"],
                    query=data["query"],
                )

                if data_resp:
                    if data["values_schema"]:
                        for data_r in data_resp:
                            data_r = mongo_decode_to_retool(
                                values_schema=data["values_schema"], data_values=data_r
                            )
                return JSONResponse(
                    {"data": data_resp, "status": "ok"}, status_code=200
                )

            if data["method"] == "insert":
                data_resp = await mongo_repo.add(
                    core_element_collection=data["collection"],
                    core_element_name=data["collection"],
                    core_values=data["query"],
                )
                if not data_resp:
                    return JSONResponse(
                        {"error": "Error to upload document", "status": "error"},
                        status_code=400,
                    )
                return JSONResponse(
                    {"data": "data_inserted", "status": "ok"}, status_code=200  # type: ignore
                )

            if data["method"] == "update":
                values = retool_decode_to_mongo(
                    query=data["values"], schema=data["values_schema"]
                )
                new_values = {"$set": values}
                data_resp = await mongo_repo.update_one(
                    core_element_collection=data["collection"],
                    core_element_name=data["collection"],
                    core_query=data["query"],
                    core_values=new_values,
                )

                if not data_resp:
                    return JSONResponse(
                        {"error": "Error to upload document", "status": "error"},
                        status_code=400,
                    )
                return JSONResponse(
                    {
                        "data": {
                            "Matched documents": data_resp.matched_count,  # type: ignore
                            "Modified documents": data_resp.modified_count,  # type: ignore
                        },
                        "status": "ok",
                    },
                    status_code=200,
                )

            return JSONResponse(
                {"status": "error", "error": "`method` not supported"}, status_code=200
            )
        except Exception as e:
            logging.error(e)
            return JSONResponse({"error": str(e), "status": "error"}, status_code=400)


# def mongo_decode_to_retool(dr: Dict[Any, Any], fields: Dict[Any, Any]):
#     if fields["type"] == "uuid":
#         dr[fields["key"]] = str(Binary.as_uuid(dr[fields["key"]]))
#     if fields["type"] == "float":
#         dr[fields["key"]] = float(dr[fields["key"]])
#     if fields["type"] == "datetime":
#         dr[fields["key"]] = dr[fields["key"]].strftime("%Y-%m-%d %H:%M:%S.%f")
#     if dr[fields["key"]] == "binary":
#         fields["value"] = dr[fields["key"]].decode("utf-8")
#     if fields["type"] == "list":
#         if not dr[fields["key"]]:
#             return dr
#         for dr_sub in dr[fields["key"]]:
#             for subfields in fields["value"]:
#                 dr_sub = mongo_decode_to_retool(dr=dr_sub, fields=subfields)
#     return dr


def mongo_decode_to_retool(
    data_values: Dict[Any, Any], values_schema: Dict[Any, Any]
) -> Dict[Any, Any]:
    for key, value in values_schema.items():
        if value == "uuid":
            data_values[key] = str(Binary.as_uuid(data_values[key]))
        if value == "float":
            data_values[key] = float(data_values[key])
        if value == "datetime":
            data_values[key] = data_values[key].strftime("%Y-%m-%d %H:%M:%S.%f")
        if value == "binary":
            data_values[key] = data_values[key].decode("utf-8")
        if isinstance(value, list):
            for sub_value in data_values[key]:
                # if key in sub_value.keys():
                sub_value = mongo_decode_to_retool(
                    data_values=sub_value, values_schema=value[0]
                )
    return data_values


# def get_core_query(
#     core_query: Dict[Any, Any], fields: Dict[Any, Any]
# ) -> Dict[Any, Any]:
#     if fields["type"] == "uuid":
#         fields["value"] = Binary.from_uuid(UUID(fields["value"]))
#     if fields["type"] == "float":
#         fields["value"] = float(fields["value"])
#     if fields["type"] == "list":
#         if not fields["value"]:
#             fields["value"] = []
#         else:
#             sub_list = []
#             for sub_fields in fields["value"]:  # type: ignore
#                 sub_list.append(
#                     get_core_query(
#                         core_query={},
#                         fields=sub_fields,
#                     )
#                 )
#             fields["value"] = sub_list
#     del fields["type"]
#     core_query[fields["key"]] = fields["value"]
#     return core_query


def retool_decode_to_mongo(
    query: Dict[Any, Any], schema: Dict[Any, Any]
) -> Dict[Any, Any]:
    for key, value in schema.items():
        if value == "uuid":
            query[key] = Binary.from_uuid(UUID(query[key]))
        if value == "float":
            query[key] = float(query[key])
        if value == "bool":
            query[key] = bool(query[key])
        if isinstance(value, list):
            for sub_query in query[key]:  # type: ignore
                sub_query = retool_decode_to_mongo(
                    query=sub_query,
                    schema=value[0],
                )
    return query


def validate_schema_type(fields: Dict[Any, Any]) -> bool:
    if fields["type"] not in [
        "uuid",
        "float",
        "string",
        "binary",
        "datetime",
        "list",
    ]:
        return False
    return True
