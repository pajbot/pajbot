import sys


def dump_threads():
    import threading
    import traceback

    for th in threading.enumerate():
        print(th)
        traceback.print_stack(sys._current_frames()[th.ident])
        print()
