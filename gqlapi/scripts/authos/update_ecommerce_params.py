""" Script to Create new Ecommerce Seller in the Authos service

    How to run:
    poetry run python -m gqlapi.scripts.authos.add_ecommerce --help
    # poetry run python -m gqlapi.scripts.authos.update_ecommerce_params --supplier-business-id {id}
"""

import argparse
import asyncio
import json
import logging
import random
import string
from typing import Optional, Tuple
from uuid import UUID
from gqlapi.lib.clients.clients.cloudinaryapi.cloudinary import CloudinaryApi, Folders
from gqlapi.lib.clients.clients.vercelapi.vercel import (
    VercelUtils,
)
from gqlapi.domain.interfaces.v2.supplier.supplier_business import SupplierBusinessGQL
from gqlapi.domain.models.v2.b2bcommerce import EcommerceParams, EcommerceSeller
from gqlapi.lib.environ.environ.environ import Environment, get_env
from gqlapi.config import (
    ENV as DEV_ENV,
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
    "scripts.create_new_ecommerce_seller ", logging.INFO, Environment(get_env())
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
        "--params_vars_file",
        type=str,
        help="ENV vars in txt (TXT)",
        required=False,
    )
    parser.add_argument(
        "--logo",
        type=str,
        help="logo path",
        required=False,
    )
    parser.add_argument(
        "--banner",
        type=str,
        help="banner path",
        required=False,
    )
    parser.add_argument(
        "--icon",
        type=str,
        help="icon_path",
        required=False,
    )
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


def create_image_in_cloudinary(
    path: str,
    image_type: str,
    supplier_business_id: str,
    cloudinary_api: CloudinaryApi,
) -> bool:
    img_file = path
    img_key = supplier_business_id + "_" + image_type
    cloudinary_api.delete(
        folder=Folders.MARKETPLACE.value,
        subfolder=f"{Folders.SUPPLIER.value}/{Folders.PROFILE.value}",
        img_key=img_key,
    )
    _data = cloudinary_api.upload(
        folder=Folders.MARKETPLACE.value,
        img_file=img_file,
        subfolder=f"{Folders.SUPPLIER.value}/{Folders.PROFILE.value}",
        img_key=img_key,
    )

    if "status" in _data and _data["status"] == "ok" and "data" in _data:
        return True
    return False


async def edit_ecomm_seller_params(
    info: InjectedStrawberryInfo,
    supplier_business_id: UUID,
    params_vars: Optional[str] = None,
    logo: Optional[str] = None,
    banner: Optional[str] = None,
    icon: Optional[str] = None,
) -> bool:
    # convert env_vars to dict
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
    if params_vars:
        try:
            params_vars_dictionary = json.loads(params_vars)
        except Exception as e:
            logger.error(e)
            return False

        if not info.context["db"].authos:
            logger.warning("Authos DB not connected!")
            return False

        ecommerce_params = EcommerceParams(**params_vars_dictionary)
        if await ecommerce_handler.edit_ecommerce_seller(
            ecommerce_seller=EcommerceSeller(
                id=supplier_seller.id,
                supplier_business_id=supplier_seller.supplier_business_id,
                seller_name=supplier_seller.seller_name,
                secret_key=supplier_seller.secret_key,
                ecommerce_url=supplier_seller.ecommerce_url,
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
                default_supplier_unit_id=supplier_seller.default_supplier_unit_id,
                commerce_display=ecommerce_params.commerce_display,
                account_active=bool(ecommerce_params.account_active),
                currency=ecommerce_params.currency,
            ),
        ):
            logger.info("Ecommerce Seller created successfully!")
    if logo or banner or icon:
        cloudinary_api = CloudinaryApi(env=DEV_ENV)
        if logo:
            if not create_image_in_cloudinary(
                logo, "logo", str(supplier_seller.supplier_business_id), cloudinary_api
            ):
                logger.error(
                    f"Error to upload logo image for supplier {supplier_seller.supplier_business_id}"
                )
                return False
        if banner:
            if not create_image_in_cloudinary(
                banner,
                "banner",
                str(supplier_seller.supplier_business_id),
                cloudinary_api,
            ):
                logger.error(
                    f"Error to upload banner image for supplier {supplier_seller.supplier_business_id}"
                )
                return False
        if icon:
            if not create_image_in_cloudinary(
                icon, "icon", str(supplier_seller.supplier_business_id), cloudinary_api
            ):
                logger.error(
                    f"Error to upload icon image for supplier {supplier_seller.supplier_business_id}"
                )
                return False
    return True


async def edit_ecomm_wrapper(
    supplier_business_id: UUID,
    params_vars: Optional[str] = None,
    logo: Optional[str] = None,
    banner: Optional[str] = None,
    icon: Optional[str] = None,
) -> bool:
    info = InjectedStrawberryInfo(
        db=SQLDatabase,
        mongo=MongoDatabase,
        authos=AuthosSQLDatabase,
    )
    return await edit_ecomm_seller_params(
        info, supplier_business_id, params_vars, logo, banner, icon
    )


async def main():
    try:

        pargs = parse_args()
        # connect to DB
        await db_startup()
        logger.info("Starting script to update Ecommerce seller params")
        params_file_content = None
        logo = None
        banner = None
        icon = None
        if pargs.params_vars_file:
            with open(pargs.params_vars_file, "r") as file:
                params_file_content = file.read()
        if pargs.logo:
            logo = pargs.logo
        if pargs.banner:
            banner = pargs.banner
        if pargs.icon:
            icon = pargs.icon
        resp = await edit_ecomm_wrapper(
            UUID(pargs.supplier_business_id),
            params_file_content,
            logo,
            banner,
            icon,
        )
        if resp:
            logger.info("Finished script to to update Ecommerce seller params")
        else:
            logger.info("Error to to update Ecommerce seller params")
        await db_shutdown()
    except Exception as e:
        logger.error(e)
        logger.info("Error to to update Ecommerce seller params")


if __name__ == "__main__":
    logger.info("Edit Ecommerce Seller in the Authos service")
    asyncio.run(main())
