#!/usr/bin/env python3
from argparse import ArgumentParser, Namespace
from datetime import datetime
from launchpadlib.errors import HTTPError
from launchpadlib.launchpad import Launchpad
from pathlib import Path


LP_SERVER = "production"


def parse_args() -> Namespace:
    """Parse command line args."""
    parser = ArgumentParser()
    parser.add_argument("-a", "--app", help="Application name, i.e: OpenSearch, Spark etc.")
    parser.add_argument("-p", "--project", help="LP Project name.")
    parser.add_argument("-t", "--tarball", help="Tarball file path.")
    parser.add_argument("-v", "--version", help="The application version (i.e: 2.8.0)")
    parser.add_argument("-c", "--credentials", help="Credentials file to authenticate the LP client.")
    return parser.parse_args()


def get_series(lp_project, version: str):
    """Fetch the series matching the current version."""
    series_name = ".".join(version.split(".")[:2])
    return lp_project.getSeries(name=series_name)


def get_milestone(lp_project, lp_series, version: str):
    """Fetch the milestone matching this version or create one if not exists."""
    milestones = [milestone.name for milestone in lp_series.all_milestones]
    if version in milestones:
        return lp_project.getMilestone(name=version)

    return lp_series.newMilestone(name=version)


def get_release(lp_project, lp_series, lp_milestone, tarball_path: str, version: str):
    """Get release or create one if not exists."""
    releases = [release.version for release in lp_series.releases]
    if version not in releases:
        return lp_milestone.createProductRelease(
            date_released=datetime.now().isoformat(),
            release_notes=f"Release {version}.",
        )

    # here we need to delete the file matching the newly released file if any
    release = lp_project.getRelease(version=version)

    tarball_file_name = tarball_path.split("/")[-1]
    files = [f for f in release.files if str(f).split("/")[-1] == tarball_file_name]
    if files:
        try:
            files[0].delete()
        except HTTPError:
            # the LP api throws a 404 *after* deleting a file
            pass

    return release


def upload_release_files(release, app: str, tarball_file_path: str, version: str):
    """Upload the tarball and signature file if any."""
    tarball = Path(tarball_file_path)
    signature = Path(f"{tarball_file_path}.asc")

    payload = {
        "content_type": "application/x-gtar",
        "description": f"{app} {version}",
        "file_content": tarball.read_bytes(),
        "file_type": "Code Release Tarball",
        "filename": str(tarball.name),
    }
    if signature.exists():
        payload["signature_content"] = signature.read_bytes()
        payload["signature_filename"] = str(signature.name)

    release.add_file(**payload)


def main():
    """Download and store latest release artifacts for the release branches of a product."""
    args = parse_args()

    # get launchpad client
    launchpad = Launchpad.login_with(args.project, LP_SERVER, credentials_file=args.credentials)
    lp_project = launchpad.projects[args.project]

    # fetch project series matching with version
    lp_series = get_series(lp_project, args.version)

    # get milestone or create if not exists
    lp_milestone = get_milestone(lp_project, lp_series, args.version)

    # get release or create if not exists
    lp_release = get_release(lp_project, lp_series, lp_milestone, args.tarball, args.version)

    # upload the tarball and signature file if any
    upload_release_files(lp_release, args.app, args.tarball, args.version)


if __name__ == "__main__":
    main()
