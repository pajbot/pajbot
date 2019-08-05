#!/usr/bin/env python3
import re

import json
import requests


def download_emoji_data():
    resp = requests.get("https://unicode.org/Public/emoji/12.0/emoji-test.txt")
    resp.raise_for_status()
    return resp.text


data_line_regex = re.compile("^[^#]*# (\\S+).*$")


def parse_emoji_data(text):
    lines = text.splitlines()

    all_emoji = []
    for line in lines:
        # strip whitespace
        line = line.strip()

        # skip comments
        if line.startswith("#"):
            continue

        # skip blank lines
        if len(line) == 0:
            continue

        # now only the lines containing the actual emoji are left
        match = data_line_regex.search(line)
        if match is None:
            raise ValueError("Unparseable line encountered: " + line)

        the_emoji = match.group(1)
        all_emoji.append(the_emoji)

    return all_emoji


if __name__ == "__main__":
    emoji_data_text = download_emoji_data()
    all_emoji = parse_emoji_data(emoji_data_text)

    list_str = json.dumps(all_emoji, ensure_ascii=False, indent=4)
    print("ALL_EMOJI = " + list_str)
