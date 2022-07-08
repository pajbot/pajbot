# Command Arguments

## Banphrases

`--length`/`--time`/`--duration` - sets the timeout length of for the phrase (in seconds). Default = 600 seconds  
`--notify`/`--no-notify` - choose whether to notify the user of the banned phrase. Default = notify  
`--perma`/`--permanent`/`--no-perma`/`--no-permanent` - choose whether to permanently ban the user or not. Default = no-perma  
`--casesensitive`/`--no-casesensitive` - choose if the banphrase should be case sensitive or not. Default = no-casesensitive  
`--warning`/`--no-warning` - choose if the banphrase should first warn the user for a shorter timeout period. Requires the warnings module to be enabled. Default = warning  
`--subimmunity`/`--no-subimmunity` - choose if subscribers should be exempt from the banphrase. Default = no-subimmunity  
`--removeaccents`/`--no-removeaccents` - choose if the bot should strip the accents before checking for the phrase. Default = no-removeaccents  
`--operator contains/startswith/endswith/exact/regex` - choose the operator that should be used for banphrase checking. Default = contains  
`--name` - name the banphrase. Default = No name

## Commands

### Setting the reply type

The default reply type is `say`

- `--say` - sends a regular chat message with the command response
- `--whisper` - whispers the response of the command to the source user
- `--reply` - context-dependant reply based on where the command is used
- `--announce` - uses the /announce feature to highlight the response in the chat

To make your command a `.me` command, start the response with `.me` or `/me`

### Miscellaneous

`--cd` - sets the global cooldown of the command (in seconds). Default = 5 seconds  
`--usercd` - sets the per-user cooldown of the command (in seconds). Default = 15 seconds  
`--level` - sets the required level to use the command. If the mod-only argument is used, the mod must also meet the level specified here in order to use the command. Default = 100  
`--cost` - sets the points cost of the command. Default = 0  
`--tokens-cost` - sets the tokens cost of the command. Default = 0  
`--modonly`/`--no-modonly` - allows only moderators to use the command. If a level is also set for a command, but the mod does not meet the level requirement; they will not be able to use the command. Default = no-modonly  
`--subonly`/`--no-subonly` - allows only subscribers to use the command. Default = no-subonly  
`--checkmsg`/`--no-checkmsg` - choose whether to check the message against the banphrase api. If enabled, the bot will not post the message if it matches a phrase. Default = no-checkmsg<br/>
`--disable`/`--enable` - makes the command either enabled or disabled. Default = enabled
