def iterate_in_chunks(seq, chunk_size):
    return (seq[pos : pos + chunk_size] for pos in range(0, len(seq), chunk_size))
