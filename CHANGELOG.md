# Changelog

## Unreleased

- Minor: Removed `!reload` command since it did nothing.
- Bugfix: If redis is busy loading data, the bot no longer exists, and waits for
  completion instead.
- Bugfix: `/api/v1/user/:username` no longer fetches `nl_rank` from redis twice.
- Bugfix: If no git data is available, web interface will no longer show
  `Last commit:`, instead last commit will be omitted altogether
- Documentation Bugfix: `$(urlfetch)` returns the response body, not request
  body

<!--
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
