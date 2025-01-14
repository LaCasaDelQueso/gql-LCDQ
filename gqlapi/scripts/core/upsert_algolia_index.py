# """ Script to generate algolia index.

# This script is used to generate the algolia index for the restaurant, and supplier categories.
# Example:
#     cd projects/gqlapi/
#     python -m gqlapi.scripts.core.upsert_algolia_index --help
#     # python -m gqlapi.scripts.core.upsert_algolia_index --env prod --action replace_all
# """
# import argparse
# import asyncio
# import logging
# from typing import Any, Dict, List
# import uuid
# from bson import Binary
# from gqlapi.domain.models.v2.supplier import SupplierUnitDeliveryOptions
# from gqlapi.domain.models.v2.utils import SellingOption, ServiceDay
# from gqlapi.handlers.b2bcommerce.ecommerce_seller import EcommerceSellerHandler
# from gqlapi.handlers.supplier.supplier_business import SupplierBusinessHandler
# from gqlapi.handlers.supplier.supplier_restaurants import SupplierRestaurantsHandler
# from gqlapi.handlers.supplier.supplier_unit import SupplierUnitHandler
# from gqlapi.repository import CoreMongoRepository
# from gqlapi.repository.b2bcommerce.ecommerce_seller import EcommerceSellerRepository
# from gqlapi.repository.core.category import (
#     CategoryRepository,
#     RestaurantBranchCategoryRepository,
#     SupplierUnitCategoryRepository,
# )
# from gqlapi.repository.core.invoice import MxSatCertificateRepository
# from gqlapi.repository.core.product import ProductRepository
# from gqlapi.repository.restaurant.restaurant_branch import RestaurantBranchRepository
# from gqlapi.repository.restaurant.restaurant_business import (
#     RestaurantBusinessAccountRepository,
#     RestaurantBusinessRepository,
# )
# from gqlapi.repository.supplier.supplier_business import (
#     SupplierBusinessAccountRepository,
#     SupplierBusinessRepository,
# )
# from gqlapi.repository.supplier.supplier_product import (
#     SupplierProductPriceRepository,
#     SupplierProductRepository,
#     SupplierProductStockRepository,
# )
# from gqlapi.repository.supplier.supplier_restaurants import (
#     SupplierRestaurantsRepository,
# )
# from gqlapi.repository.supplier.supplier_unit import (
#     SupplierUnitDeliveryRepository,
#     SupplierUnitRepository,
# )
# from gqlapi.repository.supplier.supplier_user import (
#     SupplierUserPermissionRepository,
#     SupplierUserRepository,
# )
# from gqlapi.repository.user.core_user import CoreUserRepository
# from gqlapi.utils.domain_mapper import domain_to_dict
# from gqlapi.utils.helpers import list_into_strtuple
# import pandas as pd

# from gqlapi.lib.environ.environ.environ import Environment, get_env
# from gqlapi.lib.logger.logger.basic_logger import get_logger
# from gqlapi.db import database as SQLDatabase, db_shutdown, db_startup
# from gqlapi.mongo import mongo_db as MongoDatabase
# from gqlapi.algolia import algolia_idx as AlgoliaIndex
# from gqlapi.utils.automation import InjectedStrawberryInfo
# from gqlapi.config import ENV, RETOOL_SECRET_BYPASS
# from tqdm import tqdm


# logger = get_logger(
#     "scripts.upsert_algolia_index", logging.INFO, Environment(get_env())
# )


# # arg parser
# def parse_args() -> argparse.Namespace:
#     """Parse the command line arguments."""
#     parser = argparse.ArgumentParser(description="Create or Update algolias index.")
#     parser.add_argument(
#         "--env",
#         help="Environment",
#         choices=["prod", "stg"],
#         default=None,
#         required=True,
#     )
#     parser.add_argument(
#         "--action",
#         help="Action to perform",
#         choices=["replace_all", "single_update"],
#         default=None,
#         required=True,
#     )
#     return parser.parse_args()


# async def fetch_all_supplier_units(
#     info: InjectedStrawberryInfo,
# ) -> List[Dict[str, Any]]:
#     """Fetch all supplier units."""
#     _db = info.context["db"].sql
#     _query = "SELECT * FROM supplier_unit"
#     res = await _db.fetch_all(_query)  # type: ignore (safe)
#     return [dict(r) for r in res]


# async def fetch_all_supplier_business(
#     info: InjectedStrawberryInfo, unit_ids: List[uuid.UUID]
# ) -> List[Dict[str, Any]]:
#     """Fetch all supplier units."""
#     _db = info.context["db"].sql
#     _query = (
#         f"SELECT * FROM supplier_business WHERE id in {list_into_strtuple(unit_ids)}"
#     )
#     res = await _db.fetch_all(_query)  # type: ignore (safe)
#     return [dict(r) for r in res]


# async def fetch_all_supplier_units_displays_in_marketplace(
#     info: InjectedStrawberryInfo, supplier_units
# ) -> List[Dict[str, Any]]:
#     """Fetch all supplier units."""
#     # Convert string IDs to ObjectId
#     object_ids = []
#     for supp_unit in supplier_units:
#         object_ids.append(Binary.from_uuid(supp_unit["supplier_business_id"]))

#     # Specify the condition for the query
#     query_condition = {
#         "supplier_business_id": {"$in": object_ids},
#         "displays_in_marketplace": True,
#     }
#     mongo = CoreMongoRepository(info)  # type: ignore
#     result = await mongo.fetch_many(
#         core_element_name="Supplier_businessAccount",
#         core_element_collection="supplier_business_account",
#         query=query_condition,
#     )

#     return result


# async def fetch_all_supplier_units_delivery_info(
#     info: InjectedStrawberryInfo, supplier_units
# ) -> List[SupplierUnitDeliveryOptions]:
#     """Fetch all supplier units."""
#     # Convert string IDs to ObjectId
#     object_ids = []
#     for supp_unit in supplier_units:
#         object_ids.append(Binary.from_uuid(supp_unit["id"]))

#     # Specify the condition for the query
#     query_condition = {"supplier_unit_id": {"$in": object_ids}}
#     mongo = CoreMongoRepository(info)  # type: ignore
#     result = await mongo.fetch_many(
#         core_element_name="Supplier_businessAccount",
#         core_element_collection="supplier_unit_delivery_info",
#         query=query_condition,
#     )
#     invoicing_options = []
#     for r in result:
#         invoicing_options.append(
#             SupplierUnitDeliveryOptions(
#                 supplier_unit_id=Binary.as_uuid(r["supplier_unit_id"]),
#                 selling_option=[SellingOption(so) for so in r["selling_option"]],
#                 service_hours=[ServiceDay(**_servd) for _servd in r["service_hours"]],
#                 regions=[str(r).upper() for r in r["regions"]],
#                 delivery_time_window=r["delivery_time_window"],
#                 warning_time=r["warning_time"],
#                 cutoff_time=r["cutoff_time"],
#             )
#         )
#     return invoicing_options


# def find_supplier_business_account_idx(
#     sup_unit: Dict[Any, Any], sup_units_dim: List[Dict[Any, Any]]
# ) -> Dict[Any, Any] | None:
#     for sup_unit_dim in sup_units_dim:
#         if sup_unit_dim["supplier_business_id"] == sup_unit["supplier_business_id"]:
#             return sup_unit_dim
#     return None


# def find_supplier_business_idx(
#     sup_unit: Dict[Any, Any], sup_business: List[Dict[Any, Any]]
# ) -> Dict[Any, Any] | None:
#     for sb in sup_business:
#         if sb["id"] == sup_unit["supplier_business_id"]:
#             return sb
#     return None


# def find_supplier_delivery_info_idx(
#     sup_unit: Dict[Any, Any], sup_units_di: List[SupplierUnitDeliveryOptions]
# ) -> SupplierUnitDeliveryOptions | None:
#     for sup_unit_di in sup_units_di:
#         if sup_unit_di.supplier_unit_id == sup_unit["id"]:
#             return sup_unit_di
#     return None


# async def replace_all_index(info: InjectedStrawberryInfo) -> bool:
#     # fetch all supplier units
#     sup_units = await fetch_all_supplier_units(info)
#     supp_unit_ids = []
#     for sup_unit in sup_units:
#         supp_unit_ids.append(sup_unit["supplier_business_id"])
#     sup_units_dim = await fetch_all_supplier_units_displays_in_marketplace(
#         info, sup_units
#     )
#     sup_units_di = await fetch_all_supplier_units_delivery_info(info, sup_units)
#     sup_units_dim_id_list = []
#     for sup_unit_dim in sup_units_dim:
#         sup_unit_dim["supplier_business_id"] = uuid.UUID(
#             bytes=bytes(sup_unit_dim["supplier_business_id"])
#         )
#         sup_units_dim_id_list.append(sup_unit_dim["supplier_business_id"])
#     _sup_units_dim = []
#     supplier_business_list = await fetch_all_supplier_business(info, supp_unit_ids)
#     for sup_unit in sup_units:
#         if sup_unit["supplier_business_id"] in sup_units_dim_id_list:
#             supplier_business_account = find_supplier_business_account_idx(
#                 sup_unit, sup_units_dim
#             )
#             delivery_info = find_supplier_delivery_info_idx(sup_unit, sup_units_di)
#             supplier_business = find_supplier_business_idx(
#                 sup_unit, supplier_business_list
#             )
#             if supplier_business_account and delivery_info and supplier_business:
#                 _sup_units_dim.append(
#                     {
#                         "supplier_unit": sup_unit,
#                         "supplier_business": supplier_business,
#                         "supplier_business_account": supplier_business_account,
#                         "delivery_info": delivery_info,
#                     }
#                 )
#     # instance handlers
#     sup_biz_handler = SupplierBusinessHandler(
#         supplier_business_repo=SupplierBusinessRepository(info),  # type: ignore
#         supplier_business_account_repo=SupplierBusinessAccountRepository(info),  # type: ignore
#         core_user_repo=CoreUserRepository(info),  # type: ignore
#     )
#     sup_unit_handler = SupplierUnitHandler(
#         supplier_unit_repo=SupplierUnitRepository(info),  # type: ignore
#         unit_category_repo=SupplierUnitCategoryRepository(info),  # type: ignore
#         supplier_unit_delivery_repo=SupplierUnitDeliveryRepository(info),  # type: ignore
#         core_user_repo=CoreUserRepository(info),  # type: ignore
#         tax_info_repo=MxSatCertificateRepository(info),  # type: ignore
#     )
#     sup_res_assign_handler = SupplierRestaurantsHandler(
#         supplier_restaurants_repo=SupplierRestaurantsRepository(info),  # type: ignore
#         supplier_unit_repo=SupplierUnitRepository(info),  # type: ignore
#         supplier_user_repo=SupplierUserRepository(info),  # type: ignore
#         supplier_user_permission_repo=SupplierUserPermissionRepository(info),  # type: ignore
#         restaurant_branch_repo=RestaurantBranchRepository(info),  # type: ignore
#         core_user_repo=CoreUserRepository(info),  # type: ignore
#         restaurant_business_repo=RestaurantBusinessRepository(info),  # type: ignore
#         restaurant_business_account_repo=RestaurantBusinessAccountRepository(
#             info  # type: ignore
#         ),
#         category_repo=CategoryRepository(info),  # type: ignore
#         restaurant_branch_category_repo=RestaurantBranchCategoryRepository(
#             info  # type: ignore
#         ),
#         product_repo=ProductRepository(info),  # type: ignore
#         supplier_product_repo=SupplierProductRepository(info),  # type: ignore
#         supplier_product_price_repo=SupplierProductPriceRepository(info),  # type: ignore
#         supplier_product_stock_repo=SupplierProductStockRepository(info),  # type: ignore
#     )
#     _handler = EcommerceSellerHandler(
#         ecommerce_seller_repo=EcommerceSellerRepository(info),  # type: ignore
#         supplier_business_handler=sup_biz_handler,
#         supplier_unit_handler=sup_unit_handler,
#         supplier_restaurant_assign_handler=sup_res_assign_handler,
#         restaurant_branch_repo=RestaurantBranchRepository(info),  # type: ignore
#         core_user_repo=CoreUserRepository(info),  # type: ignore
#     )

#     # rs_query = RestaurantSuppliersQuery()
#     _sup_units_dim_to_algolia = []
#     for su in tqdm(_sup_units_dim, desc="Prods from SUs"):  # CHECK THIS
#         ecomm_sell_cat = await _handler.fetch_seller_default_catalog_info(
#             supplier_unit_id=su["supplier_unit"]["id"],
#             search="",
#             page=1,
#             page_size=100000,
#         )
#         if len(ecomm_sell_cat.products) == 0:
#             continue
#         # _prods = await rs_query.get_public_marketplace_restaurant_suppliers(
#         #     info, su["id"]
#         # )
#         # all_prods.extend(_prods)

#         su["products"] = ecomm_sell_cat.products
#         _sup_units_dim_to_algolia.append(su)
#     # format data
#     # _df = pd.DataFrame(all_prods)
#     # df = _df[_df.products.apply(lambda x: isinstance(x, list))]
#     # formatted_prods = []
#     # for i, row in df.iterrows():
#     #     if not row.supplier_business_account["displays_in_marketplace"]:
#     #         continue
#     #     _unit = row.unit[0]
#     #     for pr in row.products:
#     #         tmp = {
#     #             # supplier product
#     #             "objectID": str(pr["price"]["supplier_product_id"]),
#     #             "id": str(pr["price"]["supplier_product_id"]),
#     #             "conversionFactor": pr["product"]["conversion_factor"],
#     #             "estimatedWeight": pr["product"]["estimated_weight"],
#     #             "minQuantity": pr["product"]["min_quantity"],
#     #             "price": {
#     #                 "amount": pr["price"]["price"],
#     #                 "id": str(pr["price"]["id"]),
#     #                 "supplierProductId": str(pr["price"]["supplier_product_id"]),
#     #                 "unit": pr["price"]["currency"].value,
#     #                 "validUntil": pr["price"]["valid_upto"].isoformat(),
#     #             },
#     #             "productDescription": pr["product"]["description"],
#     #             "productUuid": str(pr["product"]["product_id"])
#     #             if pr["product"]["product_id"]
#     #             else None,
#     #             "sellUnit": pr["product"]["sell_unit"].name,
#     #             "sku": pr["product"]["sku"],
#     #             "taxAmount": pr["product"]["tax"],
#     #             "unitMultiple": pr["product"]["unit_multiple"],
#     #             "createdAt": pr["price"]["created_at"].isoformat(),
#     #             # # unit
#     #             "cutOffTime": _unit["delivery_info"]["cutoff_time"],
#     #             "deleted": _unit["supplier_unit"]["deleted"],
#     #             "deliverySchedules": _unit["delivery_info"]["service_hours"],
#     #             "deliveryTypes": [
#     #                 so.value if so.value == "pickup" else "delivery"
#     #                 for so in _unit["delivery_info"]["selling_option"]
#     #             ],
#     #             "deliveryWindowSize": _unit["delivery_info"]["delivery_time_window"],
#     #             "deliveryZones": [
#     #                 " ".join(rg.split("_"))
#     #                 for rg in _unit["delivery_info"]["regions"]
#     #             ],
#     #             "fullAddress": _unit["supplier_unit"]["full_address"],
#     #             "unitName": _unit["supplier_unit"]["unit_name"],
#     #             "supplier_unit_id": str(_unit["supplier_unit"]["id"]),
#     #             "warnDays": _unit["delivery_info"]["warning_time"],
#     #             # image
#     #             "images": [_im["route"] for _im in pr["images"]],
#     #             # supplier
#     #             "supplier_business_id": str(row.supplier_business["id"]),
#     #             "supplierName": row.supplier_business["name"],
#     #             "minimumOrderValue": {
#     #                 "amount": row.supplier_business_account[
#     #                     "default_commertial_conditions"
#     #                 ]["minimum_order_value"]["amount"],
#     #                 "measure": "PESOS"
#     #                 if row.supplier_business_account["default_commertial_conditions"][
#     #                     "minimum_order_value"
#     #                 ]["measure"]
#     #                 == "$"
#     #                 else "PRODUCTS",
#     #             },
#     #         }
#     #         formatted_prods.append(tmp)
#     # logger.info(f"Found {len(formatted_prods)} products to upsert")
#     # fmt_prods_df = pd.DataFrame(formatted_prods)
#     # print(fmt_prods_df.groupby("supplierName").agg({"id": "count"}))

#     # FER PRODUCTS
#     _df = pd.DataFrame(_sup_units_dim_to_algolia)
#     # df = _df[_df.products.apply(lambda x: isinstance(x, list))]
#     formatted_prods = []
#     for i, row in _df.iterrows():
#         for pr in row.products:
#             tmp = {
#                 # supplier product
#                 "objectID": str(pr.id),
#                 "id": str(pr.id),
#                 "conversionFactor": pr.conversion_factor,
#                 "estimatedWeight": pr.estimated_weight,
#                 "minQuantity": pr.min_quantity,
#                 "price": {
#                     "amount": pr.last_price.price,
#                     "id": str(pr.last_price.id),
#                     "supplierProductId": str(pr.id),
#                     "unit": pr.last_price.currency.value,
#                     "validUntil": pr.last_price.valid_upto.isoformat(),
#                 },
#                 "productDescription": pr.description,
#                 "productUuid": str(pr.product_id) if pr.product_id else None,
#                 "sellUnit": pr.sell_unit.name,
#                 "sku": pr.sku,
#                 "taxAmount": pr.tax,
#                 "unitMultiple": pr.unit_multiple,
#                 "createdAt": pr.last_price.created_at.isoformat(),
#                 # # unit
#                 "cutOffTime": row["delivery_info"].cutoff_time,
#                 "deleted": row["supplier_unit"]["deleted"],
#                 "deliverySchedules": [
#                     domain_to_dict(so) for so in row["delivery_info"].service_hours
#                 ],
#                 "deliveryTypes": [
#                     so.value if so.value == "pickup" else "delivery"
#                     for so in row["delivery_info"].selling_option
#                 ],
#                 "deliveryWindowSize": row["delivery_info"].delivery_time_window,
#                 # "deliveryZones": [
#                 #     " ".join(rg.split("_")) for rg in row["delivery_info"].regions
#                 # ],
#                 "fullAddress": row["supplier_unit"]["full_address"],
#                 "unitName": row["supplier_unit"]["unit_name"],
#                 "supplier_unit_id": str(row["supplier_unit"]["id"]),
#                 "warnDays": row["delivery_info"].warning_time,
#                 # image
#                 "images": [_im for _im in pr.images],
#                 # supplier
#                 "supplier_business_id": str(
#                     row["supplier_unit"]["supplier_business_id"]
#                 ),
#                 "supplierName": row["supplier_business"]["name"],
#                 "minimumOrderValue": {
#                     "amount": row["supplier_business_account"][
#                         "default_commertial_conditions"
#                     ]["minimum_order"]["amount"],
#                     "measure": "PESOS"
#                     if row["supplier_business_account"][
#                         "default_commertial_conditions"
#                     ]["minimum_order"]["measure"]
#                     == "$"
#                     else "PRODUCTS",
#                 },
#             }
#             formatted_prods.append(tmp)
#     logger.info(f"Found {len(formatted_prods)} products to upsert")
#     fmt_prods_df = pd.DataFrame(formatted_prods)
#     print(fmt_prods_df.groupby("unitName").agg({"id": "count"}))
#     # upsert all products
#     try:
#         AlgoliaIndex.clear_objects()
#         AlgoliaIndex.save_objects(formatted_prods)
#     except Exception as e:
#         logger.error(e)
#         return False
#     return True


# async def single_update_index(info: InjectedStrawberryInfo) -> bool:
#     logger.warning("Not implemented yet")
#     raise NotImplementedError


# async def run_upsert_algolia_index(
#     info: InjectedStrawberryInfo,
#     env: str,
#     action: str,
#     password: str
# ) -> bool:
#     # verify env vars are the same as the env in the args
#     if env.lower() != ENV.lower():
#         logger.error(f"ENV in args ({env}) does not match ENV in env vars ({ENV})")
#         return False
#     if password != RETOOL_SECRET_BYPASS:
#         logging.info("Access Denied")
#         raise Exception("Access Denied")
#     if action == "replace_all":
#         return await replace_all_index(info)
#     elif action == "single_update":
#         # [TODO]
#         return await single_update_index(info)
#     return True


# async def run_upsert_algolia_index_wrapper(
#     env: str,
#     action: str,
#     password: str
# ) -> bool:
#     _info = InjectedStrawberryInfo(SQLDatabase, MongoDatabase)
#     return await run_upsert_algolia_index(_info, env, action, password)


# async def main():
#     args = parse_args()
#     logger.info(f"Started running Algolia ReIndex: {args.env}")
#     try:
#         await db_startup()
#         password = RETOOL_SECRET_BYPASS
#         fl = await run_upsert_algolia_index_wrapper(
#             args.env,
#             args.action,
#             password
#         )
#         if not fl:
#             logger.info(
#                 f"Algolia ReIndex [{args.action}] for ({args.env}) not able to be executed"
#             )
#             return
#         logger.info(
#             f"Finished running Algolia ReIndex [{args.action}] successfully: {args.env}"
#         )
#         await db_shutdown()
#     except Exception as e:
#         logger.error(f"Error running Algolia ReIndex [{args.action}]: {args.env}")
#         logger.error(e)


# if __name__ == "__main__":
#     asyncio.run(main())
