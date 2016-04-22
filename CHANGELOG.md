# Change Log

## [Unreleased]
- Greatly optimized the update_chatters method

## [2.8.0] - 2016-04-22
### Removed
- Removed the following deprecated dispatch methods:
  - paid_timeout
  - unban_source
  - untimeout_source
  - last_seen

### Changed
- Major change to the way we store and cache users. Previously we cached users in-memory for 10 minutes before pushing any changes to the MySQL database. We have no removed this layer entirely, and changes made in the bot will be pushed immediately. This will greatly reduce the memory footprint of pajbot, but put a bigger strain on the database.
- Moved a bunch of columns from MySQL to redis. (num_lines, last_seen, last_active, banned, ignored)
- A bunch of more things that I don't remember, first changelog :sunglasses::ok_hand:

[Unreleased]: https://github.com/pajlada/pajbot/compare/2.8.0...HEAD
[2.8.0]: https://github.com/pajlada/pajbot/compare/2.7.4...2.8.0
