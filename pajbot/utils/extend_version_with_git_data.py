from typing import Tuple

import logging
import os
import subprocess

log = logging.getLogger(__name__)


def _read_git_info_from_subprocess() -> Tuple[str, str, str]:
    current_branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"]).decode("utf8").strip()
    latest_commit = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode("utf8").strip()[:8]
    commit_number = subprocess.check_output(["git", "rev-list", "HEAD", "--count"]).decode("utf8").strip()
    return current_branch, latest_commit, commit_number


def _read_git_info_from_environment_variables() -> Tuple[str, str, str]:
    # These fail with a KeyError if one of these is not set
    current_branch = os.environ["PB1_BRANCH"]
    latest_commit = os.environ["PB1_COMMIT"][:8]
    commit_number = os.environ["PB1_COMMIT_COUNT"]
    return current_branch, latest_commit, commit_number


def extend_version_with_git_data(version: str) -> str:
    try:
        current_branch, latest_commit, commit_number = _read_git_info_from_subprocess()
    except:
        current_branch, latest_commit, commit_number = _read_git_info_from_environment_variables()
    return f"{version} DEV ({current_branch}, {latest_commit}, commit {commit_number})"


def extend_version_if_possible(version: str) -> str:
    # we first try to use "git" subprocess directly, if that fails, we try to read environment variables,
    # if that also fails, the version is not expanded at all.
    try:
        return extend_version_with_git_data(version)
    except:
        log.exception("Failed to parse extra commit data, long version will be %s", version)
        return version
