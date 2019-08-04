#!/bin/sh

set -e

streamer_db() {
    streamer=$1

    case "$streamer" in
        "forsen") DATABASE="pb_snusbot" ;;
        "nani") DATABASE="pb_reipbot" ;;
        "nymn") DATABASE="pb_botnextdoor" ;;
        "imaqtpie") DATABASE="pb_wowsobot" ;;
        "xqcow") DATABASE="pb_xqc" ;;
        *) echo "No DB set up for streamer $streamer"; exit 1 ;;
    esac
}

STREAMER=$1
OLD_USERNAME=$2
NEW_USERNAME=$3

# fetch streamer DB
streamer_db "$STREAMER"

if [ -z "$STREAMER" ] || [ -z "$OLD_USERNAME" ] || [ -z "$NEW_USERNAME" ] || [ -z "$DATABASE" ]; then
    echo "Usage: ${0} STREAMER OLD_USERNAME NEW_USERNAME"
    exit 1
fi

echo "Starting REDIS transfer script"
./transfer-redis.sh "${STREAMER}" "${OLD_USERNAME}" "${NEW_USERNAME}"

echo "Starting SQL transfer script"
./transfer-sql.sh "${DATABASE}" "${OLD_USERNAME}" "${NEW_USERNAME}"
