# tyggbot

tyggbot is a twitch chat bot created by [pajlada](http://twitch.tv/pajlada).  
Examples of twitch channels where the bot is run:

| Bot name  | Twitch channel | Maintainer |
| ---------- | ------ | ----- |
| Tyggbot | [Tyggbar](http://twitch.tv/tyggbar) | [pajlada](http://twitch.tv/pajlada) |
| Snusbot | [Forsen](http://twitch.tv/forsenlol) | [pajlada](http://twitch.tv/pajlada) |
| botnextdoor | [NymN_HS](http://twitch.tv/nymn_hs) | [pajlada](http://twitch.tv/pajlada) |
| Annies_Bot | [AnnieFuchsia](http://twitch.tv/anniefuchsia) | [GiggleArrows](http://twitch.tv/gigglearrows) |
| pajbot | [pajlada](http://twitch.tv/pajlada) | [pajlada](http://twitch.tv/pajlada) |
| lanbot144 | [Landon144](http://twitch.tv/landon144) | [pajlada](http://twitch.tv/pajlada) |
| Snookibot | [SnookiPoof](http://twitch.tv/snookipoof) | [Dorsens](http://twitch.tv/dorsens) |
| LinneasBot | [linneafly](http://twitch.tv/linneafly) | [GiggleArrows](http://twitch.tv/gigglearrows) |
| wowsobot | [imaqtpie](http://twitch.tv/imaqtpie) | [pajlada](http://twitch.tv/pajlada) |
| niconicobot | [eloise_ailv](http://twitch.tv/eloise_ailv) | [pajlada](http://twitch.tv/pajlada) |

TODO: Continue working on the installation instructions.

## Quick install

1. Install library requirements by typing `pip install -r pip-requirements.txt` in the root folder
2. Copy `install/config.example.ini` to `./config.ini` and change the relevant lines in the file.
3. Run the bot! `./main.py`

## Detailed install

The guide below will make sure the bot runs, and optionally how to run it as a [PM2](https://github.com/Unitech/pm2) service. The instructions below are tested on Ubuntu Server 14.0.4

### Requirements
 * MySQL 5+ (Tested with 5.6)
 * Python 3 (Tested with 3.4)
 * PM2 (optional)

### Install required dependencies
1. Install MySQL: `sudo apt-get install mysql-server`
2. In the bot root folder:<br/>`pip3 install -r pip-requirements.txt --user`<br/>If `pip3` is not installed, install it by typing `sudo apt-get install python3-pip`

### Set up a MySQL user
1. Open up the MySQL Terminal as root by typing<br/>`mysql -u root -p`
2. In the MySQL terminal, create a database for the bot:<br/>`CREATE DATABASE tyggbot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;`
3. Again in the MySQL terminal, create our user and grant it all privileges on the newly created database:<br/>`GRANT ALL PRIVILEGES ON tyggbot.* TO 'tyggbot'@'localhost' IDENTIFIED BY 'password';`


### Set up the bot
1. Create a config file according to the specifications in [wiki](https://github.com/pajlada/tyggbot/wiki/Config-File) and save it somewhere.
2. Start the bot by typing `./main.py` in the root folder.

### Run the bot as a PM2 service (optional)
1. Install PM2 `npm install -g pm2`
2. Create a PM2 service that runs the bot `pm2 start main.py --name="NAME_OF_BOT" --output="/path/to/output.log" --error="/path/to/error.out" --merge-logs -- --config /path/to/config.ini`
