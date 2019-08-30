# Changelog

<!-- reformat this file with `npx prettier --prose-wrap=always --write CHANGELOG.md` -->

## Unreleased

Remember to bring your dependencies up to date with
`pip install -r requirements.txt` when updating to this version!

- Breaking: pajbot now uses PostgreSQL instead of MySQL as its preferred
  database engine. To migrate your existing databases, see
  `./scripts/migrate-mysql-to-postgresql` and the updated example config/install
  instructions for how to create databases, users and schemas, and for the new
  DB URL schema.
- Breaking (if you rely on it in an automatic way somehow): `venvinstall.sh` has
  been moved into `./scripts`, where all other shell scripts also reside.
- Feature: Added `!namechange <oldusername> <newusername>` command for migrating
  users that changed their twitch name. (Level 2000 only)
- Bugfix: Fixed a series of bugs (including the `!laststream` command sometimes
  not working) caused by a mismatch of datetime-aware and datetime-naive
  objects.

<!--
- Internal: New (stupider) migrations system that directly uses SQL, and can additionally
  also migrate redis and other resources.
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
