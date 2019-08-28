import subprocess

import logging

log = logging.getLogger(__name__)


def extend_version_with_git_data(version):
    current_branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"]).decode("utf8").strip()
    latest_commit = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode("utf8").strip()[:8]
    commit_number = subprocess.check_output(["git", "rev-list", "HEAD", "--count"]).decode("utf8").strip()
    return "{0} DEV ({1}, {2}, commit {3})".format(version, current_branch, latest_commit, commit_number)


def extend_version_if_possible(version):
    try:
        return extend_version_with_git_data(version)
    except:
        log.exception("Failed to parse extra commit data, long version will be %s", version)
        return version
