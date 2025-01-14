""" GET Images template
    Usage example:
    poetry run python -m gqlapi.scripts.product.get_image_name_template \
    --images_dir ../../../_cambios_DB/{images_dir}
"""

import asyncio
from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.lib.logger.logger.basic_logger import get_logger
import argparse
import os
from pathlib import Path
import pandas as pd

logger = get_logger(get_app())


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--images_dir", help="Images dir", required=True)
    _args = parser.parse_args()
    return _args


async def get_supplier_product_images_template(images_dir_str: str, img_dir):
    try:
        # List all files in the directory
        file_names = [
            f for f in os.listdir(img_dir) if os.path.isfile(os.path.join(img_dir, f))
        ]
        # Extract filenames and extensions
        file_info = [(os.path.splitext(file)[0], file) for file in file_names]
        if len(file_info) > 1:
            df_ok = pd.DataFrame(
                file_info, columns=["supplier_product_id", "image_name"]
            )
            output_found_excel_path = os.path.join(
                f"{images_dir_str}", "found_images_template.xlsx"
            )  # Update this with your desired output path
            df_ok.to_excel(output_found_excel_path, index=False)
    except Exception as e:
        logger.error(e)


if __name__ == "__main__":
    pargs = parse_args()
    logger.info("Starting to get images template")
    imgs_dir = Path(pargs.images_dir)
    if not imgs_dir.is_dir():
        raise Exception("Images dir is not a valid folder")

    asyncio.run(get_supplier_product_images_template(pargs.images_dir, imgs_dir))
    logger.info("Finished get images template")
