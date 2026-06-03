import time
from functools import wraps


def benchmark(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        duration = end_time - start_time
        print(f"Function '{func.__name__}' took {duration:.6f} seconds to complete.")
        return result

    return wrapper
