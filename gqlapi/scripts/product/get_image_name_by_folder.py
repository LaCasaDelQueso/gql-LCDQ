""" GET Images template
    Usage example:
    poetry run python -m gqlapi.scripts.product.get_image_name_by_folder \
    --supplier_products_file ../../../_cambios_DB/{file}.xlsx \
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
    parser.add_argument(
        "--supplier_products_file", help="Supplier Products file (XLSX)", required=True
    )
    parser.add_argument("--images_dir", help="Images dir", required=True)
    _args = parser.parse_args()
    if _args.supplier_products_file.split(".")[-1] != "xlsx":
        raise Exception("Products file invalid format: Must be XLSX")
    return _args


def get_files_in_folder(folder_path):
    return [
        f
        for f in os.listdir(folder_path)
        if os.path.isfile(os.path.join(folder_path, f))
    ]


async def get_supplier_product_images_template(
    images_dir_str: str, img_dir, data: pd.DataFrame
):
    try:

        # Iterate through each row in the input DataFrame
        folder_not_found = []
        folder_found = []
        count = 1
        for index, row in data.iterrows():
            count = count + 1
            folder_path = os.path.join(img_dir, str(row["folder"]))
            # Check if the folder exists
            if os.path.exists(folder_path):
                file_names = get_files_in_folder(folder_path)
                # Add a row for each file in the output DataFrame
                for file_name in file_names:
                    folder_found.append(
                        {
                            "supplier_product_id": row["supplier_product_id"],
                            "image_name": row["folder"] + "/" + file_name,
                        }
                    )
            else:
                folder_not_found.append(
                    {
                        "supplier_product_id": row["supplier_product_id"],
                        "folder": row["folder"],
                    }
                )
                print(f"Folder not found for ID {row['supplier_product_id']}")

        if len(folder_found) > 1:
            output_found_excel_path = os.path.join(
                f"{images_dir_str}", "found_images.xlsx"
            )  # Update this with your desired output path
            found_images_df = pd.DataFrame(folder_found)
            found_images_df.to_excel(output_found_excel_path, index=False)
            print(count)
        if len(folder_not_found) > 1:
            output_not_found_excel_path = os.path.join(
                f"{images_dir_str}", "not_found_images.xlsx"
            )  # Update this with your desired output path
            not_found_images_df = pd.DataFrame(folder_not_found)
            not_found_images_df.to_excel(output_not_found_excel_path, index=False)
    except Exception as e:
        logger.error(e)


def get_supplier_product_folder_data(supp_prod_file) -> pd.DataFrame:
    _df = pd.read_excel(supp_prod_file, dtype={"image_name": str})
    if not set(_df.columns).issuperset({"supplier_product_id", "folder"}):
        raise Exception("Master Data has missing columns!")
    _df = _df.dropna()
    return _df


if __name__ == "__main__":
    pargs = parse_args()
    logger.info("Starting to get images by folder template")
    imgs_dir = Path(pargs.images_dir)
    data = get_supplier_product_folder_data(pargs.supplier_products_file)
    if not imgs_dir.is_dir():
        raise Exception("Images dir is not a valid folder")

    asyncio.run(get_supplier_product_images_template(pargs.images_dir, imgs_dir, data))
    logger.info("Finished get images by folder template")
