# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

import fnmatch
import logging
import os
import re
import shutil
from typing import List

import requests

logger = logging.getLogger(__name__)

PRODUCT_PATTERN = "^[a-z]*-\\d[.]\\d[.]\\d-.*-ubuntu(0|[1-9][0-9]*)-(20\\d{2})[01][1-9][0-3][1-9][0-1]\\d[0-5]\\d[0-5]\\d\\S*"
TAG_PATTERN = "-(20\\d{2})[01][1-9][0-3][1-9][0-1]\\d[0-5]\\d[0-5]\\d\\S*"
RELEASE_VERSION = "^[a-z]*-\\d[.]\\d[.]\\d-.*-ubuntu(0|[1-9][0-9]*)"


def is_valid_release_version(release_version: str) -> bool:
    """This function validates the release version."""
    try:
        p = re.compile(RELEASE_VERSION)
        if p.match(release_version):
            return True
    except Exception:
        raise ValueError("Name do not match the ")
    return False


def is_valid_product_name(product_name: str) -> bool:
    """This function validates the name of the tarball."""
    try:
        p = re.compile(PRODUCT_PATTERN)
        if p.match(product_name):
            return True
    except Exception:
        raise ValueError("Name do not match the ")
    return False


def get_product_tags(
    repository_owner: str, project_name: str, product_name: str, product_version: str
):
    """This function return the tags related to a product."""
    tags = get_repositories_tags(repository_owner, project_name)
    return [t for t in tags if t.startswith(f"{product_name}-{product_version}")]


def check_release_exists(
    output_directory: str,
    tarball_pattern: str,
    repository_owner: str,
    project_name: str,
):
    """Validates that the collected builds are"""
    assert output_directory
    logger.info(f"Analyzing directory: {output_directory}")
    folders_to_delete = []
    for release_directory in os.listdir(output_directory):
        tarball_name = None
        for filename in os.listdir(f"{output_directory}/{release_directory}"):
            if fnmatch.fnmatch(filename, tarball_pattern):
                tarball_name = filename
                break
        assert tarball_name
        new_release_version = get_version_from_tarball_name(tarball_name)
        product_name = new_release_version.split("-")[0]
        product_version = new_release_version.split("-")[1]
        # check them against tags in Github
        related_tags = get_product_tags(
            repository_owner, project_name, product_name, product_version
        )
        if new_release_version in related_tags:
            folders_to_delete.append(release_directory)
            continue
        # check if the new release has a valid patch naming
        assert check_next_release_name(
            repository_owner,
            project_name,
            product_name,
            product_version,
            new_release_version,
        )

    for folder in folders_to_delete:
        logger.info(f"Deleting folder: {folder}")
        shutil.rmtree(f"{output_directory}/{folder}")


def get_patch_version(release_version: str) -> int:
    """Return the patch version from the release version."""
    if not is_valid_release_version(release_version):
        raise ValueError(f"The release version '{release_version}' is not valid!")
    return int(release_version.split("-")[-1].replace("ubuntu", ""))


def check_next_release_name(
    repository_owner: str,
    project_name: str,
    product_name: str,
    product_version: str,
    release_version: str,
) -> bool:
    """Check that the new release name is valid."""

    related_tags = get_product_tags(
        repository_owner, project_name, product_name, product_version
    )
    if not is_valid_release_version(release_version):
        raise ValueError(
            f"The inserted product version is not valid: {release_version}"
        )
    new_patch_version = get_patch_version(release_version)
    last_released_patch = -1
    if len(related_tags) != 0:
        last_tag = sorted(
            related_tags, key=lambda x: get_patch_version(x), reverse=True
        )[0]
        last_released_patch = get_patch_version(last_tag)
    if new_patch_version != last_released_patch + 1:
        logger.warning(f"Invalid release name: {release_version}")
        return False
    return True


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


def get_repositories_tags(owner: str, repository_name) -> List[str]:
    """This function return the list of tags in the database."""
    url = f"https://api.github.com/repos/{owner}/{repository_name}/tags"
    logger.debug(f"url: {url}")
    r = requests.get(url)
    logger.debug(f"status code: {r.status_code}")
    assert r.status_code == 200
    items = r.json()
    tags = []
    for item in items:
        if "name" in item:
            tags.append(item["name"])
        else:
            logger.warning(f"No key 'name' in Github API response: {item}")

    return tags
