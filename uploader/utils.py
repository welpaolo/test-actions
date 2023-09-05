# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

import fnmatch
import logging
import os
import re
import shutil
import tarfile
import zipfile
from typing import List

import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)

PRODUCT_PATTERN = "^[a-z]*-\\d[.]\\d[.]\\d-.*-ubuntu(0|[1-9][0-9]*)-(20\\d{2})[01][1-9][0-3][1-9][0-1]\\d[0-5]\\d[0-5]\\d\\S*"
TAG_PATTERN = "-(20\\d{2})[01][1-9][0-3][1-9][0-1]\\d[0-5]\\d[0-5]\\d\\S*"
RELEASE_VERSION = "^[a-z]*-\\d[.]\\d[.]\\d-.*-ubuntu(0|[1-9][0-9]*)"

CUSTOM_KEYMAP = [".jar", ".pom", ".sha1", ".sha256", ".sha512"]


def file_comparator(file: str):
    """Comparator for ordering file extensions for upload."""
    if os.path.splitext(file)[1] in CUSTOM_KEYMAP:
        return CUSTOM_KEYMAP.index(os.path.splitext(file)[1])
    return 100


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
    return [
        t
        for t in tags
        if t.startswith(f"{product_name}-{product_version}")
        and is_valid_release_version(t)
    ]


def check_new_releases(
    output_directory: str,
    tarball_pattern: str,
    repository_owner: str,
    project_name: str,
):
    """Iterate over most recents releases and check if they need to be released."""
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
        # delete folder with release if already published
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


def get_jars_in_tarball(tarball_path: str) -> List[str]:
    """Return all the jars contained into a tarball."""
    os.mkdir("tmp")

    with tarfile.open(tarball_path) as file:
        file.extractall("tmp/")

        jar_filenames = [
            filename
            for _, _, files in os.walk("tmp/")
            for filename in files
            if filename.endswith(".jar")
        ]

    logger.info(f"Number of jars: {len(jar_filenames)}")
    shutil.rmtree("tmp")
    return jar_filenames


def upload_jars(
    tarball_path: str,
    maven_repository_archive: str,
    artifactory_repository: str,
    artifactory_username: str,
    artifactory_password: str,
):
    """Upload jars to artifactory."""
    jars_to_upload = get_jars_in_tarball(tarball_path)
    os.mkdir("tmp")
    with zipfile.ZipFile(maven_repository_archive, "r") as zip:
        zip.extractall("tmp/")

    subdirs = []
    folder = "tmp/repository/"
    for subdir, _, files in os.walk(folder):
        for file in files:
            if file.endswith(".jar"):
                if file in jars_to_upload:
                    logger.info(f"subdir: {subdir}")
                    subdirs.append(subdir)

    for subdir in subdirs:
        files = sorted(os.listdir(subdir), key=file_comparator)
        for file in files:
            # skip temp files or metadata
            if file.startswith("_") or file.endswith(".repositories"):
                continue
            url = f"{artifactory_repository}{subdir.replace(folder,'')}/{file}"
            logger.debug(f"upload url: {url}")
            headers = {"Content-Type": "application/java-application"}
            r = requests.put(
                url,
                headers=headers,
                data=open(f"{subdir}/{file}", "rb"),
                auth=HTTPBasicAuth(artifactory_username, artifactory_password),
            )
            assert r.status_code == 201

    shutil.rmtree("tmp")


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
