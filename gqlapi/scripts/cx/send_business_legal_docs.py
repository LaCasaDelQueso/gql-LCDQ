""" Script to Send Legal docs to team


Usage:
    cd projects/gqlapi/
    python -m gqlapi.scripts.cx.send_business_legal_docs --help
"""
import asyncio
import argparse
import logging
import uuid

from gqlapi.lib.environ.environ.environ import Environment, get_env
from gqlapi.lib.logger.logger.basic_logger import get_logger
from gqlapi.mongo import mongo_db as MongoDatabase
from gqlapi.utils.cx import send_business_docs

logger = get_logger(
    "gqlapi.scripts.send_business_legal_docs", logging.INFO, Environment(get_env())
)


# arg parser
def parse_args() -> argparse.Namespace:
    """Parse the command line arguments."""
    parser = argparse.ArgumentParser(description="Send Legal Docs.")
    parser.add_argument(
        "--email",
        help="Email to send docs to.",
        type=str,
        default="sellers@alima.la",
    )
    parser.add_argument(
        "--business_id",
        help="Business ID to send docs to. (restaurant or supplier)",
        type=str,
        default=False,
        required=True,
    )
    parser.add_argument(
        "--business_account_type",
        help="Business account type (restaurant or supplier)",
        type=str,
        choices=["restaurant", "supplier"],
        default=None,
        required=True,
    )
    return parser.parse_args()


async def main():
    args = parse_args()
    logging.info(f"Starting sending {args.business_id} docs to: {args.email} ...")
    try:
        fl = await send_business_docs(
            MongoDatabase,
            args.email,
            args.business_account_type,
            uuid.UUID(args.business_id),
        )
        if not fl:
            logging.info(
                f"NOT able to send docs from {args.business_id} to {args.email}"
            )
            return
        logging.info(f"Successfully sent docs to: {args.email}")
    except Exception as e:
        logging.error(f"Error sending docs to: {args.email}")
        logging.error(e)


if __name__ == "__main__":
    asyncio.run(main())
