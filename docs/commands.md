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
