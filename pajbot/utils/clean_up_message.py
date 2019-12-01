def clean_up_message(message):
    # list of twitch commands permitted, without leading slash or dot
    permitted_commands = ["me"]

    # remove leading whitespace
    message = message.lstrip()

    # limit of one split
    # '' -> ['']
    # 'a' -> ['a']
    # 'a ' -> ['a', '']
    # 'a b' -> ['a', 'b']
    # 'a b ' -> ['a', 'b ']
    # 'a b c' -> ['a', 'b c']
    parts = message.split(" ", 1)

    # if part 0 is a twitch command, we determine command and payload.
    if parts[0][:1] in [".", "/"]:
        if parts[0][1:] in permitted_commands:
            # permitted twitch command
            command = parts[0]
            if len(parts) < 2:
                payload = None
            else:
                payload = parts[1].lstrip()
        else:
            # disallowed twitch command
            command = "."
            payload = message
    else:
        # not a twitch command
        command = None
        payload = message

    # Stop the bot from calling other bot commands
    # by prefixing payload with invisible character
    if payload[:1] in ["!", "$", "-", "<", "?"]:
        payload = "\U000e0000" + payload

    if command is not None and payload is not None:
        # we have command and payload (e.g. ".me asd" or ". .timeout")
        return f"{command} {payload}"

    if command is not None:
        # we have command and NO payload (e.g. ".me")
        return command

    # we have payload and NO command (e.g. "asd", "\U000e0000!ping")
    return payload
