from argparse import Namespace
from dataclasses import dataclass
from urllib.error import URLError

from launchpadlib.launchpad import Launchpad
from typing import Any, Dict, List
from urllib.parse import unquote
import argparse
import collections
import httplib2
import os
import urllib.request


LP_APP = "data-platform-java-build-app"
LP_SERVER = "production"
LP_VERSION = "devel"


@dataclass
class CIBuild:
    branch_name: str
    build_log_url: str
    ci_results: str
    date_built: str
    commit_sha1: str
    build_state: str
    artifact_urls: List[str]


def _get_tokenized_librarian_url(lp: Launchpad, file_url: str) -> str:
    """Use OAuth to get a tokenised URL for private downloads"""
    # rewrote url
    rewritten_url = file_url.replace("code.launchpad.net/", "api.launchpad.net/devel/")
    print("Rewrote {} to {} for OAuth access...".format(file_url, rewritten_url))
    print("Using OAuth'd client to get launchpad.net URL with token...")
    try:
        ret = lp._browser._connection.request(rewritten_url, redirections=0)
        # Print the response to assist debugging failures
        print(ret)
        assert False, "No redirect to download from, we can't proceed"
    except httplib2.RedirectLimit as e:
        return e.response["location"]  # type: str


def parse_args() -> Namespace:
    """Parse command line args"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--app", help="Application name, i.e: OpenSearch, Spark etc.")
    parser.add_argument(
        "--repository-url",
        type=str,
        required=True,
        help="The url of the Launchpad repository.",
    )
    parser.add_argument(
        "--branch-prefix",
        type=str,
        required=True,
        help="The prefix name of the desired branches, if not specified all branches will be scanned.",
    )
    parser.add_argument(
        "--credential-file",
        type=str,
        required=True,
        help="The path of the file that contains the Launchpad credentials.",
    )
    parser.add_argument(
        "--output-folder",
        type=str,
        required=True,
        help="The output folder where the built software will be downloaded.",
    )
    return parser.parse_args()


def get_launchpad(credential_file: str) -> Launchpad:
    """Get launchpad handler."""
    return Launchpad.login_with(
        LP_APP, LP_SERVER, credentials_file=credential_file, version=LP_VERSION, timeout=30
    )


def _get_version_urls():
    """This function returns for each version the files that needed to be downloaded."""
    pass


def get_branches_in_repo(lp: Launchpad, repo_url: str, branch_prefix: str) -> Dict[str, List[Any]]:
    """Fetch branches from repo."""
    # get repository
    repo = lp.git_repositories.getByPath(path=repo_url)

    # get all branches
    branches = list(repo.branches)

    # collect reports for the desired branches
    branch_map = collections.defaultdict(list)
    for branch in branches:
        if branch_prefix and branch_prefix not in branch.path:
            continue

        for report in repo.getStatusReports(commit_sha1=branch.commit_sha1):
            branch_map[branch.path].append(report)

    return branch_map


def get_build_runs_by_branch(branches: Dict[str, List[Any]]):
    """Fetch the list of build runs by branch."""
    branch_builds = {}

    # iterate over builds
    for branch, ci_runs in branches.items():
        print(f"Checking builds for branch: {branch}")
        if branch not in branch_builds:
            branch_builds[branch] = []

        for run in ci_runs:
            ci_build = run.ci_build

            # only consider successfully built
            if "Successfully built" not in ci_build.buildstate:
                continue

            artifact_urls = []
            for file_url in run.ci_build.getFileUrls():
                artifact_urls.append(file_url)

            branch_builds[branch].append(
                CIBuild(
                    branch,
                    ci_build.build_log_url,
                    ci_build.results,
                    ci_build.datebuilt,
                    ci_build.commit_sha1,
                    ci_build.buildstate,
                    artifact_urls,
                )
            )

    return branch_builds


def download_build_artifacts_by_branch(
    launchpad: Launchpad,
    app: str,
    branch: str,
    build_run,
    output_folder: str
) -> None:
    """Download build artifacts of a build run."""
    output_directory = f"{output_folder}/{str(branch).split('-')[-1]}"
    os.makedirs(output_directory, exist_ok=True)

    for url_file in build_run.artifact_urls:
        url = _get_tokenized_librarian_url(launchpad, url_file)
        # download each file related to the build
        file_name = str(url_file).split('/')[-1]

        # we want to skip non binaries / signature files (i.e logs )
        if app not in file_name:
            continue

        try:
            urllib.request.urlretrieve(url, f"{output_directory}/{unquote(file_name)}")
        except URLError as e:
            raise RuntimeError("Failed to download '{}'. '{}'".format(url, e.reason))


def main():
    """Download latest build software from Launchpad repository."""
    args = parse_args()

    # Get Launchpad instance
    launchpad = get_launchpad(args.credential_file)

    # fetch repositories
    branches = get_branches_in_repo(launchpad, args.repository_url, args.branch_prefix)
    if not branches:
        raise ValueError("No items to download please checks the repository or branch prefix")

    # fetch list of builds by branch
    branch_builds = get_build_runs_by_branch(branches)

    # iterate over each branch and download locally the latest build
    for branch, runs in branch_builds.items():
        if not runs:
            continue

        last_run = sorted(runs, key=lambda x: x.date_built, reverse=True)[0]
        download_build_artifacts_by_branch(
            launchpad, args.app, branch, last_run, args.output_folder
        )


if __name__ == "__main__":
    main()
