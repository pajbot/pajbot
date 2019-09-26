# Changelog

## Unversioned

Remember to bring your dependencies up to date with
`pip install -r requirements.txt` when updating to this version!

- Breaking: pajbot now uses PostgreSQL instead of MySQL as its supported
  database engine. It is not possible to continue to use MySQL.  
  To migrate your existing database(s):

  - Install new requirements from apt: `sudo apt-get install libpq-dev`
  - Bring your installed dependencies up-to-date with `pip install -r requirements.txt`
  - Install and start PostgreSQL, if you have not done so already
  - Create the pajbot PostgreSQL user, a database and optionally a schema for
    the bot to use. (see the updated SQL section of
    [the install docs](./install-docs/debian9/install-debian9.txt))
  - Edit `./scripts/migrate-mysql-to-postgresql.py` with a connection string for
    the old MySQL database, and your new PostgreSQL database.
  - Stop pajbot:
    `sudo systemctl stop pajbot@streamername pajbot-web@streamername`
  - Backup your data:
    `sudo mysqldump --single-transaction --result-file=mysql-dump-streamername.sql pajbot_streamername`
  - Activate the python virtualenv: `source venv/bin/activate`
  - Run `./scripts/migrate-mysql-to-postgresql` to move the data
  - Update the `sql` connection string in your bot config (see the updated
    [example config](./install-docs/debian9/kkonatestbroadcaster.ini) for
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
  [the example config](https://github.com/pajbot/pajbot/blob/677651d416fa60c80ef939df8666bf554237ae0d/install-docs/debian9/kkonatestbroadcaster.ini#L62)
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

Changelogs were not maintained for older pajbot versions.
