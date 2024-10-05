import sys


def dump_threads() -> None:
    import threading
    import traceback

    for th in threading.enumerate():
        print(th)
        if th.ident:
            traceback.print_stack(sys._current_frames()[th.ident])
        print()
