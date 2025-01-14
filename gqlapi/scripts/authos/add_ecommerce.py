""" Script to Create new Ecommerce Seller in the Authos service

    How to run:
    poetry run python -m gqlapi.scripts.authos.add_ecommerce --help
    # poetry run python -m gqlapi.scripts.authos.add_ecommerce --supplier-business-id {id}
"""

import argparse
import asyncio
import json
import logging
import random
import string
from typing import List, Tuple
from uuid import UUID
from gqlapi.lib.clients.clients.godaddyapi.godaddy import GoDaddyClientApi
from gqlapi.lib.clients.clients.vercelapi.vercel import (
    VercelClientApi,
    VercelEnvironmentVariables,
    VercelGitRepository,
    VercelUtils,
)
from gqlapi.domain.interfaces.v2.supplier.supplier_business import SupplierBusinessGQL
from gqlapi.domain.models.v2.b2bcommerce import (
    EcommerceParams,
    EcommerceSeller,
    NewEcommerceEnvVars,
)
from gqlapi.lib.environ.environ.environ import Environment, get_env
from gqlapi.config import (
    GODADDY_DOMAIN,
    GODADDY_API_KEY,
    GODADDY_API_SECRET,
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
    "scripts.add_ecommerce ", logging.INFO, Environment(get_env())
)


def parse_args() -> argparse.Namespace:
    """Parse the command line arguments."""
    parser = argparse.ArgumentParser(
        description="Create new Ecommerce Seller in the Authos service"
    )
    # JSON to ENVARS
    parser.add_argument(
        "--supplier-business-id",
        help="Supplier Business ID",
        type=str,
        default=None,
        required=True,
    )
    parser.add_argument(
        "--env_vars_file",
        type=str,
        help="ENV vars in txt (TXT)",
        required=True,
    )
    parser.add_argument(
        "--params_vars_file",
        type=str,
        help="ENV vars in txt (TXT)",
        required=True,
    )
    _args = parser.parse_args()
    if _args.env_vars_file.split(".")[-1] != "txt":
        raise Exception("Env Vars Template file has invalid format: Must be txt")

    return parser.parse_args()


async def generate_new_business_name(
    supplier_business: SupplierBusinessGQL,
    ecommerce_handler: EcommerceSellerHandler,
    subdomain_alima: str = "compralima.com",
) -> Tuple[str, str] | Tuple[None, None]:
    ecomm_proj = VercelUtils.build_project_name(supplier_business.name.strip())
    ecomm_domain = VercelUtils.build_domain_name(
        supplier_business.name.strip(), subdomain_alima
    )
    supplier_seller_val_url = await ecommerce_handler.fetch_ecommerce_seller(
        "ecommerce_url", ecomm_domain
    )
    supplier_seller_val_project = await ecommerce_handler.fetch_ecommerce_seller(
        "project_name", ecomm_proj
    )
    if not supplier_seller_val_url and not supplier_seller_val_project:
        return ecomm_proj, ecomm_domain
    alphabet = [i for i in string.ascii_lowercase]
    random.shuffle(alphabet)
    # Iterate over the alphabet
    for letter in alphabet:
        ecomm_proj = VercelUtils.build_project_name(
            supplier_business.name.strip() + "-" + letter
        )
        ecomm_domain = VercelUtils.build_domain_name(
            supplier_business.name.strip() + "-" + letter, subdomain_alima
        )
        supplier_seller_val_url = await ecommerce_handler.fetch_ecommerce_seller(
            "ecommerce_url", ecomm_domain
        )
        supplier_seller_val_project = await ecommerce_handler.fetch_ecommerce_seller(
            "project_name", ecomm_proj
        )
        if not supplier_seller_val_url and not supplier_seller_val_project:
            return ecomm_proj, ecomm_domain
    return None, None


async def create_new_ecomm(
    info: InjectedStrawberryInfo,
    supplier_business_id: UUID,
    env_vars: str,
    params_vars: str,
) -> bool:
    # convert env_vars to dict
    try:
        env_vars_dictionary = json.loads(env_vars)
    except Exception as e:
        logger.error(e)
        return False
    try:
        params_vars_dictionary = json.loads(params_vars)
    except Exception as e:
        logger.error(e)
        return False
    if not info.context["db"].authos:
        logger.warning("Authos DB not connected!")
        return False
    supplier_business_handler = SupplierBusinessHandler(
        supplier_business_repo=SupplierBusinessRepository(info),  # type: ignore
        supplier_business_account_repo=SupplierBusinessAccountRepository(info),  # type: ignore
        core_user_repo=CoreUserRepository(info),  # type: ignore
        supplier_user_repo=SupplierUserRepository(info),  # type: ignore
        supplier_user_permission_repo=SupplierUserPermissionRepository(info),  # type: ignore
    )
    supplier_unit_handler = SupplierUnitHandler(
        supplier_unit_repo=SupplierUnitRepository(info),  # type: ignore
        unit_category_repo=SupplierUnitCategoryRepository(info),  # type: ignore
    )
    ecommerce_handler = EcommerceSellerHandler(
        ecommerce_seller_repo=EcommerceSellerRepository(info),  # type: ignore
        supplier_business_handler=supplier_business_handler,
        supplier_unit_handler=supplier_unit_handler,
    )
    # create one if not
    supplier_seller = await ecommerce_handler.fetch_ecommerce_seller(
        "supplier_business_id", supplier_business_id
    )
    if not supplier_seller:
        logger.error("Error to fetch ecommerce seller")
        return False
    supplier_business = await supplier_business_handler.fetch_supplier_business(
        supplier_business_id
    )
    ecomm_project, ecomm_url = await generate_new_business_name(
        supplier_business, ecommerce_handler, GODADDY_DOMAIN
    )
    if not ecomm_project or not ecomm_url:
        logger.error("Error to generate new business name")
        return False
    vercel_api = VercelClientApi(ENV, VERCEL_TOKEN, VERCEL_TEAM)
    go_daddy_api = GoDaddyClientApi(
        ENV, GODADDY_API_KEY, GODADDY_API_SECRET, GODADDY_DOMAIN
    )
    ecommerce_env_vars = NewEcommerceEnvVars(**env_vars_dictionary)
    ecommerce_params = EcommerceParams(**params_vars_dictionary)
    vercel_environment_variables: List[VercelEnvironmentVariables] = []
    # auto generated vars
    ecommerce_params.project_name = ecomm_project
    ecommerce_params.ecommerce_url = ecomm_url
    ecommerce_params.account_active = True
    ecommerce_params.banner_img = (
        f"alima-marketplace-PROD/supplier/profile/{supplier_business_id}_banner.png"
    )
    ecommerce_params.currency = "MXN"
    if not ecommerce_params.banner_img_href:
        ecommerce_params.banner_img_href = "/catalog/list"
    if supplier_business.account:
        ecommerce_params.footer_phone = supplier_business.account.phone_number
        ecommerce_params.footer_is_wa = True
        ecommerce_params.footer_email = supplier_business.account.email

    for key, value in ecommerce_env_vars.__dict__.items():
        if key in [
            "NEXT_PUBLIC_SELLER_NAME",
            "NEXT_PUBLIC_SELLER_ID",
            "NEXT_PUBLIC_SUNIT_ID",
            "NEXT_PUBLIC_GQLAPI_ENV",
        ]:
            vercel_environment_variables.append(
                VercelEnvironmentVariables(
                    key=key,
                    target=["production", "preview", "development"],
                    type="encrypted",
                    value=str(value),
                    # gitBranch="main",
                )
            )
    # create new project in vercel
    find_record = vercel_api.find_project(ecomm_project)
    if find_record.status == "error" and find_record.status_code == 404:
        logger.info("Project not found, creating new project")
    if find_record.status == "ok":
        logger.error("Project already exists")
        return False

    find_gd_record = go_daddy_api.find_record(ecomm_url.split(".")[0], "CNAME")
    if find_gd_record.status == "error" and find_gd_record.status_code == 404:
        logger.info("CNAME record not found, creating new record")
    if find_gd_record.status == "ok" and find_gd_record.result:
        logger.error("CNAME record already exists")
        return False

    # create new domain in godaddy
    domain_resp_gd = go_daddy_api.new_cname_record(
        ecomm_url.split(".")[0], "cname.vercel-dns.com."
    )
    if domain_resp_gd.status == "error":
        logger.warning("ISSUES CREATING GODADDY DOMAIN!!")
        logger.error(domain_resp_gd.msg)

    project_resp = vercel_api.new_project(
        project_name=ecomm_project,
        root_directory="apps/commerce-template",
        framework="nextjs",
        git_repository=VercelGitRepository(
            repo="Alima-Latam/alima-nextjs-monorepo",
            type="github",
        ),
        environment_variables=vercel_environment_variables,
    )
    if project_resp.status == "error":
        logger.error(project_resp.msg)
        return False
    # create new domain in vercel
    domain_resp = vercel_api.new_domain(ecomm_project, ecomm_url)
    if domain_resp.status == "error":
        logger.error(domain_resp.msg)
        return False
    project_created = vercel_api.find_project(ecomm_project)
    if project_created.status == "error":
        logger.error(project_created.msg)
        return False
    if not project_created.result:
        logger.error("Error to create project")
        return False
    project_created_json = json.loads(project_created.result)

    if not project_created_json["link"] or not project_created_json["link"]["repoId"]:
        logger.error("Error to create project")
        return False
    deployment = vercel_api.new_deployment(
        project_name=ecomm_project,
        repo_id=project_created_json["link"]["repoId"],
        github_branch="main",
        framework="nextjs",
    )
    if deployment.status == "error":
        logger.error(deployment.msg)
        return False

    supplier_seller.ecommerce_url = ecomm_url
    supplier_seller.project_name = ecomm_project
    if await ecommerce_handler.edit_ecommerce_seller(
        ecommerce_seller=EcommerceSeller(
            id=supplier_seller.id,
            supplier_business_id=supplier_seller.supplier_business_id,
            seller_name=supplier_seller.seller_name,
            secret_key=supplier_seller.secret_key,
            ecommerce_url="https://" + supplier_seller.ecommerce_url,
            project_name=supplier_seller.project_name,
            banner_img=ecommerce_params.banner_img,
            banner_img_href=ecommerce_params.banner_img_href,
            categories=ecommerce_params.categories,
            rec_prods=ecommerce_params.rec_prods,
            styles_json=ecommerce_params.styles_json,
            shipping_enabled=bool(ecommerce_params.shipping_enabled),
            shipping_rule_verified_by=ecommerce_params.shipping_rule_verified_by,
            shipping_threshold=(
                int(ecommerce_params.shipping_threshold)
                if ecommerce_params.shipping_threshold
                else None
            ),
            shipping_cost=(
                int(ecommerce_params.shipping_cost)
                if ecommerce_params.shipping_cost
                else None
            ),
            search_placeholder=ecommerce_params.search_placeholder,
            footer_msg=ecommerce_params.footer_msg,
            footer_cta=ecommerce_params.footer_cta,
            footer_phone=ecommerce_params.footer_phone,
            footer_is_wa=bool(ecommerce_params.footer_is_wa),
            footer_email=ecommerce_params.footer_email,
            seo_description=ecommerce_params.seo_description,
            seo_keywords=ecommerce_params.seo_keywords,
            default_supplier_unit_id=UUID(ecommerce_env_vars.NEXT_PUBLIC_SUNIT_ID),
            commerce_display=ecommerce_params.commerce_display,
            account_active=bool(ecommerce_params.account_active),
            currency=ecommerce_params.currency,
        ),
    ):
        logger.info("Ecommerce Seller created successfully!")

    return True


async def add_ecomm_wrapper(
    supplier_business_id: UUID, env_vars: str, params_vars: str
) -> bool:
    info = InjectedStrawberryInfo(
        db=SQLDatabase,
        mongo=MongoDatabase,
        authos=AuthosSQLDatabase,
    )
    return await create_new_ecomm(info, supplier_business_id, env_vars, params_vars)


async def main():
    try:

        pargs = parse_args()
        # connect to DB
        await db_startup()
        logger.info("Starting script to insert Ecommerce vercel and godaddy service")
        if pargs.env_vars_file:
            with open(pargs.env_vars_file, "r") as file:
                env_file_content = file.read()
        if pargs.params_vars_file:
            with open(pargs.params_vars_file, "r") as file:
                params_file_content = file.read()
        if not params_file_content:
            logger.error("Error to read env vars file")
            return
        resp = await add_ecomm_wrapper(
            UUID(pargs.supplier_business_id), env_file_content, params_file_content
        )
        if resp:
            logger.info(
                "Finished script to insert Ecommerce vercel and godaddy service"
            )
        else:
            logger.info("Error to new Ecommerce in vercel and godaddy service")
        await db_shutdown()
    except Exception as e:
        logger.error(e)
        logger.info("Error to new Ecommerce in vercel and godaddy service")


if __name__ == "__main__":
    logger.info("Create new Ecommerce Seller in the Authos service")
    asyncio.run(main())
