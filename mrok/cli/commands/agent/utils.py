import multiprocessing


def number_of_workers() -> int:
    return (multiprocessing.cpu_count() * 2) + 1
