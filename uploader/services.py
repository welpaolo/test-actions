# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

import logging
from argparse import ArgumentParser, Namespace
from enum import Enum

from utils import get_version_from_tarball_name, is_valid_product_name

logger = logging.getLogger(__name__)


class Actions(str, Enum):
    NAME = "get-name"
    VERSION = "get-version"
    VALID_NAME = "validate-name"
    # here
    LIST = "list"


def create_services_parser(parser: ArgumentParser) -> ArgumentParser:
    subparser = parser.add_subparsers(dest="action")
    subparser.required = True

    # parser_name = subparser.add_parser(Actions.NAME.value)
    # parser_name.add_argument('-n', '--name', type=str, help="Name of the ")

    parser_tag = subparser.add_parser(Actions.VERSION.value)
    parser_tag.add_argument(
        "-n", "--name", type=str, help="Extract the version from the product name."
    )

    parser_validation = subparser.add_parser(Actions.VALID_NAME.value)
    parser_validation.add_argument(
        "-n", "--name", type=str, help="Validate the name of the tarball."
    )

    return parser


def main(args: Namespace):
    logger.info("HERE")

    if args.action == Actions.VERSION:
        if is_valid_product_name(args.name):
            print(get_version_from_tarball_name(args.name))
            exit(0)
        raise ValueError("Invalid product name!")

    elif args.action == Actions.VALID_NAME:
        if is_valid_product_name(args.name):
            exit(0)
        raise ValueError("Invalid product name!")


if __name__ == "__main__":
    args = create_services_parser(
        ArgumentParser(description="Services utils for the Github Central Uploader")
    ).parse_args()
    main(args)
