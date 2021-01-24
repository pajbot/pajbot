# pajbot1 Variables

Args: `$(1)`, `$(2)`, etc -> return the input arguments as-is (first argument has the index 1). Does not accept transforms like `$(1|upper)`

```
$(user;1:key|strftime(%Y)|upper)
  ^ path
       ^ argument (number)
         ^ key
             ^ filter
                      ^ filter arguments
                          ^ filter
```

Examples for valid substitutions: `$(user;1:points)` - get the user with the login name in argument 1 (after the command trigger), and get their points\
`$(args:0-1|urlencode)` - urlencode the first parameter

## Available filters:

#### Uncategorized

`strftime` - allows you to format raw time strings - Help: https://strftime.org  
`urlencode` - URL encodes the value. see https://en.wikipedia.org/wiki/Percent-encoding  
`join` - join characters together using `,`  
`number_format` - format numbers using `,`  
`or_else` - if the previous filter failed, return what is specified  
`or_broadcaster`/`or_streamer` - if the previous filter failed, return the streamer's name  
`slice` - slice the string like a python3 string - see https://www.digitalocean.com/community/tutorials/how-to-index-and-slice-strings-in-python-3 (NOTE: We don't support what they call 'stride')

#### Time Since

`time_since_minutes` - outputs the time since a certain input time in minutes  
`time_since` - outputs the time since a certain input time  
`time_since_dt` - outputs the date since a certain input date

#### Letter Case

`lower` - converts the output of the variable to lowercase  
`upper` - converts the output of the variable to uppercase  
`title` - converts the first letter in each word to upper case  
`capitalize` - converts the first letter of the first word to upper case  
`swapcase` - swaps all upper case to lower case and vice versa

#### Math

`add` - tries to convert the variable result into an integer, then adds it to the defined filter argument - e.g `$(kvi:active_subs|add(5))` would add 5 to the amount of active subs you have.  
`subtract` - tries to convert the variable result into an integer, then subtracts the filter argument from it - e.g. `$(kvi:active_subs|subtract(5))` would subtract 5 from the amount of subs you have.  
`multiply` - tries to convert the variable result into an integer, then multiplies it by the filter argument - e.g. `$(kvi:active_subs|multiply(5))` would multiply the amount of subs you have by 5.  
`divide` - tries to convert the variable result into an integer, then divides it into the defined filter argument - e.g. `$(kvi:active_subs|divide(5))` would divide the amount of subs you have into 5.

# Special Substitutions

`$(urlfetch <url>)` - HTTP GET the given URL, and returns the body of the response.

Some useful "customapi" resources are:

All resources from https://customapi.aidenwallis.co.uk/  
All resources from https://docs.decapi.me/#toc

Customapis are generally a very powerful way of allowing pajbot to do more things without expanding the python code itself.

!rq command with justlog: `$(usersource;1:name)`: `$(urlfetch https://api.gempir.com/channel/pajlada/userid/$(usersource;1:id)/random)`

## Available paths:

### kvi - Key Value Integer

`$(kvi:active_subs)` - int - Number of subscribers to the broadcaster.

### tb - Info about the bot instance

#### Data from `extra`:

`$(tb:trigger)` - String - Command trigger (e.g. "logs" for "!logs")\
`$(tb:user)` - String - Sender login name\
`$(tb:emote_instances)` - List of EmoteInstance objects - useful for debugging. Outputs something like this: [[twitch] Kappa @ 11-16, [twitch] Keepo @ 17-22, [twitch] Keepo @ 23-28]\
`$(tb:emote_counts)` - List of EmoteInstanceCount objects - useful for debugging. Outputs something like this: {'Kappa': [twitch] Kappa @ [12-17], 'Keepo': [twitch] Keepo @ [18-23, 24-29]}\
`$(tb:source)` - pajbot.models.user.UserCombined - (Command sender)\
 -> see user: for all fields on user objects\
`$(tb:command)` - pajbot.models.command.Command\
`$(tb:message)` - String - message after the command

#### Data from `self.data`:

`$(tb:version_brief)` - String - '1.30'\
`$(tb:bot_name)` - String - 'BotFactory'\
`$(tb:broadcaster)` - String - 'infinitegachi'\
`$(tb:version)` - String - '1.30 DEV (master, 8ceb7235, commit 1629)'\
`$(tb:bot_domain)` - String - Returns the domain specified in the config file\
`$(tb:streamer_display)` - String - Returns the capitalized streamer name specified in the config file

#### Data from `self.data_cb`:

`$(tb:bot_uptime)` - refers to pajbot.bot.Bot.c_uptime (returns String) - '4 minutes and 24.6 seconds'\
`$(tb:current_time)` - refers to pajbot.bot.Bot.c_current_time (returns datetime.datetime object) - '2019-01-06 16:27:38.696840'\
 -- since this returns an object you can format it with strftime\
 e.g. `$(tb:current_time|strftime(%A %Y-%m-%d %H:%M:%S))`\
`$(tb:stream_status)` - refers to pajbot.bot.Bot.c_stream_status (returns String) - 'offline'/'online'\
`$(tb:status_length)` - refers to pajbot.bot.Bot.c_status_length (returns String) - '4 hours and 12 minutes'

#### Other

`$(tb:molly_age_in_years)` - String - '0.1971333233018455' (age of pajlada's puppy molly in years)\
`$(time:<timezone>)` - String - '18:47' (timezone is e.g. 'Europe/Berlin')\
`$(date:<timezone>)` - String - '2021-01-12' (timezone is e.g. 'Europe/Berlin')\
`$(datetime:<timezone>)` - refers to pajbot.bot.Bot.get_datetime_value (returns datetime.datetime object) - '2019-01-06 16:27:38.696840'\
 -- since this returns an object you can format it with strftime\
 e.g. `$(datetime:Europe/Berlin|strftime(%A %Y-%m-%d %H:%M:%S))`

#### e - emotes

`$(epm:<emote>)` - String - "68" (how often the emote was used in the last 60 seconds)\
`$(ecount:<emote>)` - String - "10482" (how often the emote was used, over all time)\
`$(epmrecord:<emote>)` - String - "103232" (highest ever epm value)

#### lasttweet - last tweet

`$(lasttweet:<TWITTERUSER>)` - String - "\<tweet text\> (5h44m ago)". You can use arguments to allow users to choose their own twitter user to fetch. E.g. `$(lasttweet;1)` would fetch the twitter user in the first argument.

#### Source

`$(source:<thing>)` - pajbot.models.user.User - same as tb:source\
`$(source:id)` - String - Twitch User ID\
`$(source:login)` - String - Twitch user login name\
`$(source:name)` - String - Twitch user display name\
`$(source:level)` - int - 100 (pajbot level)\
`$(source:points)` - int - 0 (pajbot points)\
`$(source:subscriber)` - boolean - True if channel subscriber, False otherwise\
`$(source:time_in_chat_online)` - datetime.timedelta\
`$(source:time_in_chat_offline)` - datetime.timedelta\
`$(source:num_lines)` - int\
`$(source:last_seen)` - datetime.datetime\
`$(source:last_active)` - datetime.datetime\
`$(source:ignored)` - boolean - True if the bot ignores commands by this user\
`$(source:banned)` - boolean - True if permabanned on the bot\
`$(source:tokens)` - int\
`$(source:moderator)` - boolean\
`$(source:timed_out)` - boolean - True if currently on paid timeout, False otherwise\
`$(source:timeout_end)` - datetime.datetime? - End of paid timeout, if exists

#### user

`$(user;argId:<attribute>)` - pajbot.models.user.UserCombined - (find user with the name from the argument and get user attribute \<attribute\>)

#### usersource

`$(usersource;argId:<attribute>)` - pajbot.models.user.UserCombined - (find user with the name from the argument OR if that returns nothing get the user object for the sender, and get user attribute \<attribute\>)

#### curdeck

`$(curdeck:id)` - int - '237'\
`$(curdeck:name)` - String - 'Freeze Mage'\
`$(curdeck:link)` - String - 'Freeze Mage'\
`$(curdeck:deck_class)` - String - 'Freeze Mage'\
`$(curdeck:first_used)` - datetime.datetime\
`$(curdeck:last_used)` - datetime.datetime\
`$(curdeck:times_used)` - int\
`$(curdeck:last_used_ago)` - String - '8 months and 25 days'\
`$(curdeck:first_used_ago)` - String - '8 months and 25 days'

#### stream

`$(stream:offline)` - bool\
`$(stream:online)` - bool\
`$(stream:num_viewers)` - int\
`$(stream:game)` - String\
`$(stream:title)` - String

`$(current_stream:id)` - int\
`$(current_stream:title)` - string\
`$(current_stream:stream_start)` - datetime.datetime\
`$(current_stream:stream_end)` - datetime.datetime\
`$(current_stream:ended)` - bool - if that stream has ended (False)\
`$(current_stream:uptime)` - datetime.timedelta - how long the stream is live

`$(last_stream:id)` - int\
`$(last_stream:title)` - string\
`$(last_stream:stream_start)` - datetime.datetime\
`$(last_stream:stream_end)` - datetime.datetime\
`$(last_stream:ended)` - bool - if that stream has ended (True)\
`$(last_stream:uptime)` - datetime.timedelta - how long the stream was live

#### current_song

(only works when online!)\
`$(current_song:id - int)`\
`$(current_song:stream_id)` - int\
`$(current_song:user_id)` - int\
`$(current_song:youtube_id)` - String\
`$(current_song:link)` - String - 'youtu.be/\<id\>'\
`$(current_song:date_added)` - datetime.datetime\
`$(current_song:date_played)` - datetime.datetime\
`$(current_song:skip_after)` - int\
`$(current_song:song_info)` - pajbot.models.pleblist.PleblistSongInfo\
 -> pleblist_song_youtube_id - String\
 -> title - String\
 -> duration - int\
 -> default_thumbnail - String\
Use these sub-variables like this: `$(current_song:song_info.title)`

#### args

Note: argument IDs are 0-based! `$(args:2-5)` - String - (joins args 2 (inclusive) through 5 (exclusive) together, e.g. '!argstest 1 2 3 4 5 6 7 8' -> '3 4 5')\
`$(args:3)` - String - (joins args 3 and all args until the end together, e.g. '!argstest 1 2 3 4 5 6 7 8' -> '4 5 6 7 8')

#### strictargs

Same as args, but if this substitution would return an empty string, the command is not executed.

#### command

Data about this command\
`$(command:command_id)` - int\
`$(command:num_uses)` - int\
`$(command:added_by)` - int - pajbot user ID of the user that added that command.\
`$(command:edited_by)` - int - pajbot user ID of the user that edited that command last.\
`$(command:last_date_used)` - datetime.datetime

#### broadcaster

`$(broadcaster:<attribute>)` - pajbot.models.user.UserBasics\
Valid attributes are:

- `id` for the broadcaster's Twitch ID
- `login` for the broadcaster's Twitch Login Name
- `name` for the broadcaster's Twitch Display Name
