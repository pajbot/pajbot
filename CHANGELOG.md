# Change Log

## [Unreleased]
### Changed
- Quests can now reward points and any variable amount of tokens.
- Tokens no longer expire after 3 streams. You instead have a maximum amount of tokens.

### Added
- New API endpoint: /api/v1/pleblist/top - lists the top pleblist songs
- Reasons to most timeouts
- New websocket event: refresh/reload - refreshes the clr page
- New websocket event: show_custom_image - shows a custom image URL on screen
- New Handler: send_whisper(user, message)

### Fixed
- @-replacements now work properly in Paid Timeouts

## [2.8.1] - 2016-05-13
### Changed
- Greatly optimized the update_chatters method
- Trimmed the size of username/username_raw in the user table
- Added an index to points in the user table
- BTTV Channel emotes are now stored as a hash with the emote_hash instead of a list.
- /api/v1/user/<username> now returns points_rank instead of rank for the points rank.
- Refactored all the API code to be better structured
- Reorganized how the web app is started, cleaning up app.py a lot
- The HSbet reminders now print stats about how many points are bet on win and how many points are
  bet on lose.
- Added navigation links on the /pleblist/history page

### Added
- New broadcaster command: !editpoints - creates or removes points to a user
- New HSbet command: !hsbet stats - whispers you the current win/lose points that are bet on the game.
- A flag to commands to specify whether they should whisper you if you don't have enough points

### Fixed
- The User check on /points no longer 500's
- The /stats page no longer 500's
- Fixed a mysterious bug where username_raw was being HDEL'd all the time :sunglasses:
- The /user profile page now shows messages in chat properly

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
[2.8.1]: https://github.com/pajlada/pajbot/compare/2.8.0...2.8.1
