# Changelog

## Unversioned

Remember to bring your dependencies up to date with `./scripts/venvinstall.sh` when updating to this version!

## v1.53

Remember to bring your dependencies up to date with `./scripts/venvinstall.sh` when updating to this version!

- Major: Added support for 7tv.app emotes (#1256, #1260, #1261, #1317)
- Minor: Added `can_execute_with_whisper`, `sub_only`, `mod_only` & `run_through_banphrases` fields to create command page. (#1310)
- Minor: Added ability to multiply number of raiders by the points awarded. (#1319)
- Minor: Added support for the `extendsub` msg-id to the `subalert` module. (#1311, #1318)
- Minor: Added support for the `giftpaidupgrade` msg-id to the `subalert` module. (#1306, #1315, #1318)
- Minor: Migrate from Kraken to Helix for global emote fetching. (#1289)
- Minor: Migrate from `twitchemotes.com` to Helix for channel emote fetching. (#1290)
- Minor: Added `mod_only` & `run_through_banphrases` fields to edit command page. (#1293)
- Bugfix: Fixed issue where bot would take points and attempt to enable/disable subonly mode when subonly was already enabled/disabled. (#1309)
- Bugfix: Stop `USERNOTICE` events occurring in a bot hub from being processed. (#1314)
- Bugfix: Fixed issue where bot would take points and attempt to untimeout/unban a user that isn't timed out or banned in the paidtimeout module. (#1308)
- Bugfix: Fixed issue where level 2000 users couldn't bypass the cooldown of the playsounds module. (#1292)
- Bugfix: Users can no longer bypass long massping timeouts by also typing a banphrase in their message. (#1117, #1209, #1253)
- Bugfix: Twitter (un)follow buttons in admin zone work again. (#1250)
- Bugfix: Users with level > 2000 are now also shown as admins on the web moderators page. (#1324, #1326)

## v1.52

Remember to bring your dependencies up to date with `./scripts/venvinstall.sh` when updating to this version!

- Security: Tighten CSRF protections.  
  As a result, the Banphrase, Command, and Timer removal APIs have had their methods changed from GET to POST. (#1248)

## v1.51

Remember to bring your dependencies up to date with `./scripts/venvinstall.sh` when updating to this version!

- Minor: Added an action message moderation module. This lets you disallow or force the use of the `/me` command by users, or else they would receive a timeout or message deletion. (#1199)
- Minor: Add QueUp support (the new Dubtrack). (#1197, #1206)
- Minor: Exposed `sub_immunity` and `remove_accents` fields in the Banphrase API response. (#1186)
- Bugfix: Fix `or_broadcaster`/`or_streamer` returning only the first character of the broadcasters name instead of the full name. (#1189)

## v1.50

Remember to bring your dependencies up to date with `./scripts/venvinstall.sh` when updating to this version!

- Major: Math filters (`add`, `subtract`, `multiply`, and `divide`) are now able to read float values in addition to int values.
- Minor: Added support for the `delete` moderation action in the ASCII module. (#1174)
- Minor: Added an option to the `stream_update` module that allows moderators to change the title/game (without the level requirement). (#1165)
- Minor: Added a new module to print a chat/whsiper alert on cheer. (#1158)
- Minor: Added the filter `timedelta_days` which returns the amount of days between now and a `datetime` object. (#1173)
- Minor: Added the filter `ceil` which returns the smallest integer greater than or equal to the parameter. (#1168)
- Minor: Added the filter `floor` which returns the largest integer less than or equal to the parameter. (#1168)
- Minor: Added the variable `datetimefromisoformat` which allows commands to generate a full datetime object from a given string, which can then be further expanded on using filters. (#1169)
- Minor: Filter arguments now allow the period character `.` (#1171)
- Bugfix: Escape message content in command examples. (#1181)

## v1.49

Remember to bring your dependencies up to date with `./scripts/venvinstall.sh` when updating to this version!

- Major: `$(urlfetch)` now handles non-200 error codes differently by returning the body if the returned content type is plain text, or a generic "urlfetch error 404" if the content type was not plain text. (#1140)
- Minor: Added a VIP exemption option to the case checker module. (#1150)
- Minor: Added a VIP exemption option to the link checker module. (#1149)
- Minor: Added an option to only enable slots after a re/sub. (#1146)
- Minor: Added an option to allow ASCII characters while the streamer is on/offline. (#1145)
- Minor: Added an option to allow repetitive spam while the streamer is on/offline. (#1144)
- Minor: Added an option to allow mass pings while the streamer is on/offline. (#1129)
- Minor: Added an option to allow rouletting while the streamer is on/offline. (#1131)
- Minor: Added `subtract`, `multiply` & `divide` filters. (#1136)
- Minor: Added `$(datetime:<timezone>)` variable. This allows users to parse their own timezone's time and use the `strftime` filter. (#1132)
- Minor: Added `$(date:<timezone>)` variable. (#1125)
- Bugfix: Fix issue where we matched some normal messages as links, e.g. 1.40 or asd...xd (#1148)

## v1.48

Because the Game/Title setting API calls are now using the Helix calls, it's no longer possible to use the Bot token to update the game/title of a channel, instead the Streamer token **must** be used. In addition to this, the Streamer token needs a new permission `user:edit:broadcast`.  
In short: The Streamers must re-authenticate with the `/streamer_login` endpoint for `!setgame` and `!settitle` to work.

Remember to bring your dependencies up to date with `./scripts/venvinstall.sh` when updating to this version!

- Breaking: Replace Kraken Game/Title setting API calls with Helix ones. (#1001)
- Minor: Added user-specific cooldown to playsound module (#888, #1006)
- Minor: The permaban module will now ban immediately on command use (#1014)
- Minor: Bot now provides more helpful error message when `!clip` is used in a channel with clips disabled. (#1091)
- Minor: Added custom message options to the LastFM module. (#1090)
- Minor: Added customizable cooldowns to the LastFM module. (#1090)
- Minor: Added an online only option to the LastFM module. (#1090)
- Minor: Added option to select your referred gambling command. (#1067)
- Minor: The `sub_only` command option will now show in the `!debug command` command. (#1027)
- Minor: Added settings to change command name and cooldowns for showemote module. (#1007)
- Minor: Replace Kraken Game/Title/Stream/Video fetching API calls with Helix ones (#1001)
- Minor: Removed excess message in whisper for paid timeout module. (#993)
- Minor: Move the streamer image resizing to the css file. Also added a rounded border to it. (#992)
- Minor: Add \$(broadcaster) variable (#925, #1076)
- Minor: Duel winrate now takes `duels_won` into consideration if winrate is equal (#1079)
- Minor: Moved CLR-based modules to a sub-folder. (#1094)
- Bugfix: Fixed league rank module not working at all. (#990)
- Bugfix: Paid timeouts will now only timeout once. (#993)
- Bugfix: Fixed name of "get timed out" quest. (It just said "Quest" before) (#1003)
- Bugfix: Handle new format of P&SL lists (#988, #989, #994)
- Bugfix: Added proper error handling to P&SL module. (#991, #1005)

## v1.47

Remember to bring your dependencies up to date with `./scripts/venvinstall.sh` when updating to this version!

Remember you might need to delete the web cache to get some of the updates working: `sudo rm -rf static/.webassets-cache/ static/gen && sudo systemctl restart pajbot-web@*`

- Minor: Added VIP/Founder support. VIPs & Founders will now show in the !debug command, on the userpage on the website and on the API. The broadcaster badge will now also show on the user's webpage. If you experience any issues with the badges not showing on the webpage, typing `sudo rm -rf static/.webassets-cache/ static/gen && sudo systemctl restart pajbot-web@*` in the root folder of your pajbot installation will clear the webapp cache and restart your webapp. (#886)
- Minor: Added setting to disable the `!pnslrun`/`!runpnsl` command while stream is live (#978)
- Minor: Made ranks for user levels on the website consistent. (#968)
- Minor: Added a clip command module which allows users to clip the last 30 seconds of the stream. In order for this to function, the bot will need to be re-authed via the `/bot_login` process. (#950)
- Minor: Improved `!remindme` command - the bot will alert you of the correct syntax (if incorrect) (#953)
- Minor: Moved followage module to the basic-commands group (#954)
- Minor: User detail page for broadcaster now shows broadcaster badge instead of moderator badge (#943, #965)
- Minor: Badges display on the website have been updated to the redesigned style by Twitch. (#963)
- Bugfix: Bot no longer keeps announcing that rouletting has been enabled for X seconds after a mass sub gift (It will only be announced once). (#958, #959)
- Bugfix: Updated `pillow` dependency to mitigate possible vulnerability (#949)
- Bugfix: If you didn't specify a message alongside the `!remindme` command, the response was a bit awkwardly formatted. Added a nicer special case in case no message is specified. (#953)

## v1.46

- Minor: Added the ability to set a custom response to emote commands. (#940)
- Minor: The bot will now whisper you if your `!tweet` from the bot fails/is successful. (#942)
- Minor: Refactored the case checker module - this changes the default behaviour of the module by forcing usage of a max/percentage-based upper/lowercase setting as opposed to timing out ANY upper/lowercase characters in a sentence. If the max upper/lowercase setting is met, the user is immediately timed out. If not, the bot will check the total upper/lowercase characters in a sentence to ensure it is above the minimum; if so, it will timeout based on if the percentage of upper/lowercase characters is above the pre-defined percentage. Users are able to re-create the original behaviour by simply setting the max upper/lowercase setting to 0. (#941)
- Minor: Added a secondary optional message to send when the channel goes live (live alerts module) (#938)
- Minor: Added a new module to print a chat alert when a user announces they are new (#926)
- Minor: Added a live alerts module to notify chat when the streamer goes live (#924)
- Minor: Added a `streamer_display` variable to show the capitalized version of the broadcaster (#924)
- Minor: It is no longer necessary to restart the bot during installation process after completing the `/bot_login` process. (#929)
- Minor: Removed the dubtrack module (#916)
- Bugfix: Cooldown and level values are now used correctly in the emotes module. (#947)
- Bugfix: Bot now properly attempts to reconnect if getting the login token failed (e.g. no token or refresh failed). (#929)
- Bugfix: Validate playsound names during creation (#502, #934)
- Bugfix: Cleanly handle new response from Helix Subscriptions endpoint (#961, #962)

## v1.45

Remember to bring your dependencies up to date with `./scripts/venvinstall.sh` when updating to this version!

- Major: Added a new config option `whisper_output_mode`, allowing you to send whispers to the streamer's chat or to disable them altogether, to aid un-verified bots that may be unable to send whispers. View the example config for more info. (#878)
- Minor: Added an extra config option for _known_ bots (in addition to verified bots that were already supported). See example config for usage. (#878)
- Minor: Moved chat alerts into a sub-category. (#896)
- Minor: Added a new module to print a chat alert on raids. (#896)
- Minor: Added option to unban user from chat when the `!unpermaban` command is used (#739, #887)
- Minor: Added whisper timeout reasons to the emote limit module (#866)
- Minor: Added `timeout_end` field to User API Response and `!debug user` command output. (#875)
- Minor: Paid timeouts now stack with moderator's timeouts (and no longer override them). (#876)
- Minor: Added "My profile" link to website footer (#852)
- Minor: Added support for updating the game/title using the authorization of the streamer (via `/streamer_login`). Previously only the bot's authorization was used, and required the bot to be channel editor. (Note the bot/channel editor system is still used if the streamer token cannot be used.) (#877)
- Minor: Added `!slots` alias to `!slotmachine` command (#890)
- Minor: Added settings to individually disable `!subemotes`, `!bttvemotes` or `!ffzemotes` without having to disable all of them together. (#895)
- Minor: "Stats" tab is no longer highlighted while showing the user detail page. (#902, #906)
- Minor: Updated version of Google Analytics script + added documentation for `google_analytics` config option. (#907)
- Minor: Added settings to change and disable the "User was given points for (re)subbing" and "Rouletting is now allowed for X seconds" messages. (#897, #908)
- Minor: If a user clicks "Cancel" instead of "Authorize" during the Twitch login process, they will no longer see an error page, instead the user will be silently returned to where they came from. (#914)
- Bugfix: Fixed incorrect redirect after completing the `/bot_login` or `/streamer_login` process. (#869)
- Bugfix: Added retry logic for when opening connection fails. (#872)
- Bugfix: Updated `httplib` dependency to mitigate possible vulnerability (#884)
- Bugfix: Fixed `tweet_provider_port` config option not working correctly. (#900)
- Bugfix: Welcome message(s) are no longer sent to chat when the bot reconnects. (#904)
- Bugfix: Fixed typo on login error page. (#914)

## v1.44

- Minor: Updated code for login system to make it work with upcoming changes to the Twitch API. (#861)
- Minor: Added timeout reason customization to various moderation modules
- Minor: Added new module for simple emote spam moderation
- Minor: You can now allow users with level 420 to use the `!runpnsl` command (could only be set as low as 500 before). Default level requirement remains at 750. (#830)
- Minor: Enlarged emotes on the CLR are no longer blurry
- Minor: Remove the logs option from the user page (due to the termination of overrustlelogs)
- Minor: Added a setting to change the level required for the `!trivia start` and `!trivia stop` commands. (Default remains at 500, like before.) (#847)
- Minor: Updated semantic-ui css and js dependencies
- Minor: Login system is now protected against CSRF attacks (#861)
- Minor: Login process no longer asks users for the permission to read the email from their profile (we now only request public information). (#861)
- Bugfix: Fixed warnings in the admin playsounds page
- Bugfix: Fixed scrollbar appearing on CLR overlay (#832)
- Bugfix: The modules list no longer incorrectly shows as sorted on page load
- Bugfix: Fixed `last_active` field in the API showing the same value as `last_seen` (#853)

## v1.43

- Minor: Updated response of `!checkmod` command to reflect the regular moderators refresh feature introduced in v1.38.
- Minor: Added ban reason for `!permaban`
- Minor: You can now set the points cost for the `!$timeout`/`!untimeout`/`!unban`/`!$subon`/`!$suboff` commands as high as 1 million (was 30k/10k before).
- Minor: Fixed some minor grammar issues, also modified some module names and descriptions
- Minor: "Stream Update Commands" module is now configurable (custom trigger, custom level requirement)
- Minor: Added `slice` filter that can slice up a string. See https://docs.python.org/3/library/functions.html#slice
- Minor: Removed pleblist stuff. Namely: password/key generation and password/key checking. Also removed youtube config entry from the example config file.
- Bugfix: Fixed web process not starting if the venv was recently installed or updated. (#816)
- Bugfix: Fixed founders not counting as subscribers (#820)

## v1.42

- Minor: Add ability to run P&SL lists with !runpnsl command
- Minor: Implemented required changes for [upcoming changes to the Twitch API](https://discuss.dev.twitch.tv/t/requiring-oauth-for-helix-twitch-api-endpoints/23916).
- Minor: Renamed the chatter refresh module
- Bugfix: Fixed the "type emote" quest by ensuring all emote IDs are strings. (#768)
- Bugfix: Fixed a bug where sorting in the modules page didn't sometimes work.
- Bugfix: Fixed a bug where messages like `/me` or `/commercial` (without anything after them) could not be posted by the bot.

## v1.41

- Major: Add support for streaming tweets through [tweet-provider](https://github.com/pajbot/tweet-provider) instead of going directly through Twitter.

  This makes it possible to run many instances of pajbot1 with using only one Twitter app.

- Minor: Added emotes to the join/leave messages
- Minor: Added reasoning for the vanish module
- Minor: Added `bot_domain` variable
- Minor: Added more social media options (Discord, Patreon, Snapchat)
- Minor: Changed requests should now have the appropriate `User-Agent`.
- Minor: Added `title` filter that titlecases a message (turns "lol LOL" into "Lol Lol")
- Minor: Added `capitalize` filter that capitalizes a message (turns "lol LOL" into "Lol lol")
- Minor: Added `swapcase` filter that inverts case for all letters in a message (turns "lol LOL" into "LOL lol")
- Minor: Added `(urlfetch)` masking for the commands page. (Don't think your commands with url are private yet, this still needs work)
- Minor: Modified description of the `chatters_refresh` module
- Minor: Removed the old emote rendering code from the website.
- Minor: Fixed command examples of `forsen`
- Minor: Added streamer name to syslog identifier when running under systemd (`pajbot@streamer_name` instead of `python3`)
- Minor: Updated install-docs/readme.md further-steps
- Minor: Start removing unused pieces of pleblist (song request) system, starting with the login system
- Bugfix: Fixed duels not being cancelled
- Bugfix: Fixed duel stats not being applied to the right person (#717)
- Bugfix: Respect `timeout_length` setting in Link Checker module
- Bugfix: Fixed !subemotes command not working due to a deprecated Twitch API (#682)
- Bugfix: Fixed potential issues with users with recycled Twitch usernames (cases when two users in the database shared the same Twitch username).
- Bugfix: Links are now checked against whitelisted links in case the "Disallow links from X" settings are enabled
- Bugfix: Single-raffle winners are now properly announced if the "show on clr" option is disabled

## v1.40

- Bugfix: Fixed Twitter statuses showing with undecoded HTML entities (#645)
- Bugfix: Fixed users not being banned on sight if they were "banned on pajbot" (`!permaban` command/feature).
- Bugfix: Fixed linkchecker blacklist commands not working.
- Bugfix: Fixed linkchecker blacklisted links not timing users out.
- Bugfix: Fixed strictargs not cancelling message response if a filter was applied to it. (#677)

## v1.39

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

- Minor: Bot maintainer/host information can now be added to the config file and displayed on the `/contact`-page. See bottom of updated example config for an example.
- Minor: The bot now uses the BTTV v3 API, which should fix some cases where the bot considered more emotes to be enabled than were actually supposed to be enabled.
- Minor: Emote command (e.g. !bttvemotes) cooldowns and level can now be configured in the modules settings.
- Minor: Duels now automatically expire and get cancelled if they are not accepted within 5 minutes (Time amount can be configured as a module setting).
- Minor: The subscriber badge is now automatically downloaded on web application startup. Which version of the subscriber badge should be downloaded can be configured in config.ini under the `web` section using the `subscriber_badge_version` key. Setting the `subscriber_badge_version` key to `-1` disables the sub badge downloading, in case you want to use a custom subscriber badge (or an old one that you don't want to overwrite)
- Minor: Dates/Times on the website are now all shown in the user's time zone and formatted based on the viewer's locale. Note for the bot operator: You can remove the `timezone=` setting under `[main]`, since it's no longer needed.
- Minor: The regular refresh of the points_rank and num_lines_rank is now randomly jittered by ±30s to reduce CPU spikes when multiple instances are restarted at the same time
- Minor: Added setting to configure bypass level to "Link Checker" module.
- Minor: The points gain rate information at the top of the points page is now dynamically updated based upon your settings for the "Chatters Refresh" module.
- Minor: "dev" config flag is now respected in web, properly omitting any git information in its footer
- Minor: Fix table sorting in the modules page.
- Minor: The end message sent when a negative raffle ends now says "lost X points" correctly, instead of "won -X points".
- Minor: Removed last remnants of already defunct Pleblist StreamTip integration
- Minor: Website will now show moderator badge next to usernames if the user is a Twitch moderator.
- Minor: In preparation for a slimmer docker image, the bot will now also try to read git information from `PB1_BRANCH`, `PB1_COMMIT` and `PB1_COMMIT_COUNT` environment variables.
- Bugfix: Added explicit VACUUM of user_rank relation after refresh to ensure the database server does not run out of disk space, even if you have a lot of bots (with a lot of users in the database) running on the same server.
- Bugfix: Fixed an exception and the message not being handled whenever a message contained an emote modified via the "Channel Points" Twitch feature.
- Bugfix: Fixed two more cases of long-running transactions not being closed, which in turn could cause the database server to run out of disk space (#648)
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

- Breaking: pajbot now uses PostgreSQL instead of MySQL as its supported database engine. It is not possible to continue to use MySQL.  
  To migrate your existing database(s):

  - Install new requirements from apt: `sudo apt-get install libpq-dev`
  - Bring your installed dependencies up-to-date with `./scripts/venvinstall.sh`
  - Install and start PostgreSQL, if you have not done so already
  - Create the pajbot PostgreSQL user, a database and optionally a schema for the bot to use. (see the updated SQL section of [the install docs](./install-docs/debian10/install-debian10.txt))
  - Edit `./scripts/migrate-mysql-to-postgresql.py` with a connection string for the old MySQL database, and your new PostgreSQL database.
  - Stop pajbot: `sudo systemctl stop pajbot@streamername pajbot-web@streamername`
  - Backup your data: `sudo mysqldump --single-transaction --result-file=mysql-dump-streamername.sql pajbot_streamername`
  - Activate the python virtualenv: `source venv/bin/activate`
  - Run `./scripts/migrate-mysql-to-postgresql` to move the data
  - Update the `sql` connection string in your bot config (see the updated [example config](./configs/example.ini) for examples)
  - Start pajbot again: `sudo systemctl start pajbot@streamername pajbot-web@streamername`
  - Drop the old MySQL database: `sudo mysql -e "DROP DATABASE pajbot_streamername"`

  The procedure for new bot installations is described in the [install documentation](./install-docs).

- Breaking: If you were using the [chatters microservice](https://github.com/pajbot/chatters), you must update it to be able to use it after the PostgreSQL update.
- Breaking (if you rely on it in an automatic way somehow): `venvinstall.sh` has been moved from `./install` into `./scripts`, where all other shell scripts also reside.
- Major: Official support for python 3.5 has been removed. Only python 3.6 or above will be supported from this release on.
- Feature: Added `!namechange <oldusername> <newusername>` command for migrating users that changed their twitch name. (Level 2000 only). `./scripts/transfer-{all,sql,redis}` scripts have been removed.
- Minor: Removed `!reload` command since it did nothing.
- Minor: Modules can now be configured to only allow users above a certain level to configure them. #108
- Minor: Removed "Personal Uptime" module.
- Bugfix: A series of bugs (including the `!laststream` command sometimes not working) caused by a mismatch of datetime-aware and datetime-naive objects.
- Bugfix: If redis is busy loading data, the bot no longer exists, and waits for completion instead.
- Bugfix: `/api/v1/user/:username` no longer fetches `nl_rank` from redis twice.
- Bugfix: If no git data is available, web interface will no longer show `Last commit:`, instead last commit will be omitted altogether
- Bugfix: Fixed a series of bugs (including the `!laststream` command sometimes not working) caused by a mismatch of datetime-aware and datetime-naive objects.
- Bugfix: Commands are now only checked against banphrases, ascii and massping checks if you enabled `run_through_banphrases` (e.g. via `--checkmsg`) (#478)
- Bugfix: Subscribers refresh now correctly sets the `active_subs` KVI value.
- Bugfix: You can no longer ignore yourself
- Bugfix: You can now use the same phrases (1k, "all", etc.) with the `!givepoints` command.
- Documentation Bugfix: `$(urlfetch)` returns the response body, not request body

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

- Breaking: In your `config.ini`, rename `[webtwitchapi]` to `[twitchapi]` and delete the old `[twitchapi]` config file entry. See [the example config](https://github.com/pajbot/pajbot/blob/677651d416fa60c80ef939df8666bf554237ae0d/install-docs/debian10/kkonatestbroadcaster.ini#L62) for example values.
- Breaking: a `redirect_uri` is now always required under `[twitchapi]` in your `config.ini`.
- Breaking: If you want to continue fetching subscribers, you will need to have the streamer log in once with `/streamer_login`. Then the bot will automatically start fetching a list of subscribers regularly.
- Major: To be able to use game and title updates with `!settitle` and `!setgame`, re-authenticate the bot with `/bot_login`. Then ask the streamer to add the bot as a channel editor.
- Major: Dependency on `twitch-api-v3-proxy` has been removed. You can uninstall that service if you were running it. (The bot now uses the new Twitch v5 and Helix APIs)
- Feature: Dubtrack module can now show requester
- Feature: Dubtrack module can automatically post a message when a new song starts playing
- Bugfix: Fix a recurring error that could appear when fetching the stream live/offline status.
- Bugfix: Make subscriber fetch routine more accurate (will now fetch the correct/accurate number of subscribers)
- Bugfix: `!settitle` and `!setgame` are now packaged as a module, you no longer need to add these commands as `funccommand`s.
- Bugfix: Updated link checker module to use the latest version of the safe browsing API.

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
- The HSbet reminders now print stats about how many points are bet on win and how many points are bet on lose.
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
