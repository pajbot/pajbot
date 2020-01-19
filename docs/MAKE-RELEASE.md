# Making a release

Replace `v1.23` with the new version in the commands/examples below.

## For the Pull Request

- Update `CHANGELOG.md`, replace `## Unversioned` with `## v1.23` and add a new empty `## Unversioned` section above `## v1.23`.
- Look through the changelog entries of this version, and reorder any entries so the most important changes are at the top of each category
- Update `pajbot/constants.py` with the new version

## After the Pull Request has been accepted

- Tag the release: `git tag v1.23 -am "v1.23"`
- Push the tag: `git push --tags`
- Update the `stable` branch to point to the new release: `git checkout stable && git merge --ff-only v1.23`
