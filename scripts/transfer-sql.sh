#!/bin/sh

set -e

mysql_command="mysql -uroot -ppenis"

# Ensure mysql command is set up properly
$mysql_command -e 'SHOW databases' 1>/dev/null

DATABASE=$1
OLD_USERNAME=$2
NEW_USERNAME=$3
ACTION=${4:-"move"}

if [ -z "${NEW_USERNAME}" ]; then
    echo "Usage: ${0} DATABASE OLD_USERNAME NEW_USERNAME (e.g. ${0} pb_snusbot pajlada-old-name pajlada-new-name)"
    exit 1
fi

echo "DATABASE: ${DATABASE}"
echo "Old username: ${OLD_USERNAME}"
echo "New username: ${NEW_USERNAME}"

while true; do
    printf "Are you sure you want to transfer all sql-data from %s to %s in database %s? (y/n) " "${OLD_USERNAME}" "${NEW_USERNAME}" "${DATABASE}"
    read -r yn
    case $yn in
        [Yy]* ) break;;
        [Nn]* ) exit;;
    esac
done

echo "Continuing..."

if [ "$ACTION" = "move" ]; then
    OLD_USER_ID=$($mysql_command "${DATABASE}" -s -N -e "SELECT id FROM tb_user WHERE username='${OLD_USERNAME}'")
    NEW_USER_ID=$($mysql_command "${DATABASE}" -s -N -e "SELECT id FROM tb_user WHERE username='${NEW_USERNAME}'")

    if [ -z "$NEW_USER_ID" ]; then
        echo "New user does not exist in the database"
        exit 1
    fi

    if [ -z "$OLD_USER_ID" ]; then
        echo "Old user does not exist in the database"
        exit 1
    fi
fi

# Move roulette stats from new user to old user
QUERY_MOVE_ROULETTE_STATS="UPDATE tb_roulette SET user_id=${OLD_USER_ID} WHERE user_id=${NEW_USER_ID}"

# Move duel stats from new user to old user
QUERY_MOVE_DUEL_STATS="UPDATE tb_user_duel_stats SET user_id=${OLD_USER_ID} WHERE user_id=${NEW_USER_ID}"
QUERY_GET_NEW_USER_DUEL_STATS="SELECT duels_won, duels_total, points_won, points_lost, last_duel, current_streak, longest_losestreak, longest_winstreak FROM tb_user_duel_stats WHERE user_id=${NEW_USER_ID}"
QUERY_GET_OLD_USER_DUEL_STATS="SELECT duels_won, duels_total, points_won, points_lost, last_duel, current_streak, longest_losestreak, longest_winstreak FROM tb_user_duel_stats WHERE user_id=${OLD_USER_ID}"

NEW_USER_DUEL_STATS=$($mysql_command "${DATABASE}" -s -N -e "${QUERY_GET_NEW_USER_DUEL_STATS}")
OLD_USER_DUEL_STATS=$($mysql_command "${DATABASE}" -s -N -e "${QUERY_GET_OLD_USER_DUEL_STATS}")

# Move stats from new user to old user
QUERY_MOVE_USER_STATS="
UPDATE
    tb_user OldUser,
    (
     SELECT
        level,
        points,
        minutes_in_chat_online,
        minutes_in_chat_offline
    FROM tb_user
    WHERE
        username='${NEW_USERNAME}') NewUser
SET
    OldUser.level = NewUser.level,
    OldUser.points = OldUser.points + NewUser.points,
    OldUser.minutes_in_chat_online = OldUser.minutes_in_chat_online + NewUser.minutes_in_chat_online,
    OldUser.minutes_in_chat_offline = OldUser.minutes_in_chat_offline + NewUser.minutes_in_chat_offline
WHERE
    OldUser.username='${OLD_USERNAME}';"

# Remove new user
QUERY_REMOVE_NEW_USER="DELETE FROM tb_user WHERE username='${NEW_USERNAME}' LIMIT 1;"

# Update username of old user
QUERY_UPDATE_OLD_USER_USERNAME="UPDATE tb_user SET username='${NEW_USERNAME}' WHERE username='${OLD_USERNAME}' LIMIT 1;"

if [ "$ACTION" = "move" ]; then
    echo "Moving roulette stats new user ${NEW_USERNAME} to old user ${OLD_USERNAME}"
    $mysql_command "${DATABASE}" -e "${QUERY_MOVE_ROULETTE_STATS}"

    echo "Moving duel stats new user ${NEW_USERNAME} to old user ${OLD_USERNAME}"
    if [ -n "$NEW_USER_DUEL_STATS" ]; then
        if [ -n "$OLD_USER_DUEL_STATS" ]; then
            echo "Both old user and new user have dueled, do a complicated combine (TODO)"
            $mysql_command "${DATABASE}" -e "DELETE FROM tb_user_duel_stats WHERE user_id=${NEW_USER_ID} LIMIT 1;"
        else
            echo "Old user has not dueled, do a simple move"
            $mysql_command "${DATABASE}" -e "${QUERY_MOVE_DUEL_STATS}"
        fi
    fi

    echo "Moving user stats from new user ${NEW_USERNAME} to old user ${OLD_USERNAME}"
    $mysql_command "${DATABASE}" -e "${QUERY_MOVE_USER_STATS}"

    echo "Removing new user ${NEW_USERNAME}"
    $mysql_command "${DATABASE}" -e "${QUERY_REMOVE_NEW_USER}"
fi

if [ "$ACTION" = "move" ] || [ "$ACTION" = "rename" ]; then
    echo "Updating old user username from ${OLD_USERNAME} to ${NEW_USERNAME}"
    $mysql_command "${DATABASE}" -e "${QUERY_UPDATE_OLD_USER_USERNAME}"
fi
