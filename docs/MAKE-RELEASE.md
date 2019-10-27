# Making a release

## For the Pull Request

- Update CHANGELOG.md, add entry inbetween `## Unversioned` and any changelog entries with `## YOUR.VERSION`
- Look through the changelog entries of this version, and reorder any entries so the most important changes are at the top of each category
- Update pajbot/constants.py

## After the Pull Request has been accepted

- Tag the release: `git tag YOUR.VERSION -am "YOUR.VERSION"`
- Push the tag: `git push --tags`
