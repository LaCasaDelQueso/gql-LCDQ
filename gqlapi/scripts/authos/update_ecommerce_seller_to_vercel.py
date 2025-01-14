""" Script to Create new Ecommerce Seller in the Authos service

    How to run:
    poetry run python -m gqlapi.scripts.authos.create_new_ecommerce_seller --help
    # poetry run python -m gqlapi.scripts.authos.update_ecommerce_seller_to_vercel
"""

import asyncio
import json
import logging
from typing import List
import unicodedata
from gqlapi.lib.clients.clients.vercelapi.vercel import (
    VercelClientApi,
)
from databases import Database
from gqlapi.domain.models.v2.b2bcommerce import EcommerceEnvVars, EcommerceSeller
from gqlapi.lib.environ.environ.environ import Environment, get_env
from gqlapi.config import (
    VERCEL_TEAM,
    VERCEL_TOKEN,
    ENV,
)
from gqlapi.db import (
    db_shutdown,
    db_startup,
    authos_database as AuthosSQLDatabase,
    database as SQLDatabase,
)
from gqlapi.handlers.b2bcommerce.ecommerce_seller import EcommerceSellerHandler
from gqlapi.handlers.supplier.supplier_business import SupplierBusinessHandler
from gqlapi.handlers.supplier.supplier_unit import SupplierUnitHandler
from gqlapi.mongo import mongo_db as MongoDatabase
from gqlapi.repository.b2bcommerce.ecommerce_seller import EcommerceSellerRepository
from gqlapi.repository.core.category import SupplierUnitCategoryRepository
from gqlapi.repository.supplier.supplier_business import (
    SupplierBusinessAccountRepository,
    SupplierBusinessRepository,
)
from gqlapi.repository.supplier.supplier_unit import SupplierUnitRepository
from gqlapi.repository.supplier.supplier_user import (
    SupplierUserPermissionRepository,
    SupplierUserRepository,
)
from gqlapi.repository.user.core_user import CoreUserRepository
from gqlapi.utils.automation import InjectedStrawberryInfo
from gqlapi.lib.logger.logger.basic_logger import get_logger

logger = get_logger(
    "scripts.update_ecommerce_seller_to_vercel ", logging.INFO, Environment(get_env())
)


async def fetch_all_ecommerce_seller(db: Database) -> List[EcommerceSeller]:
    query = "SELECT * FROM ecommerce_seller"
    ecomm_seller_rec = await db.fetch_all(query)
    ecomm_seller_list = []
    for ecomm_seller in ecomm_seller_rec:
        ecomm_seller_list.append(EcommerceSeller(**dict(ecomm_seller)))
    return ecomm_seller_list


def build_project_name(name: str) -> str:
    normalized_string = unicodedata.normalize("NFKD", name)
    result_string = "".join(
        [char for char in normalized_string if not unicodedata.combining(char)]
    )
    return (
        (result_string.replace(" ", "-").lower() + "-commerce")
        .replace("_", "-")
        .replace(".", "")
        .replace(",", "")
    )


async def fill_ecomm_seller(
    _info: InjectedStrawberryInfo,
) -> bool:
    # convert env_vars to dict
    if not _info.context["db"].authos:
        logger.warning("Authos DB not connected!")
        return False
    supplier_business_handler = SupplierBusinessHandler(
        supplier_business_repo=SupplierBusinessRepository(_info),  # type: ignore
        supplier_business_account_repo=SupplierBusinessAccountRepository(_info),  # type: ignore
        core_user_repo=CoreUserRepository(_info),  # type: ignore
        supplier_user_repo=SupplierUserRepository(_info),  # type: ignore
        supplier_user_permission_repo=SupplierUserPermissionRepository(_info),  # type: ignore
    )
    supplier_unit_handler = SupplierUnitHandler(
        supplier_unit_repo=SupplierUnitRepository(_info),  # type: ignore
        unit_category_repo=SupplierUnitCategoryRepository(_info),  # type: ignore
    )
    ecommerce_handler = EcommerceSellerHandler(
        ecommerce_seller_repo=EcommerceSellerRepository(_info),  # type: ignore
        supplier_business_handler=supplier_business_handler,
        supplier_unit_handler=supplier_unit_handler,
    )
    _db = _info.context["db"].authos
    # create one if not
    supplier_seller_list = await fetch_all_ecommerce_seller(_db)
    if not supplier_seller_list:
        logger.error("Error to fetch ecommerce seller")
        return False
    supplier_business_idx = {}
    for supplier_seller in supplier_seller_list:
        supplier_business = await supplier_business_handler.fetch_supplier_business(
            supplier_seller.supplier_business_id
        )
        if not supplier_business:
            logger.error("Error to fetch supplier business")
            return False
        supplier_business_idx[supplier_business.id] = supplier_business

    vercel_api = VercelClientApi(ENV, VERCEL_TOKEN, VERCEL_TEAM)

    for supplier_seller in supplier_seller_list:
        # project_name = build_project_name(supplier_business_idx[supplier_seller.supplier_business_id].name)
        project_name = build_project_name(supplier_seller.seller_name)
        if supplier_seller.project_name:
            continue
        if not project_name:
            logger.error(
                f"Error to fetch project name for project {supplier_seller.project_name}"
            )
            continue
        print(project_name)
        env_vars = (
            vercel_api.retrieve_the_environment_variables_of_a_project_by_id_or_name(
                project_name
            )
        )
        if not env_vars:
            logger.error(
                f"Error to fetch env vars for project {supplier_seller.project_name}"
            )
            continue
        env_decriped = {}
        # convert string in dict
        if not env_vars.result:
            logger.error(
                f"Error to fetch env vars for project {supplier_seller.project_name}"
            )
            continue
        env_vars_json = json.loads(env_vars.result)
        for env_var in env_vars_json["envs"]:
            if env_var["key"] in EcommerceEnvVars.__annotations__.keys():
                decryped_value = vercel_api.retrieve_decrypted_the_environment_variables_of_a_project_by_id_or_name(
                    project_name=project_name, env_id=env_var["id"]
                )
                if not decryped_value:
                    logger.error(
                        f"Error to fetch env vars for project {supplier_seller.project_name}"
                    )
                    raise Exception(
                        f"Error to fetch env vars for project {supplier_seller.project_name}"
                    )
                if not decryped_value.result:
                    logger.error(
                        f"Error to fetch env vars for project {supplier_seller.project_name}"
                    )
                    raise Exception(
                        f"Error to fetch env vars for project {supplier_seller.project_name}"
                    )
                decryped_value_json = json.loads(decryped_value.result)
                env_decriped[env_var["key"]] = decryped_value_json["value"]
        if await ecommerce_handler.edit_ecommerce_seller(
            ecommerce_seller=EcommerceSeller(
                id=supplier_seller.id,
                supplier_business_id=supplier_seller.supplier_business_id,
                seller_name=supplier_seller.seller_name,
                secret_key=supplier_seller.secret_key,
                project_name=project_name,
                ecommerce_url=env_decriped.get("NEXT_PUBLIC_PROJECT_URL", None),
                banner_img=env_decriped.get("NEXT_PUBLIC_BANNER_IMG", None),
                banner_img_href=env_decriped.get("NEXT_PUBLIC_BANNER_IMG_HREF", None),
                categories=env_decriped.get("NEXT_PUBLIC_CATEGORIES", None),
                rec_prods=env_decriped.get("NEXT_PUBLIC_REC_PRODS", None),
                styles_json=env_decriped.get("NEXT_PUBLIC_STYLES_JSON", None),
                shipping_enabled=bool(
                    env_decriped.get("NEXT_PUBLIC_SHIPPING_ENABLED", None)
                ),
                shipping_rule_verified_by=env_decriped.get(
                    "NEXT_PUBLIC_SHIPPING_RULE_VERIFIED_BY", None
                ),
                shipping_threshold=int(
                    env_decriped.get("NEXT_PUBLIC_SHIPPING_THRESHOLD", None)
                ),
                shipping_cost=int(env_decriped.get("NEXT_PUBLIC_SHIPPING_COST", None)),
                search_placeholder=env_decriped.get(
                    "NEXT_PUBLIC_SEARCH_PLACEHOLDER", None
                ),
                footer_msg=env_decriped.get("NEXT_PUBLIC_FOOTER_MSG", None),
                footer_cta=env_decriped.get("NEXT_PUBLIC_FOOTER_CTA", None),
                footer_phone=env_decriped.get("NEXT_PUBLIC_FOOTER_PHONE", None),
                footer_is_wa=bool(env_decriped.get("NEXT_PUBLIC_FOOTER_IS_WA", None)),
                footer_email=env_decriped.get("NEXT_PUBLIC_FOOTER_EMAIL", None),
                seo_description=env_decriped.get("NEXT_PUBLIC_SEO_DESCRIPTION", None),
                seo_keywords=env_decriped.get("NEXT_PUBLIC_SEO_KEYWORDS", None),
                default_supplier_unit_id=env_decriped.get("NEXT_PUBLIC_SUNIT_ID", None),
                commerce_display=env_decriped.get("NEXT_PUBLIC_COMMERCE_DISPLAY", None),
                account_active=bool(
                    env_decriped.get("NEXT_PUBLIC_ACCOUNT_ACTIVE", None)
                ),
                currency=env_decriped.get("NEXT_PUBLIC_CURRENCY", None),
            ),
        ):
            logger.info("Ecommerce Seller updated successfully!")

    return True


async def fill_ecomm_seller_wrapper() -> bool:
    info = InjectedStrawberryInfo(
        db=SQLDatabase,
        mongo=MongoDatabase,
        authos=AuthosSQLDatabase,
    )
    return await fill_ecomm_seller(info)


async def main():
    try:
        # connect to DB
        await db_startup()
        logger.info("Starting script to insert Ecommerce Seller info from vercel")
        resp = await fill_ecomm_seller_wrapper()
        if resp:
            logger.info("Finished script to insert Ecommerce Seller info from vercel")
        else:
            logger.info("Error to insert Ecommerce Seller info from vercel")
        await db_shutdown()
    except Exception as e:
        logger.error(e)
        logger.info("Error to new Ecommerce in vercel and godaddy service")


if __name__ == "__main__":
    logger.info("Create new Ecommerce Seller in the Authos service")
    asyncio.run(main())
