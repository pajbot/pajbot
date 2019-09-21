def split_into_chunks_with_prefix(chunks, separator=" ", limit=500, default=None):
    messages = []
    current_message = ""
    current_prefix = None

    def try_append(prefix, new_part, recursive=False):
        nonlocal messages
        nonlocal current_message
        nonlocal current_prefix
        needs_prefix = current_prefix != prefix
        # new_suffix is the thing we want to append to the current_message
        new_suffix = prefix + separator + new_part if needs_prefix else new_part
        if len(current_message) > 0:
            new_suffix = separator + new_suffix

        if len(current_message) + len(new_suffix) <= limit:
            # fits
            current_message += new_suffix
            current_prefix = prefix
        else:
            # doesn't fit, start new message
            if recursive:
                raise ValueError("Function was given part that could never fit")

            messages.append(current_message)
            current_message = ""
            current_prefix = None
            try_append(prefix, new_part, True)

    for chunk in chunks:
        prefix = chunk["prefix"]
        parts = chunk["parts"]
        for part in parts:
            try_append(prefix, part)

    if len(current_message) > 0:
        messages.append(current_message)

    if len(messages) <= 0 and default is not None:
        messages = [default]

    return messages
