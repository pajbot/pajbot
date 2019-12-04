#!/usr/bin/env python3
import argparse

import requests


def get_se_channel(twitch_channel):
    response = requests.get("https://api.streamelements.com/kappa/v2/channels/" + twitch_channel)
    response.raise_for_status()
    json = response.json()
    display_name = json["displayName"]
    se_channel = json["_id"]
    print(f"Found channel {display_name} with StreamElements channel ID {se_channel}")
    return se_channel


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel", "-c", type=str, required=True, help="Twitch channel name (lowercase)")
    args = parser.parse_args()

    twitch_channel = args.channel
    se_channel = get_se_channel(twitch_channel)

    request = requests.get(f"https://api.streamelements.com/kappa/v2/store/{se_channel}/items")
    request.raise_for_status()
    se_playsounds = request.json()

    print()
    print()
    print()

    for se_playsound in se_playsounds:
        name = se_playsound["bot"]["identifier"]
        link = se_playsound["alert"]["audio"]["src"]
        volume = int(se_playsound["alert"]["audio"]["volume"] * 100)
        cooldown = se_playsound["cooldown"]["user"]
        enabled = se_playsound["enabled"]

        print(
            f"{self.prefix}add playsound {name} {link} --volume {volume} --cooldown {cooldown}{'' if enabled else ' --disabled'}"
        )

    print()
    print()
    print()
    print("Done listing.")
    print(
        "Copy paste this list into a pastebin and then run "
        f"\"{self.prefix}eval bot.eval_from_file(event, 'https://pastebin.com/raw/link')\""
    )


if __name__ == "__main__":
    main()
