#!/bin/bash

PATH="`pwd`/myvenv/bin:$PATH" /usr/bin/pm2 start main.py --name="$1" --force --output="/var/log/pajbot/$1.log" --error="/var/log/pajbot/$1.err" --merge-logs -- --config configs/$1.ini
