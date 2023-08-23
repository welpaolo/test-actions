# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

import re
from typing import List

import git

PRODUCT_PATTERN = "^[a-z]*-\\d[.]\\d[.]\\d-.*-ubuntu-(0|[1-9][0-9]*)-(20\\d{2})[01][1-9][0-3][1-9][0-1]\\d[0-5]\\d[0-5]\\d\\S*"
TAG_PATTERN = "-(20\\d{2})[01][1-9][0-3][1-9][0-1]\\d[0-5]\\d[0-5]\\d\\S*"


def is_valid_product_name(product_name: str) -> bool:
    """This function validates the name of the tarball."""
    try:
        p = re.compile(PRODUCT_PATTERN)
        if p.match(product_name):
            return True
    except Exception:
        raise ValueError("Name do not match the ")
    return False


def check_if_version_published(
    folder: str, tarball_regex: str, published_version: List[str]
) -> bool:
    """This function check if a specific version has been already published."""
    return False


def get_published_version() -> List[str]:
    """This function returns the published versions."""

    return []


def get_version_from_filename(artifact_name: str) -> str:
    """Get version from tarball filename."""
    raise NotImplementedError


def download_checksum(url: str) -> str:
    """This function download the checksum from Github."""
    raise NotImplementedError


def get_version_from_tarball_name(tarball_name: str) -> str:
    """This function extract the the tag name that will used for the release."""
    assert is_valid_product_name(tarball_name)

    try:
        p = re.compile(TAG_PATTERN)
        items = p.split(tarball_name)
        return items[0]
    except Exception:
        raise ValueError("ERROR")


def get_repo_tags(url: str, prefix: str) -> List[str]:
    """This function return the list of tags in the database."""
    repo = git.Repo(url)
    tags = sorted(repo.tags, key=lambda t: t.commit.committed_datetime)
    return [item for item in tags if item.startswith(prefix)]
