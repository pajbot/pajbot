#!/bin/sh

set -e

STREAMER=$1
OLD_USERNAME=$2
NEW_USERNAME=$3

if [ -z "${NEW_USERNAME}" ]; then
    echo "Usage: ${0} STREAMER OLD_USERNAME NEW_USERNAME"
    exit 1
fi

echo "Streamer: ${STREAMER}"
echo "Old username: ${OLD_USERNAME}"
echo "New username: ${NEW_USERNAME}"

while true; do
    printf "Are you sure you want to transfer all redis-data from %s to %s? (y/n) " "${OLD_USERNAME}" "${NEW_USERNAME}"
    read -r yn
    case $yn in
        [Yy]* ) break;;
        [Nn]* ) exit;;
    esac
done

echo "Continuing..."

LAST_SEEN_KEY="${STREAMER}:users:last_seen"

FROM_USER_LAST_SEEN=$(redis-cli HGET "${LAST_SEEN_KEY}" "${OLD_USERNAME}")

if [ -n "$FROM_USER_LAST_SEEN" ]; then
    echo "Moving last seen value"
    REDIS_RESULT=$(redis-cli HSETNX "${LAST_SEEN_KEY}" "${NEW_USERNAME}" "${FROM_USER_LAST_SEEN}")
    if [ "$REDIS_RESULT" = "1" ]; then
        echo "Successfully moved last seen value"
        redis-cli HDEL "${LAST_SEEN_KEY}" "${OLD_USERNAME}"
    else
        echo "Unable to move last seen value"
    fi
fi

NUM_LINES_KEY="${STREAMER}:users:num_lines"

CMD="redis-cli ZSCORE ${NUM_LINES_KEY} ${OLD_USERNAME}"

NUM_LINES=$($CMD 2>&1)

echo "Transferring ${NUM_LINES} lines from ${OLD_USERNAME} TO ${NEW_USERNAME}"

redis-cli ZINCRBY "${NUM_LINES_KEY}" "${NUM_LINES}" "${NEW_USERNAME}"

redis-cli ZREM "${NUM_LINES_KEY}" "${OLD_USERNAME}"
