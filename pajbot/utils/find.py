def find(predicate, seq):
    """Method shamelessly taken from https://github.com/Rapptz/discord.py """

    for element in seq:
        if predicate(element):
            return element
    return None
