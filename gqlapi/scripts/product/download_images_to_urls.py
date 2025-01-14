""" Upload Images
    Usage example:
    poetry run python -m gqlapi.scripts.product.download_images_to_urls \
    --url_products_file ../../../_cambios_DB/{file}.xlsx \
    --images_dir ../../../_cambios_DB/{images_dir}
"""

import asyncio
import argparse
import os
from pathlib import Path
import pandas as pd

from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.lib.logger.logger.basic_logger import get_logger
import requests

logger = get_logger(get_app())


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--url_products_file", help="URL Supplier Products file (XLSX)", required=True
    )
    parser.add_argument("--images_dir", help="Images dir", required=True)
    _args = parser.parse_args()
    if _args.url_products_file.split(".")[-1] != "xlsx":
        raise Exception("Products file invalid format: Must be XLSX")
    return _args


def download_and_save_image(save_path: str, url: str, filename: str):
    response = requests.get(url)
    if response.status_code == 200:
        full_path = os.path.join(save_path, filename)
        with open(full_path, "wb") as f:
            f.write(response.content)
        print(f"Image downloaded and saved: {filename}")
    else:
        print(f"Failed to download image from {url}")


async def download_supplier_product_images(img_dir: str, prods: pd.DataFrame):
    try:
        imgs_dir_path = Path(img_dir)
        if not imgs_dir_path.is_dir():
            raise Exception("Images dir is not a valid folder")
        # Iterate through each row and download images
        for index, row in prods.iterrows():
            image_url = row["image_url"]
            image_name = f"image_{index}"  # You can customize the naming convention
            row["image_name"] = image_name
            download_and_save_image(img_dir, image_url, image_name)
        prods["image_name"] = [f"image_{i}" for i in range(len(prods))]
        output_url_excel_path = os.path.join(
            f"{img_dir}", "not_found_images.xlsx"
        )  # Update this with your desired output path
        url_images_df = pd.DataFrame(prods)
        url_images_df.to_excel(output_url_excel_path, index=False)
    except Exception as e:
        logger.error(e)


def get_supplier_product_data(supp_prod_file):
    _df = pd.read_excel(supp_prod_file, dtype={"image_url": str})
    if not set(_df.columns).issuperset({"supplier_product_id", "image_url"}):
        raise Exception("Master Data has missing columns!")
    _df = _df.dropna()
    return _df


if __name__ == "__main__":
    pargs = parse_args()
    logger.info("Starting to download images")
    data = get_supplier_product_data(pargs.url_products_file)

    asyncio.run(download_supplier_product_images(pargs.images_dir, data))
    logger.info("Finished download images")
