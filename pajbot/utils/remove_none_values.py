def remove_none_values(d):
    return {k: v for k, v in d.items() if v is not None}
