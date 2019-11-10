#!/usr/bin/env bash
PBUID=$(id -u pajbot)
PBGID=$(id -g pajbot)

if [[ -z "${PBUID}${PBGID}" ]]; then
  echo 'pajbot user not detected.'
  exit 1
fi

if [ "$1" = "" ]; then
    echo "No streamer name provided. Example: ./scripts/docker/run.sh pajlada"
    exit 1
fi

if [ ! -f /opt/pajbot/configs/"$1".ini ]; then
    echo "No config file /opt/pajbot/configs/$1.ini found."
    exit 1
fi

echo docker run \
--name pajbot1-"$1" \
--restart unless-stopped \
-d \
-e STREAMERNAME="$1" \
-e TZ=UTC \
--network host \
-v /opt/pajbot/configs/"$1".ini:/app/config.ini \
-v /var/run/postgresql:/var/run/postgresql:ro \
-v /etc/localtime:/etc/localtime:ro \
-v /srv/pajbot:/srv/pajbot \
-u "$PBUID":"$PBGID" \
pajbot1:latest
