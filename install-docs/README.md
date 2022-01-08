# Installation instructions

Welcome to the installation instructions for pajbot!

Below is the index for a full list of installation instructions for pajbot.

These installation instructions will install pajbot in a way that allows you to run pajbot for multiple streamers at once without too much duplication. For this reason, these installation instructions are split into two big parts: Installation of pajbot, and creating a pajbot instance for a single channel (which you can repeat as needed, should you want to run pajbot in multiple channels, for different streamers for example).

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->

**Table of Contents** _generated with [DocToc](https://github.com/thlorenz/doctoc)_

- [Service installation](#service-installation)
  - [Install system dependencies](#install-system-dependencies)
  - [Set up a system user](#set-up-a-system-user)
  - [Install pajbot](#install-pajbot)
  - [Install and set up the database server](#install-and-set-up-the-database-server)
  - [Install Redis](#install-redis)
  - [Install nginx](#install-nginx)
  - [Install system services](#install-system-services)
- [Single bot setup](#single-bot-setup)
  - [Create an application with Twitch](#create-an-application-with-twitch)
  - [Create a database schema](#create-a-database-schema)
  - [Create a configuration file](#create-a-configuration-file)
  - [Set up the website with nginx](#set-up-the-website-with-nginx)
  - [Enable and start the service](#enable-and-start-the-service)
  - [Authenticate the bot](#authenticate-the-bot)
  - [Further steps](#further-steps)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

# Service installation

Please note we currently only document how to run pajbot on GNU/Linux systems. The following instructions should work without any changes on Debian and Ubuntu. If you are running another distribution of GNU/Linux, you might have to make some changes to the commands, file locations, etc. below.

## Install system dependencies

Pajbot is written in python, so we need to install some basic python packages:

```bash
sudo apt update
sudo apt install python3 python3-dev python3-pip python3-venv
```

Now, double-check that you have Python 3.8 or newer installed:

```bash
python3 --version
```

We also need the following libraries and build tools:

```bash
sudo apt install libssl-dev libpq-dev build-essential git
```

## Set up a system user

For security reasons, you shouldn't run pajbot as the `root` user on your server. You can create a low-privilege "system" user for pajbot like this:

```bash
sudo adduser --system --group pajbot --home /opt/pajbot
```

## Install pajbot

Download the latest stable version of pajbot:

```bash
sudo -u pajbot git clone https://github.com/pajbot/pajbot.git /opt/pajbot --branch stable
```

Install pajbot's dependencies like this:

```bash
cd /opt/pajbot
sudo -H -u pajbot ./scripts/venvinstall.sh
```

## Install and set up the database server

pajbot uses PostgreSQL as its database server. If you don't already have PostgreSQL running on your server, you can install it with:

```bash
sudo apt install postgresql
```

Now that you have PostgreSQL installed, we will create a user to allow pajbot to use the PostgreSQL database server:

```bash
sudo -u postgres createuser pajbot
```

> Note: We have not set a password for pajbot, and this is intentional. Because we created a system user with the name `pajbot` earlier, applications running under the `pajbot` system user will be able to log into the database server as the `pajbot` database user automatically, without having to enter a password.
>
> We have run `createuser` as `postgres` for the same reason: `postgres` is a pre-defined PostgreSQL database superuser, and by using `sudo`, we are executing `createuser pajbot` as the `postgres` system (and database) user.
>
> This is a default setting present on Debian-like systems, and is defined via the configuration file [`pg_hba.conf`](https://www.postgresql.org/docs/current/auth-pg-hba-conf.html).

We will now create a database named `pajbot`, owned by the `pajbot` database user:

```bash
sudo -u postgres createdb --owner=pajbot pajbot
```

## Install Redis

Pajbot also needs an instance of [Redis](https://redis.io/) to run. The redis database server does not need any manual setup - all you have to do is install redis:

```bash
sudo apt install redis-server
```

The redis server is automatically started after installation. You can verify your installation works like this:

```bash
redis-cli PING
```

You should get `PONG` as the response output. That means your redis server is working fine.

## Install nginx

Nginx is a reverse proxy - it accepts all incoming HTTP requests to your server, and forwards the request to the correct backend service. It also applies encryption for HTTPS, can set headers, rewrite URLs, and so on.

All you need to do for this step is to install nginx:

```bash
sudo apt install nginx
```

We will configure nginx later.

> Note: You can find a basic nginx configuration setup including HTTP -> HTTPS redirect, recommended SSL configuration parameters, etc. [over here](./full-nginx-setup/README.md). If you don't already have a basic nginx setup, we strongly recommend you follow the linked guideline now.

## Install system services

We recommend you run pajbot with the help of systemd. Systemd will take care of:

- starting and stopping pajbot,
- capturing and storing the output of the service as logs,
- starting pajbot automatically on system startup (and starting it in the correct order, after other services it needs),
- restarting pajbot on failure,
- and running multiple instances if you run pajbot for multiple streamers

To start using systemd for pajbot, install the pre-packaged unit files like this:

```bash
sudo cp /opt/pajbot/install-docs/*.service /etc/systemd/system/
```

Then tell systemd to reload changes:

```bash
sudo systemctl daemon-reload
```

# Single bot setup

Now that you have the basics installed, we need to tell pajbot to (and how to) run in a certain channel. Pajbot running in a single channel, and with its website for that channel, is called an **instance** of pajbot from now on.

## Create an application with Twitch

The first thing you need to do is to create an application for the bot instance. Registering an application gives you three important bits of data the bot needs to be able to access the Twitch API and allow users to log in to the website using their Twitch account: A client ID, The client secret, and the authentication redirect URI.

To create an application with Twitch, visit https://dev.twitch.tv/console/apps/create.

- Under _Name_, enter the name you want users to see when they log into the website and have to confirm they want to grant you access to their account.
- Under _OAuth Redirect URL_, enter the full URL users should be redirected to after they complete the log in procedure with Twitch. This should be `https://pleb-domain.com/login/authorized` (adjust domain name of course).
- Under _Category_, you should pick _Chat Bot_, as it is the most appropriate option for pajbot.

After you click "Create", you are given access to the **Client ID**. After clicking **New Secret**, you can also access your **Client Secret**. You will need these values in the next step - when you create the configuration file for your instance.

## Create a database schema

Each instance's data lives in the same database (`pajbot`, we created this earlier), but we separate the data by putting each instance into its own **schema**. To create a new schema for your instance, run:

```bash
sudo -u pajbot psql pajbot -c "CREATE SCHEMA pajbot1_streamername"
```

Remember the name of the schema you created! You'll need to enter it into the configuration file, which you will create and edit in the next step:

## Create a configuration file

There is an [example config file](../configs/example.ini) available for you to copy:

```bash
sudo -u pajbot cp /opt/pajbot/configs/example.ini /opt/pajbot/configs/streamer_name.ini
```

The example config contains comments about what values you need to enter in what places. Edit the config with a text editor to adjust the values.

```bash
sudo -u pajbot editor /opt/pajbot/configs/streamer_name.ini
```

## Set up the website with nginx

Pajbot comes with pre-set nginx configuration files you only need to copy and edit lightly to reflect your installation.

```bash
sudo cp /opt/pajbot/install-docs/nginx-example.conf /etc/nginx/sites-available/streamer_name.your-domain.com.conf
sudo ln -s /etc/nginx/sites-available/streamer_name.your-domain.com.conf /etc/nginx/sites-enabled/
```

You have to then edit the file, at the very least you will have to insert the correct streamer name instead of the example streamer name.

The example configuration sets your website up over HTTPS, for which you need a certificate (`ssl_certificate` and `ssl_certificate_key`). There are many possible ways to get a certificate, which is why we can't offer a definitive guide that will work for everybody's setup. However, if you need help for this step, you can [find a guide here](./certbot-with-cloudflare/README.md) if you have set up your domain with **CloudFlare DNS**.

Once you're done with your changes, test that the configuration has no errors:

```bash
sudo nginx -t
```

If this check is OK, you can now reload nginx:

```bash
sudo systemctl reload nginx
```

## Enable and start the service

To start and enable (i.e. run it on boot) pajbot, run:

```bash
sudo systemctl enable --now pajbot@streamer_name pajbot-web@streamer_name
```

## Authenticate the bot

One last step: You need to give your pajbot instance access to use your bot account! For this purpose, visit the URL `https://streamer_name.your-domain.com/bot_login` and complete the login procedure to authorize the bot.

The bot will then automatically come online in chat within about 2-3 seconds of you completing the login process.

## Further steps

Congratulations! Your bot should be running by now, but there are some extra steps you may want to complete:

- Ask the streamer to log in once by going to `https://streamer_name.your-domain.com/streamer_login` - If the streamer does this, the bot will be able to fetch who's a subscriber and keep the database up-to-date regularly. The bot will also then be able to change the game and title with the `!settitle` and `!setgame` commands. Alternatively the streamer could give the bot the [editor permission](https://help.twitch.tv/s/article/Managing-Roles-for-your-Channel?language=en_US#manage), this will also allow the bot to change the game and title from chat.
- Add some basic commands:

  Here's some ideas:

  ```
  !add command ping --reply $(tb:bot_name) $(tb:version_brief) online for $(tb:bot_uptime)
  !add command commands|help --reply $(tb:bot_name) commands available here: https://$(tb:bot_domain)/commands
  !add command ecount --reply $(1) has been used $(ecount;1) times.
  !add command epm --reply $(1) is currently being used $(epm;1) times per minute.
  !add command uptime|downtime --reply $(broadcaster:name) has been $(tb:stream_status) for $(tb:status_length)
  !add command points|p --reply $(usersource;1:name) has $(usersource;1:points|number_format) points
  !add command lastseen --reply $(user;1:name) was last seen $(user;1:last_seen|time_since_dt) ago, and last active $(user;1:last_active|time_since_dt) ago.
  !add command epmrecord --reply $(1) per minute record is $(epmrecord;1).
  !add command profile --reply https://$(tb:bot_domain)/user/$(usersource;1:login)
  !add command overlay|clr --reply https://$(tb:bot_domain)/clr/overlay/12345
  !add command playsounds --reply available playsounds are listed here: https://$(tb:bot_domain)/playsounds
  !add command title --reply Current stream title: $(stream:title)
  !add command game --reply Current stream game: $(stream:game)
  !add command timeonline|watchtime --reply $(usersource;1:name) has spent $(usersource;1:minutes_in_chat_online|time_since_minutes) in online chat.
  !add command timeoffline --reply $(usersource;1:name) has spent $(usersource;1:minutes_in_chat_offline|time_since_minutes) in offline chat.
  ```

- Advanced command arguments can be found [here.](https://github.com/pajbot/pajbot/blob/1ed503003c7363ebc592d0945d6c31ab1107db30/pajbot/managers/command.py#L450-L464)
