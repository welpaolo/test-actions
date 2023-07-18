from argparse import ArgumentParser
import argparse
import collections
from dataclasses import dataclass
import os
import sys
from typing import List
from urllib.error import URLError
from launchpadlib.launchpad import Launchpad
import urllib.request
import httplib2

# repo-url
# branch prefix
# credential-files
# output folder

@dataclass
class CIBuild:
    branch_name: str
    build_log_url: str
    ci_results: str
    date_built: str
    commit_sha1: str
    build_state: str
    artifact_urls: List[str]

def _get_tokenised_librarian_url(lp: Launchpad, file_url: str):
	'''Use OAuth to get a tokenised URL for private downloads'''
	# rewrote url
	rewritten_url = file_url.replace('code.launchpad.net/', 'api.launchpad.net/devel/')
	print('Rewrote {} to {} for OAuth access...'.format(file_url, rewritten_url))
	print("Using OAuth'd client to get launchpad.net URL with token...")
	try:
		ret = lp._browser._connection.request(rewritten_url, redirections=0)
		# Print the response to assist debugging failures
		print(ret)
		assert False, "No redirect to download from, we can't proceed"
	except httplib2.RedirectLimit as e:
		location = e.response['location']  # type: str
		return location

def add_config_arguments() -> ArgumentParser:
    """
    Add arguments to the parser.
    """
    parser = argparse.ArgumentParser()
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
    return parser

def get_launchpad(credential_file:str) -> Launchpad:
    """Get launchpad handler."""
    launchpad = Launchpad.login_with('hello-world', 'production', credentials_file=credential_file, version='devel',timeout=30)
    return launchpad

def _get_version_urls():
    """This function returns for each version the files that needed to be downloaded."""
    pass

def download_build_from_lp(
    launchpad: Launchpad,
    repo_url: str, 
    branch_prefix: str,
    output_folder: str) -> None:
    """Download latest build software from Launchpad repository."""
    
    # get repository
    r = launchpad.git_repositories.getByPath(path=repo_url)

    # get all branches
    branches = list(r.branches)

    # collect reports for the desired branches
    branch_map = collections.defaultdict(list)
    for branch in branches:
        if branch_prefix is None or branch_prefix in branch.path: 
            for report in r.getStatusReports(commit_sha1=branch.commit_sha1):
                branch_map[branch.path].append(report)
    
    if len(branch_map) == 0:
        raise ValueError(f"No items to download please checks the repository or branch prefix")
    
    branch_builds = {}
    
    # iterate over builds 
    for branch, ci_runs in branch_map.items():
        print(f"Checking builds for branch: {branch}")
        if branch not in branch_builds:
            branch_builds[branch] = []
        for run in ci_runs:
            build_log_url = run.ci_build.build_log_url
            ci_results = run.ci_build.results
            date_built = run.ci_build.datebuilt
            commit_sha1 = run.ci_build.commit_sha1
            build_state = run.ci_build.buildstate
            # only consider successfully built 
            if "Successfully built" not in build_state:
                continue
            artifact_urls = []
            for file_url in run.ci_build.getFileUrls():
                artifact_urls.append(file_url)
            c_build = CIBuild(branch, build_log_url, date_built,ci_results,commit_sha1, build_state, artifact_urls)
            branch_builds[branch].append(c_build)
        
    # iterate over each branch and download the latest build
    for branch, runs in branch_builds.items():
        if len(runs) == 0:
            continue
        sorted_runs = sorted(runs, key=lambda x: x.date_built, reverse=True)
        last_run = sorted_runs[0]
        
        output_directory = f"{output_folder}/{str(branch).split('/')[-1]}"
        os.mkdir(output_directory)
        
        for url_file in last_run.artifact_urls:
            url = _get_tokenised_librarian_url(launchpad, url_file)
            # download each file related to the build
            file_name = str(url_file).split('/')[-1]
            try: 
                urllib.request.urlretrieve(url, f"{output_directory}/{file_name}")
            except URLError as e:
                raise RuntimeError("Failed to download '{}'. '{}'".format(url, e.reason))
    
        
if __name__ == "__main__":
    parser = add_config_arguments()
    args = parser.parse_args()
    repo_url = args.repository_url
    branch_prefix = args.branch_prefix
    credential_file = args.credential_file
    output_folder = args.output_folder
    # Get Launchpad instance    
    launchpad = get_launchpad(credential_file)
    # Download latests build from Launchpad
    download_build_from_lp(launchpad, repo_url, branch_prefix, output_folder)