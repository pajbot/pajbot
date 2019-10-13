#!/usr/bin/env python3
import sys

import redis

# adjust here if you have specific redis options!
r = redis.Redis()

KEY_TEMPLATES = [
    "emotes:count",
    "kvi",
    "emotes:epmrecord",
    "users:username_raw",
    "users:last_seen",
    "users:num_lines",
    "users:last_active",
    "logs:admin",
]


def dump(streamer):
    # MULTI
    sys.stdout.buffer.write(b"*1\r\n$5\r\nMULTI\r\n")
    for key_template in KEY_TEMPLATES:
        key = f"{streamer}:{key_template}"
        blob = r.dump(key)

        binary_key = key.encode("utf-8")
        binary_key_len = str(len(key)).encode("ascii")

        if blob is None:
            # DEL <key>
            sys.stdout.buffer.write(b"*2\r\n$3\r\nDEL\r\n$" + binary_key_len + b"\r\n" + binary_key + b"\r\n")
            continue

        binary_blob_len = str(len(blob)).encode("ascii")
        # RESTORE <key> 0 <blob> REPLACE
        sys.stdout.buffer.write(
            b"*5\r\n$7\r\nRESTORE\r\n$"
            + binary_key_len
            + b"\r\n"
            + binary_key
            + b"\r\n$1\r\n0\r\n$"
            + binary_blob_len
            + b"\r\n"
            + blob
            + b"\r\n$7\r\nREPLACE\r\n"
        )

    # EXEC
    sys.stdout.buffer.write(b"*1\r\n$4\r\nEXEC\r\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Error: first argument missing (should be the streamer name)", file=sys.stderr)
        sys.exit(1)

    if sys.stdout.isatty():
        print(
            f"""Error: Detected that stdout is a terminal.
This script generates raw redis protocol, and the binary output will most likely fuck up your terminal badly.
Redirect this script's output to a file, e.g. {sys.argv[0]} > redis_dump_{sys.argv[1]}.bin""",
            file=sys.stderr,
        )
        sys.exit(1)

    dump(sys.argv[1])
    print("Success! Restore the data with redis-cli --pipe < your_dump_file.bin", file=sys.stderr)
