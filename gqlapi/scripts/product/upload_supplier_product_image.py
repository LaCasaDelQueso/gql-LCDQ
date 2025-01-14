""" Upload Images
    Usage example:
    poetry run python -m gqlapi.scripts.product.upload_supplier_product_image \
    --supplier_products_file ../../../_cambios_DB/{file}.xlsx \
    --images_dir ../../../_cambios_DB/{images_dir}
"""

import asyncio
import base64
import argparse
from pathlib import Path
from typing import Any, Dict, List
from uuid import UUID
import uuid
from gqlapi.lib.clients.clients.cloudinaryapi.cloudinary import CloudinaryApi, Folders
from gqlapi.domain.models.v2.supplier import SupplierProductImage
from gqlapi.db import database as SQLDatabase, db_shutdown, db_startup
from gqlapi.repository.services.image import ImageRepository
from gqlapi.utils.automation import InjectedStrawberryInfo
import pandas as pd

from gqlapi.config import ENV as DEV_ENV

from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.lib.logger.logger.basic_logger import get_logger

logger = get_logger(get_app())


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--supplier_products_file", help="Supplier Products file (XLSX)", required=True
    )
    parser.add_argument("--images_dir", help="Images dir", required=True)
    _args = parser.parse_args()
    if _args.supplier_products_file.split(".")[-1] != "xlsx":
        raise Exception("Products file invalid format: Must be XLSX")
    return _args


async def upload_supplier_product_images(img_dir, prods: List[Dict[Any, Any]]):
    try:
        await db_startup()
        _info = InjectedStrawberryInfo(db=SQLDatabase, mongo=None)
        repository = ImageRepository(info=_info)  # type: ignore
        cloudinary_api = CloudinaryApi(env=DEV_ENV)
        feedback_errors = []
        feedback_ok = []
        for row in prods:
            logger.info(f"Uploading image for: {row['supplier_product_id']}")
            try:
                _supp_image_count = await repository.count(
                    supplier_product_id=UUID(row["supplier_product_id"])
                )
                priority = (
                    await repository.get_last_priority(row["supplier_product_id"]) + 1
                )
            except Exception:
                feedback_errors.append(
                    {
                        "supplier_product_id": row["supplier_product_id"],
                        "image_name": row["image_name"],
                        "error": "NO es UUID",
                    }
                )
                continue

            img_fname = row["supplier_product_id"]
            img_file = img_dir.joinpath(row["image_name"])
            _data = cloudinary_api.upload(
                folder=Folders.MARKETPLACE.value,
                img_file=img_file,
                subfolder=f"{Folders.SUPPLIER.value}/{Folders.SUPPLIER_PRODUCTS.value}",
                img_key=img_fname + "_" + str(_supp_image_count),
            )

            if "status" in _data and _data["status"] == "ok" and "data" in _data:
                logger.info(f"CORRECTLY SAVED IMAGE FOR SUPPLIER PRODUCT - {row}")
                try:
                    if not await repository.add(
                        SupplierProductImage(
                            id=uuid.uuid4(),
                            supplier_product_id=UUID(row["supplier_product_id"]),
                            deleted=False,
                            image_url=_data["data"],
                            priority=priority,
                        )
                    ):
                        logger.error(f"ISSUES SAVING SUPPLIER PRODUCT IMAGE - {row}")
                        feedback_errors.append(
                            {
                                "supplier_product_id": row["supplier_product_id"],
                                "image_name": row["image_name"],
                                "error": "Se subio la imagen pero no se guardo",
                            }
                        )
                        continue
                except Exception:
                    feedback_errors.append(
                        {
                            "supplier_product_id": row["supplier_product_id"],
                            "image_name": row["image_name"],
                            "error": "Se subio la imagen pero no se guardo",
                        }
                    )
                    continue
                feedback_ok.append(row)
            else:
                logger.error(f"ISSUES SAVING SUPPLIER PRODUCT IMAGE - {row}")
                feedback_errors.append(
                    {
                        "supplier_product_id": row["supplier_product_id"],
                        "image_name": row["image_name"],
                        "error": "NO encontro la imagen",
                    }
                )
                continue
        df_ok = pd.DataFrame(feedback_ok)
        with pd.ExcelWriter("OK.xlsx", engine="xlsxwriter") as writer:
            df_ok.to_excel(writer, index=False)
        with open("OK.xlsx", "rb") as file:
            base64.b64encode(file.read()).decode()
        df_errors = pd.DataFrame(feedback_errors)
        with pd.ExcelWriter("ERRORS.xlsx", engine="xlsxwriter") as writer:
            df_errors.to_excel(writer, index=False)
        with open("ERRORS.xlsx", "rb") as file:
            base64.b64encode(file.read()).decode()
        await db_shutdown()
    except Exception as e:
        logger.error(e)


def get_supplier_product_data(supp_prod_file):
    _df = pd.read_excel(supp_prod_file, dtype={"image_name": str})
    if not set(_df.columns).issuperset({"supplier_product_id", "image_name"}):
        raise Exception("Master Data has missing columns!")
    _df = _df.dropna()
    return _df.to_dict(orient="records")


if __name__ == "__main__":
    pargs = parse_args()
    logger.info("Starting to upload images")
    data = get_supplier_product_data(pargs.supplier_products_file)
    imgs_dir = Path(pargs.images_dir)
    if not imgs_dir.is_dir():
        raise Exception("Images dir is not a valid folder")

    asyncio.run(upload_supplier_product_images(imgs_dir, data))
    logger.info("Finished uploading images")
