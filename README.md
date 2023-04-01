# pajbot ![Python 4HEad](https://github.com/pajbot/pajbot/workflows/Python%204HEad/badge.svg)

pajbot is a twitch chat bot created by [pajlada](http://twitch.tv/pajlada).  
[Website](https://pajbot.com)

Note: pajbot is in **maintenance mode**.
This means we focus on keeping the project alive by not allowing major overhauls of any pajbot system or any major features.
Fixing bugs, updating dependencies and ensuring that code interacting with external APIs still function will be our main goal.
Feature requests will not be accepted unless someone is willing to own the feature, and even then some features that change too much of the architecture won't be allowed.
Current minimal supported Python version is **3.9**.

## Python versioning

We use [pyenv](https://github.com/pyenv/pyenv) to manage Python versions. Get familiar with this tool.  
Quick install of pyenv on Linux systems: `curl https://pyenv.run | bash`

If you don't want to use pyenv's version of Python in any of our scripts, set the `SKIP_PYENV` environment variable to `1`.

## Quick install

1. Install library requirements by typing `./scripts/venvinstall.sh` in the root folder
2. Copy `./configs/example.ini` to `./config.ini` and change the relevant lines in the file.
3. Run the bot! `./main.py`

## Detailed install

You can find a detailed installation guide for **pajbot** in the [`install-docs` directory](./install-docs) of this repository.

## Run-time options

Some values can be set to apply to your bot without modifying the config file, these are mostly for out-of-bot things.  
They are configured using environment variables. The following options are available:

- `PB1_LOG_HIDE_TIMESTAMPS`  
   If this option is set to `1`, all log entries will be printed without a timestamp prefix.
