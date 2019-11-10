# Environment variables

### PB1_BRANCH, PB1_COMMIT, PB1_COMMIT_COUNT

Used as a fallbacks if `git` is not available, to expand the version information.

You would typically set these to the output of the following commands:

- `PB1_BRANCH`: `git rev-parse --abbrev-ref HEAD`
- `PB1_COMMIT`: `git rev-parse HEAD`
- `PB1_COMMIT_COUNT`: `git rev-list HEAD --count`
