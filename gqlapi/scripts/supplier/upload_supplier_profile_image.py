""" Upload Images
    Usage example:
    poetry run python -m gqlapi.scripts.supplier.upload_supplier_profile_image \
    --supplier_file ../../../_cambios_DB/{file}.xlsx \
    --images_dir ../../../_cambios_DB/{images_dir}
"""

import asyncio
import base64
import argparse
from pathlib import Path
from typing import Any, Dict, List
from uuid import UUID
from gqlapi.lib.clients.clients.cloudinaryapi.cloudinary import CloudinaryApi, Folders
from gqlapi.db import database as SQLDatabase, db_shutdown, db_startup
from gqlapi.repository.supplier.supplier_business import SupplierBusinessRepository
from gqlapi.utils.automation import InjectedStrawberryInfo
import pandas as pd

from gqlapi.config import ENV as DEV_ENV

from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.lib.logger.logger.basic_logger import get_logger

logger = get_logger(get_app())


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--supplier_file", help="Supplier Products file (XLSX)", required=True
    )
    parser.add_argument("--images_dir", help="Images dir", required=True)
    _args = parser.parse_args()
    if _args.supplier_file.split(".")[-1] != "xlsx":
        raise Exception("Products file invalid format: Must be XLSX")
    return _args


async def upload_supplier_images(img_dir, data: List[Dict[Any, Any]]):
    try:
        await db_startup()
        _info = InjectedStrawberryInfo(db=SQLDatabase, mongo=None)
        supplier_business_repo = SupplierBusinessRepository(info=_info)  # type: ignore
        cloudinary_api = CloudinaryApi(env=DEV_ENV)
        feedback_errors = []
        feedback_ok = []
        for row in data:
            logger.info(f"Uploading image for: {row['supplier_product_id']}")
            img_fname = row["supplier_product_id"]
            img_file = img_dir.joinpath(row["image_name"])
            _data = cloudinary_api.upload(
                folder=Folders.MARKETPLACE.value,
                img_file=img_file,
                subfolder=f"{Folders.SUPPLIER.value}/{Folders.PROFILE.value}",
                img_key=img_fname,
            )

            if "status" in _data and _data["status"] == "ok" and "data" in _data:
                logger.info(f"CORRECTLY SAVED IMAGE FOR SUPPLIER IMAGE - {row}")
                try:
                    if not await supplier_business_repo.edit(
                        id=UUID(row["supplier_product_id"]), logo_url=_data["data"]
                    ):
                        logger.error(f"ISSUES SAVING SUPPLIER IMAGE - {row}")
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
                logger.error(f"ISSUES SAVING SUPPLIER IMAGE - {row}")
                feedback_errors.append(
                    {
                        "supplier_product_id": row["supplier_product_id"],
                        "image_name": row["image_name"],
                        "error": "NO encontro la imagen",
                    }
                )
                continue
        df_ok = pd.DataFrame(feedback_ok)
        with pd.ExcelWriter("OK_PROFILE.xlsx", engine="xlsxwriter") as writer:
            df_ok.to_excel(writer, index=False)
        with open("OK_PRODILE.xlsx", "rb") as file:
            base64.b64encode(file.read()).decode()
        df_errors = pd.DataFrame(feedback_errors)
        with pd.ExcelWriter("ERRORS_PROFILE.xlsx", engine="xlsxwriter") as writer:
            df_errors.to_excel(writer, index=False)
        with open("ERRORS_PROFILE.xlsx", "rb") as file:
            base64.b64encode(file.read()).decode()
        await db_shutdown()
    except Exception as e:
        logger.error(e)


def get_supplier_data(supp_prod_file):
    _df = pd.read_excel(supp_prod_file, dtype={"image_name": str})
    if not set(_df.columns).issuperset({"supplier_product_id", "image_name"}):
        raise Exception("Master Data has missing columns!")
    _df = _df.dropna()
    return _df.to_dict(orient="records")


if __name__ == "__main__":
    pargs = parse_args()
    logger.info("Starting to upload profile images")
    data = get_supplier_data(pargs.supplier_file)
    imgs_dir = Path(pargs.images_dir)
    if not imgs_dir.is_dir():
        raise Exception("Images dir is not a valid folder")

    asyncio.run(upload_supplier_images(imgs_dir, data))
    logger.info("Finished uploading images")
