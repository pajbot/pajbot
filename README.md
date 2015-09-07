# tyggbot

tyggbot is a twitch chat bot created by [pajlada](http://twitch.tv/pajlada).  
Examples of twitch channels where the bot is run:

| Bot name  | Twitch channel | Maintainer |
| ---------- | ------ | ----- |
| Tyggbot | [Tyggbar](http://twitch.tv/tyggbar) | [pajlada](http://twitch.tv/pajlada) |
| Snusbot | [Forsen](http://twitch.tv/forsenlol) | [pajlada](http://twitch.tv/pajlada) |
| botnextdoor | [NymN_HS](http://twitch.tv/nymn_hs) | [pajlada](http://twitch.tv/pajlada) |
| Annies_Bot | [AnnieFuchsia](http://twitch.tv/anniefuchsia) | [GiggleArrows](http://twitch.tv/gigglearrows) |
| cougarbot | [TaruliHS](http://twitch.tv/tarulihs) | [pajlada](http://twitch.tv/pajlada) |
| potatisbot | [RosenMVP](http://twitch.tv/rosenmvp) | [pajlada](http://twitch.tv/pajlada) |
| pajbot | [pajlada](http://twitch.tv/pajlada) | [pajlada](http://twitch.tv/pajlada) |
| lanbot144 | [Landon144](http://twitch.tv/landon144) | [pajlada](http://twitch.tv/pajlada) |
| Snookibot | [SnookiPoof](http://twitch.tv/snookipoof) | [Dorsens](http://twitch.tv/dorsens) |

TODO: Continue working on the installation instructions.

## Quick install

1. Install library requirements by typing `pip install -r pip-requirements.txt` in the root folder
2. Copy `install/config.example.ini` to `./config.ini` and change the relevant lines in the file.
3. Run the bot! `./main.py`

## Detailed install

The guide below will set up the bot to run as a [PM2](https://github.com/Unitech/pm2) service.

### Requirements
MySQL 5.6
Python 3 (Tested with 3.4)
PM2

### Install required dependencies
1. Install and set up MySQL 5.6 on your server. For Ubuntu 14.04, this you would type this: `sudo apt-get install mysql-server-5.6`.
2. Install PM2

### Set up a MySQL user
1. Open up a MySQL CLI logged in as root.
2. Type in the following commands:


### Set up the bot
1. Create a config file according to the specifications in [wiki](https://github.com/pajlada/tyggbot/wiki/Config-File) and save it somewhere in the root code folder. (TODO: configs should be able to be located anywhere...)
2. Start the bot using PM2: `pm2 start main.py --name="NAME_OF_BOT" --output="/path/to/output.log" --error="/path/to/error.out" --merge-logs -- --config path/to//config.ini`

## Disclaimer

The code is most likely messy and ugly, this is my first "full scale" python project.
