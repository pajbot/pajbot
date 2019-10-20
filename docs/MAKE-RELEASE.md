# Making a release

## For the Pull Request

- Update CHANGELOG.md, add entry inbetween `## Unversioned` and any changelog entries with `## YOUR.VERSION`
- Update pajbot/constants.py

## After the Pull Request has been accepted

- Tag the release: `git tag YOUR.VERSION -am "YOUR.VERSION"`
- Push the tag: `git push --tags`
