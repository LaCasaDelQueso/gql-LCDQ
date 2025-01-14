from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.config import CLOUDINARY_BASE_URL
from gqlapi.lib.logger.logger.basic_logger import get_logger
import os
from typing import Any, Dict, List
from enum import Enum
import cloudinary
import cloudinary.uploader
import cloudinary.api
import requests
import strawberry

logger = get_logger(get_app())
version = "1690931377"


@strawberry.enum
class Folders(Enum):
    MARKETPLACE = "alima-marketplace"
    SUPPLIER = "supplier"
    SUPPLIER_PRODUCTS = "prods"
    PROFILE = "profile"


@strawberry.enum
class ImageType(Enum):
    LOGO = "logo"
    ICON = "icon"
    BANNER = "banner"


@strawberry.enum
class Extensions(Enum):
    PNG = ".png"
    JPG = ".jpg"


def construct_route(base_url: str, width: str, route: str) -> str:
    return f"{base_url}w_{width}/v{version}/{route}{Extensions.PNG.value}"


def construct_route_jpg_to_invoice(route: str) -> str:
    CLOUDINARY_BASE_URL_TO_INVOICE = CLOUDINARY_BASE_URL.replace(
        "/c_scale,f_auto,q_auto,", ""
    )
    return f"{CLOUDINARY_BASE_URL_TO_INVOICE}/v{version}/{route}{Extensions.JPG.value}"


class CloudinaryApi:
    """Requires environment variable with access to cloudinary

    CLOUDINARY_URL="cloudinary://xxxxx:yyyyy@zzzzz"
    """

    def __init__(self, env) -> None:
        self.base_folder = "PROD" if env.lower() == "prod" else "STG"

    def upload(
        self, img_file: bytes | Any, folder: str, subfolder: str, img_key: str
    ) -> Dict[Any, Any]:
        try:
            cloudinary.uploader.destroy(
                f"{folder}-{self.base_folder}/{subfolder}/{img_key}", invalidate=True
            )

            route = f"{folder}-{self.base_folder}/{subfolder}/{img_key}"
            upload_result = cloudinary.uploader.upload(
                img_file,
                folder=f"{folder}-{self.base_folder}/{subfolder}/",
                public_id=img_key,
                overwrite=True,
                invalidate=True,
                resource_type="image",
            )
            # Transform the image to PNG format
            png_transformation = {"format": "png"}
            cloudinary.CloudinaryImage(upload_result["public_id"]).build_url(
                transformation=png_transformation
            )
            return {"status": "ok", "data": route}
        except Exception as e:
            logger.error(e)
            return {"status": "error", "msg": str(e)}

    def delete(self, folder: str, subfolder: str, img_key: str) -> Dict[Any, Any]:
        try:
            cloudinary.uploader.destroy(
                f"{folder}-{self.base_folder}/{subfolder}/{img_key}", invalidate=True
            )
            return {"status": "ok", "msg": "ok"}
        except Exception as e:
            logger.error(e)
            return {"status": "error", "msg": str(e)}

    def get_image_urls(self, directory: str):
        # List all resources in the specified directory
        resources = cloudinary.api.resources(
            type="upload",
            prefix=directory,
            max_results=600,  # Adjust the max_results as needed
        )
        # [TODO] SAVE IN EXCEL
        # Extract URLs from the resources
        return [resource["secure_url"] for resource in resources["resources"]]

    def download_images(self, image_urls: List, download_path: str):
        for url in image_urls:
            response = requests.get(url)
            if response.status_code == 200:
                with open(
                    os.path.join(download_path, url.split("/")[-1]), "wb"
                ) as file:
                    file.write(response.content)
                print(f"Downloaded: {url}")
            else:
                print(f"Failed to download: {url}")
