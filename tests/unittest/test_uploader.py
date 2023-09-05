# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.


from unittest.mock import patch

from uploader.utils import (
    check_next_release_name,
    get_patch_version,
    get_repositories_tags,
    get_version_from_tarball_name,
    is_valid_product_name,
)


def test_valid_product_name():
    """This function test the validity of product name."""

    v_1 = "spark-3.4.1-bin-ubuntu1-20230821132449.tgz"
    v_2 = "spark-3.3.1-bin-ubuntu1-20231201152409.zip"
    v_3 = "opensearch-2.9.0-linux-x64-ubuntu1-20230821132449.tar.gz"
    v_4 = "spark-3.4.1-bin-ubuntu100-20230821132449.tgz"
    i_1 = "spark-3.4-bin-ubuntu-1-20230821132449.tgz"
    i_2 = "spark-3.4.1-bin-ubuntu-01-20230821132449.tgz"
    i_3 = "spark-3.4.1-bin-ubuntu-01-20230821132469.tgz"
    i_4 = "spark-3.4.1-bin-ubuntu01-20230821132439.tgz"
    i_5 = "spark-3.4.1-bin-ubuntu-1-20230821132449.tgz"

    valid_names = [v_1, v_2, v_3, v_4]
    invalid_names = [i_1, i_2, i_3, i_4, i_5]

    for v in valid_names:
        assert is_valid_product_name(v)

    for v in invalid_names:
        assert not is_valid_product_name(v)


def test_get_version_tarball_name():
    """This function test the correct extraction of the tag name."""

    v_1 = "spark-3.4.1-bin-ubuntu0-20230821132449.tgz"
    v_2 = "spark-3.3.1-bin-ubuntu1-20231201152409.zip"
    v_3 = "opensearch-2.9.0-linux-x64-ubuntu1-20230821132449.tar.gz"
    v_4 = "spark-3.4.1-bin-ubuntu100-20230821132449.tgz"

    t_1 = "spark-3.4.1-bin-ubuntu0"
    t_2 = "spark-3.3.1-bin-ubuntu1"
    t_3 = "opensearch-2.9.0-linux-x64-ubuntu1"
    t_4 = "spark-3.4.1-bin-ubuntu100"

    tarball_names = [v_1, v_2, v_3, v_4]
    tags = [t_1, t_2, t_3, t_4]

    for idx, tarball_name in enumerate(tarball_names):
        assert get_version_from_tarball_name(tarball_name) == tags[idx]


def test_get_repositories_tags():
    """This function test the retrivial of repository tags."""
    tags = get_repositories_tags("canonical", "kafka-operator")
    assert len(tags) > 0


def test_check_next_release_name():
    """This function test that the new release name is valid."""
    with patch(
        "uploader.utils.get_product_tags", return_value=["spark-3.4.1-bin-ubuntu0"]
    ):
        assert check_next_release_name(
            "test-owner", "test-project", "spark", "3.4.1", "spark-3.4.1-bin-ubuntu1"
        )
        assert not check_next_release_name(
            "test-owner",
            "test-project",
            "spark",
            "3.4.1",
            "spark-3.4.1-bin-ubuntu2",
        )
    with patch("uploader.utils.get_product_tags", return_value=[]):
        assert check_next_release_name(
            "test-owner", "test-project", "spark", "3.4.1", "spark-3.4.1-bin-ubuntu0"
        )
        assert not check_next_release_name(
            "test-owner",
            "test-project",
            "spark",
            "3.4.1",
            "spark-3.4.1-bin-ubuntu1",
        )


def test_get_patch_version():
    """This function test the extraction of the patch version."""

    r_1 = "spark-3.4.1-bin-ubuntu0"
    r_2 = "spark-3.3.1-bin-ubuntu1"
    r_3 = "opensearch-2.9.0-linux-x64-ubuntu1"
    r_4 = "spark-3.4.1-bin-ubuntu100"

    p_1 = 0
    p_2 = 1
    p_3 = 1
    p_4 = 100

    release_names = [r_1, r_2, r_3, r_4]
    patches = [p_1, p_2, p_3, p_4]

    for idx, release_name in enumerate(release_names):
        assert get_patch_version(release_name) == patches[idx]
