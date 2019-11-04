# Changelog

## Unversioned

- Major: `pleblist_song` table mistakenly wiped any non-user-connected rows in v1.38, this version will make the `pleblist_song` table able to contain non-user-connected rows again.

  Here is how you can recover the data, should you be affected:

  ```bash
  # Replace "streamer_name" with the name of the streamer in all commands below

  # Create new database to restore into
  sudo -u postgres createdb pajbot_restore --owner=pajbot

  # Restore the backup into the "pajbot_restore" database
  sudo -u pajbot psql pajbot_restore < pre-user-migration-backup.sql

  # Get the data that was in the pleblist_song and user table in the pre-migration database state
  sudo -u pajbot psql pajbot_restore -c "COPY (SELECT * FROM pajbot1_streamer_name.pleblist_song) TO STDOUT" > pleblist_song_old.txt
  sudo -u pajbot psql pajbot_restore -c "COPY (SELECT * FROM pajbot1_streamer_name.user) TO STDOUT" > user_old.txt

  # Drop the temporary database again
  sudo -u postgres dropdb pajbot_restore

  # Then run the final restore script: This loads data from "pleblist_song_old.txt" and "user_old.txt" and restores
  # into the pleblist_song table inside the schema you specify (pajbot1_streamer_name)
  # To customize the file paths, adjust the script itself
  sudo -u pajbot psql pajbot -c "SET search_path=pajbot1_streamer_name" -f ./scripts/restore-pleblist-songs.sql
  ```

- Minor: Emote command (e.g. !bttvemotes) cooldowns and level can now be configured in the modules settings.
- Minor: The end message sent when a negative raffle ends now says "lost X points" correctly, instead of "won -X points".
- Minor: Duels now automatically expire and get cancelled if they are not accepted within 5 minutes (Time amount can be configured as a module setting).
- Minor: The regular refresh of the points_rank and num_lines_rank is now randomly jittered by ±30s to reduce CPU spikes when multiple instances are restarted at the same time
- Minor: Added setting to configure bypass level to "Link Checker" module.
- Minor: The bot now uses the BTTV v3 API, which should fix some cases where the bot considered more emotes to be enabled than were actually supposed to be enabled.
- Minor: The points gain rate information at the top of the points page is now dynamically updated based upon your settings for the "Chatters Refresh" module.
- Minor: "dev" config flag is now respected in web, properly omitting any git information in its footer
- Minor: The subscriber badge is now automatically downloaded on web application startup. Which version of the subscriber badge should be downloaded can be configured in config.ini under the `web` section using the `subscriber_badge_version` key. Setting the `subscriber_badge_version` key to `-1` disables the sub badge downloading, in case you want to use a custom subscriber badge (or an old one that you don't want to overwrite)
- Minor: Dates/Times on the website are now all shown in the user's time zone and formatted based on the viewer's locale. Note for the bot operator: You can remove the `timezone=` setting under `[main]`, since it's no longer needed.
- Minor: Fix table sorting in the modules page.
- Minor: Removed last remnants of already defunct Pleblist StreamTip integration
- Bugfix: Fixed two more cases of long-running transactions not being closed, which in turn could cause the database server to run out of disk space (#648)
- Bugfix: Fixed an exception and the message not being handled whenever a message contained an emote modified via the "Channel Points" Twitch feature.
- Bugfix: Fixed an exception whenever the result of a command was being checked by the massping module.
- Bugfix: Fixed a lot of log-spam and the subscribers refresh not working when the bot was running in its own channel. Re-authorize via `/bot_login` after this update if you were affected by this issue before.
- Bugfix: Fixed subscriber update failing if the broadcaster had no subscription program.
- Bugfix: Fixed points_rank and num_lines_rank never refreshing automatically.
- Bugfix: Mass ping protection will no longer count inactive users (never seen before or seen longer than 2 weeks ago).
- Bugfix: Fixed single raffle silently failing when finishing. #610
- Bugfix: Fixed !dubtrack previous/!lastsong printing the current song instead of the previous song

## v1.38

Remember to bring your dependencies up to date with `./scripts/venvinstall.sh` when updating to this version!

- Major: User data is not stored in redis anymore. Relevant data will automatically be migrated.
- Major: Added automatic support for Twitch name changes. (`!namechange` command has been removed.)

  This includes a potentially quite large (might take long on large databases) automatic migration that will:

  - Query the Twitch API for the User ID of all your current existing users, and
  - Delete data about the users that don't exist on Twitch anymore.

  For this reason, a database backup for your old data is recommended before this upgrade:

  ```bash
  sudo -u pajbot pg_dump --file=sql_dump_streamer.sql --schema=pajbot1_streamer pajbot
  sudo -u pajbot pg_dump --file=sql_dump_all.sql pajbot
  sudo -u pajbot ./scripts/redis-dump.py streamer > redis_dump_streamer.bin
  ```

  When migrating a bot you probably want to either disable the chatters microservice entirely, or remove that bot's entry from the chatters `config.json`.

- Feature: Added module to fetch current chatters and update the database back to the bot (was previously [a microservice](https://github.com/pajbot/chatters)). Includes a new `!reload chatters` command.
- Feature: Added `!reload subscribers` command to force refresh of subscriber status in the DB.
- Minor: You can now reference users by their display name, even if the display name contains asian characters (e.g. `!checkmod 테스트계정420` finds the user correctly).
- Minor: Messages shared with the streamer as part of resub messages are now processed like normal chat messages (They were not processed at all before).
- Minor: Added `?user_input=true` optional parameter to `/api/v1/users/:login` endpoint to query for usernames more fuzzily.
- Minor: Added `/api/v1/users/id/:id` to look up users by ID.
- Minor: Removed system to synchronize points updates to StreamElements.
- Minor: Small improvement made to the efficiency of caching data from the Twitch API.
- Minor: Added the `points_rank` user property back.
- Minor: Added a dump/restore utility for redis data to the `scripts` directory.
- Minor: Removed some unfinished test code related to notifications.
- Minor: Placed reasonable minimum/maximum limits on the `Seconds until betting closes` setting for the HSBet module.
- Minor: Added setting to adjust points tax for the duel module
- Minor: Link checker module now prints far less debug info about itself.
- Minor: Added possibility to modify command token cost using `--tokens-cost` in `!add command`/`!edit command` commands.
- Minor: Added two pluralization cases for when only a single user wins a multi-raffle.
- Minor: Added logging output for notices received from the SQL server.
- Minor: The bot automatically now additionally refreshes who is a moderator and who isn't (This data was previously only updated when the user typed a message). A `!reload moderators` command has been added to trigger this update manually.
- Minor: Added a lot more data to the output message of the `!debug user` command.
- Bugfix: Errors in the main thread no longer exit the bot (#443)
- Bugfix: Several places in the bot and Web UI now correctly show the user display name instead of login name
- Bugfix: Removed unfinished "email tag" API.
- Bugfix: If the bot is restarted during an active HSBet game, bets will no longer be lost.
- Bugfix: Web process no longer creates a super long-running database transaction that was never closed.
- Bugfix: Will no longer run all redis migrations on every bot startup.
- Bugfix: Fixed a crash when an app access token expired and needed to be refreshed.

## v1.37

Remember to bring your dependencies up to date with `./scripts/venvinstall.sh` when updating to this version!

- Breaking: pajbot now uses PostgreSQL instead of MySQL as its supported
  database engine. It is not possible to continue to use MySQL.  
  To migrate your existing database(s):

  - Install new requirements from apt: `sudo apt-get install libpq-dev`
  - Bring your installed dependencies up-to-date with `./scripts/venvinstall.sh`
  - Install and start PostgreSQL, if you have not done so already
  - Create the pajbot PostgreSQL user, a database and optionally a schema for
    the bot to use. (see the updated SQL section of
    [the install docs](./install-docs/debian10/install-debian10.txt))
  - Edit `./scripts/migrate-mysql-to-postgresql.py` with a connection string for
    the old MySQL database, and your new PostgreSQL database.
  - Stop pajbot:
    `sudo systemctl stop pajbot@streamername pajbot-web@streamername`
  - Backup your data:
    `sudo mysqldump --single-transaction --result-file=mysql-dump-streamername.sql pajbot_streamername`
  - Activate the python virtualenv: `source venv/bin/activate`
  - Run `./scripts/migrate-mysql-to-postgresql` to move the data
  - Update the `sql` connection string in your bot config (see the updated
    [example config](./install-docs/debian10/kkonatestbroadcaster.ini) for
    examples)
  - Start pajbot again:
    `sudo systemctl start pajbot@streamername pajbot-web@streamername`
  - Drop the old MySQL database:
    `sudo mysql -e "DROP DATABASE pajbot_streamername"`

  The procedure for new bot installations is described in the
  [install documentation](./install-docs).

- Breaking: If you were using the
  [chatters microservice](https://github.com/pajbot/chatters), you must update
  it to be able to use it after the PostgreSQL update.
- Breaking (if you rely on it in an automatic way somehow): `venvinstall.sh` has
  been moved from `./install` into `./scripts`, where all other shell scripts
  also reside.
- Major: Official support for python 3.5 has been removed. Only python 3.6 or
  above will be supported from this release on.
- Feature: Added `!namechange <oldusername> <newusername>` command for migrating
  users that changed their twitch name. (Level 2000 only).
  `./scripts/transfer-{all,sql,redis}` scripts have been removed.
- Minor: Removed `!reload` command since it did nothing.
- Minor: Modules can now be configured to only allow users above a certain level to configure them. #108
- Minor: Removed "Personal Uptime" module.
- Bugfix: A series of bugs (including the `!laststream` command sometimes not
  working) caused by a mismatch of datetime-aware and datetime-naive objects.
- Bugfix: If redis is busy loading data, the bot no longer exists, and waits for
  completion instead.
- Bugfix: `/api/v1/user/:username` no longer fetches `nl_rank` from redis twice.
- Bugfix: If no git data is available, web interface will no longer show
  `Last commit:`, instead last commit will be omitted altogether
- Bugfix: Fixed a series of bugs (including the `!laststream` command sometimes
  not working) caused by a mismatch of datetime-aware and datetime-naive
  objects.
- Bugfix: Commands are now only checked against banphrases, ascii and massping
  checks if you enabled `run_through_banphrases` (e.g. via `--checkmsg`) (#478)
- Bugfix: Subscribers refresh now correctly sets the `active_subs` KVI value.
- Bugfix: You can no longer ignore yourself
- Bugfix: You can now use the same phrases (1k, "all", etc.) with the `!givepoints` command.
- Documentation Bugfix: `$(urlfetch)` returns the response body, not request
  body

<!--
- Internal: New (stupider) migrations system that directly uses SQL, and can additionally
  also migrate redis and other resources.
- Internal: Removed last remnants of highlight system (`bot.trusted_mods` and
  `trusted_mods` config option)
- Internal: Made `Bot` initialization clearer by moving everything into
  `__init__`
- Internal: Each utility is in its own file now
- Internal: Removed dead code/comments in various places
- Internal: Removed duplication in `UserManager` and with git version fetching
- Internal: `ActionManager` now accepts `*args` and `**kwargs` instead of a list
  and a dict. (Easier to use)
-->

## v1.36

- Breaking: In your `config.ini`, rename `[webtwitchapi]` to `[twitchapi]` and
  delete the old `[twitchapi]` config file entry. See
  [the example config](https://github.com/pajbot/pajbot/blob/677651d416fa60c80ef939df8666bf554237ae0d/install-docs/debian10/kkonatestbroadcaster.ini#L62)
  for example values.
- Breaking: a `redirect_uri` is now always required under `[twitchapi]` in your
  `config.ini`.
- Breaking: If you want to continue fetching subscribers, you will need to have
  the streamer log in once with `/streamer_login`. Then the bot will
  automatically start fetching a list of subscribers regularly.
- Major: To be able to use game and title updates with `!settitle` and
  `!setgame`, re-authenticate the bot with `/bot_login`. Then ask the streamer
  to add the bot as a channel editor.
- Major: Dependency on `twitch-api-v3-proxy` has been removed. You can uninstall
  that service if you were running it. (The bot now uses the new Twitch v5 and
  Helix APIs)
- Feature: Dubtrack module can now show requester
- Feature: Dubtrack module can automatically post a message when a new song
  starts playing
- Bugfix: Fix a recurring error that could appear when fetching the stream
  live/offline status.
- Bugfix: Make subscriber fetch routine more accurate (will now fetch the
  correct/accurate number of subscribers)
- Bugfix: `!settitle` and `!setgame` are now packaged as a module, you no longer
  need to add these commands as `funccommand`s.
- Bugfix: Updated link checker module to use the latest version of the safe
  browsing API.

## Older versions

Changelogs were kept sporadically before this point

## 2016-05-26

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

## 2016-05-13

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

## 2016-04-22

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
